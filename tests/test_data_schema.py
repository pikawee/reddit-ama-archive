import json
from pathlib import Path


def test_threads_registry():
    threads_path = Path("assets/data/threads.json")
    assert threads_path.exists(), "threads.json missing"
    data = json.loads(threads_path.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["id"] == "1w78hmo"
    assert data[0]["guest_handle"] == "carpe02"
    assert data[0]["total_answers"] == 65
    assert data[0].get("avatar_url", "").startswith("http")

def test_carl_pei_qa_data():
    qa_path = Path("assets/data/1w78hmo.json")
    assert qa_path.exists(), "1w78hmo.json missing"
    data = json.loads(qa_path.read_text(encoding="utf-8"))
    assert data["thread_id"] == "1w78hmo"
    assert data["guest"].get("avatar_url", "").startswith("http")
    assert len(data["items"]) == 65
    first_item = data["items"][0]
    assert first_item["id"] == 1
    assert "oneunique" in first_item["question_author"]
    assert "carpe02" in first_item["answer_author"]

    item_52 = next((it for it in data["items"] if it["id"] == 52), None)
    assert item_52 is not None
    assert "Get us dynamic island" in item_52["question_text"]
    assert item_52["question_author"] == "u/_dsuza"
    assert "Switch to iPhone" in item_52["answer_text"]

def test_carl_pei_js_companion():
    js_path = Path("assets/data/1w78hmo.js")
    assert js_path.exists(), "1w78hmo.js companion missing"
    content = js_path.read_text(encoding="utf-8")
    assert "window.__AMA_DATA__" in content
    assert "1w78hmo" in content
