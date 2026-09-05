from pathlib import Path


def test_index_html_dynamic_structure():
    content = Path("index.html").read_text(encoding="utf-8")
    assert 'id="search"' in content, "Search input missing"
    assert 'id="grid"' in content, "Card grid missing"
    assert 'id="filters"' in content, "Filters container missing"
    assert 'threads.json' in content, "Threads registry reference missing"
    assert '__AMA_DATA__' in content, "Fallback companion script support missing"
    assert 'id="guest-avatar"' in content, "Guest avatar element missing"
    # Verify cards are rendered dynamically rather than hardcoded 65 times in template
    assert content.count('<article class="card"') == 0, "Cards are still hardcoded in index.html"
