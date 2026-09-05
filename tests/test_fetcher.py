from scripts.fetch_ama import extract_thread_id_from_url, pair_questions_and_answers


def test_extract_thread_id_from_url():
    url1 = "https://www.reddit.com/r/NothingTech/comments/1w78hmo/im_carl_pei_ceo_of_nothing_ama/?sort=qa"
    assert extract_thread_id_from_url(url1) == "1w78hmo"
    url2 = "https://reddit.com/comments/abc1234/"
    assert extract_thread_id_from_url(url2) == "abc1234"
    url3 = "1w78hmo"
    assert extract_thread_id_from_url(url3) == "1w78hmo"

def test_pair_questions_and_answers():
    sample_comments = [
        {
            "id": "c1",
            "parent_id": "t3_1w78hmo",
            "author": "user1",
            "body": "Could you consider removing semi-forced app installs?",
            "permalink": "/r/NothingTech/comments/1w78hmo/comment/c1/"
        },
        {
            "id": "c2",
            "parent_id": "t1_c1",
            "author": "carpe02",
            "body": "Yeah I agree we should dial this back a bit.",
            "permalink": "/r/NothingTech/comments/1w78hmo/comment/c2/"
        },
        {
            "id": "c3",
            "parent_id": "t3_1w78hmo",
            "author": "user2",
            "body": "Unanswered question from user 2?",
            "permalink": "/r/NothingTech/comments/1w78hmo/comment/c3/"
        }
    ]
    items = pair_questions_and_answers(sample_comments, target_user="carpe02")
    assert len(items) == 1
    assert items[0]["id"] == 1
    assert items[0]["question_author"] == "u/user1"
    assert items[0]["answer_author"] == "u/carpe02"
    assert "Yeah I agree" in items[0]["answer_text"]
    assert "Could you consider" in items[0]["question_text"]
