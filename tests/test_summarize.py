from digest.models import Post
from digest.summarize import summarize
from tests.fakes import FakeClient


def make_post():
    return Post(url="u", company="Acme", title="Scaling queues", published="2026-10-20",
                excerpt="E" * 500)


def test_success_sets_summary_and_tags():
    client = FakeClient('{"summary": "Two sentences.", "tags": ["AI", "Infra", "x", "y"]}')
    result = summarize(make_post(), client)
    assert result.summary == "Two sentences."
    assert result.tags == ["ai", "infra", "x"]
    assert result.summarized is True


def test_prompt_contains_title_and_excerpt():
    client = FakeClient('{"summary": "S", "tags": []}')
    summarize(make_post(), client)
    content = client.calls[0]["messages"][0]["content"]
    assert "Scaling queues" in content and "EEEE" in content


def test_fenced_json_is_accepted():
    client = FakeClient('```json\n{"summary": "S", "tags": []}\n```')
    assert summarize(make_post(), client).summary == "S"


def test_bad_json_falls_back_to_excerpt():
    result = summarize(make_post(), FakeClient("not json at all"))
    assert result.summary == "E" * 300
    assert result.tags == []
    assert result.summarized is False


def test_empty_summary_falls_back():
    result = summarize(make_post(), FakeClient('{"summary": "  ", "tags": []}'))
    assert result.summarized is False


def test_api_error_falls_back():
    result = summarize(make_post(), FakeClient(error=RuntimeError("boom")))
    assert result.summary == "E" * 300
    assert result.summarized is False
