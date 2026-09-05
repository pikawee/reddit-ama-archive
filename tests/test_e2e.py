import http.server
import threading
import time
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path("dist").resolve()), **kwargs)

@pytest.fixture(scope="module")
def local_server():
    port = 8124
    with http.server.ThreadingHTTPServer(("", port), Handler) as httpd:
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        time.sleep(0.5)
        yield f"http://localhost:{port}"
        httpd.shutdown()

def test_e2e_http_server(local_server):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))
        
        page.goto(local_server, wait_until="networkidle")

        title = page.title()
        assert "Carl Pei" in title
        cards = page.query_selector_all(".card")
        assert len(cards) == 65, f"Expected 65 cards, found {len(cards)}"

        cat_btn = page.query_selector("button.filter:not([data-cat='All'])")
        assert cat_btn is not None
        cat_btn.click()
        page.wait_for_timeout(300)
        visible_cards = [c for c in page.query_selector_all(".card") if "hidden" not in (c.get_attribute("class") or "")]
        assert 0 < len(visible_cards) < 65

        all_btn = page.query_selector("button.filter[data-cat='All']")
        all_btn.click()
        page.wait_for_timeout(300)
        visible_cards_all = [c for c in page.query_selector_all(".card") if "hidden" not in (c.get_attribute("class") or "")]
        assert len(visible_cards_all) == 65

        search_input = page.query_selector("#search")
        search_input.fill("RAMageddon")
        page.wait_for_timeout(300)
        search_results = [c for c in page.query_selector_all(".card") if "hidden" not in (c.get_attribute("class") or "")]
        assert len(search_results) == 1
        assert "megakilo13" in search_results[0].inner_text().lower()

        assert len(errors) == 0, f"Page errors encountered: {errors}"
        browser.close()

def test_e2e_file_protocol():
    dist_html = Path("dist/index.html").resolve()
    file_url = dist_html.as_uri()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))
        
        page.goto(file_url, wait_until="load")
        page.wait_for_timeout(500)
        
        cards = page.query_selector_all(".card")
        assert len(cards) == 65, f"Expected 65 cards under file:///, found {len(cards)}"
        assert len(errors) == 0, f"Errors under file:///: {errors}"
        browser.close()
