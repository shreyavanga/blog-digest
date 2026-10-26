import logging
from types import SimpleNamespace

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
    result = summarize(make_post(), client)
    assert result.summary == "S"
    assert result.tags == []
    assert result.summarized is True


def test_bad_json_falls_back_to_excerpt():
    result = summarize(make_post(), FakeClient("not json at all"))
    assert result.summary == "E" * 300
    assert result.tags == []
    assert result.summarized is False


def test_empty_summary_falls_back():
    result = summarize(make_post(), FakeClient('{"summary": "  ", "tags": []}'))
    assert result.summarized is False
    assert result.summary == "E" * 300
    assert result.tags == []


def test_api_error_falls_back():
    result = summarize(make_post(), FakeClient(error=RuntimeError("boom")))
    assert result.summary == "E" * 300
    assert result.summarized is False


GOOD = '{"summary": "S", "tags": ["ai"]}'


def test_thinking_block_first_then_text():
    blocks = [SimpleNamespace(type="thinking", thinking="hmm"),
              SimpleNamespace(type="text", text=GOOD)]
    result = summarize(make_post(), FakeClient(blocks=blocks))
    assert result.summarized is True and result.summary == "S"


def test_no_text_block_falls_back():
    client = FakeClient(blocks=[SimpleNamespace(type="thinking", thinking="hmm")])
    result = summarize(make_post(), client)
    assert result.summarized is False and result.summary == "E" * 300


def test_max_tokens_stop_reason_falls_back():
    result = summarize(make_post(), FakeClient(GOOD, stop_reason="max_tokens"))
    assert result.summarized is False and result.tags == []


def test_refusal_stop_reason_falls_back():
    assert summarize(make_post(), FakeClient(GOOD, stop_reason="refusal")).summarized is False


def test_string_tags_become_empty_list():
    result = summarize(make_post(), FakeClient('{"summary": "S", "tags": "ai, infra"}'))
    assert result.summarized is True and result.tags == []


def test_request_parameters():
    client = FakeClient(GOOD)
    summarize(make_post(), client)
    call = client.calls[0]
    assert call["thinking"] == {"type": "disabled"}
    assert call["max_tokens"] == 1024
    assert call["model"] == "claude-haiku-5-5"


def test_prompt_has_teaser_and_always_json_instruction():
    client = FakeClient(GOOD)
    summarize(make_post(), client)
    content = client.calls[0]["messages"][0]["content"]
    assert "may be only a short teaser" in content
    assert "ALWAYS reply with the JSON object only" in content


def test_prose_reply_logs_start_of_reply_and_falls_back(caplog):
    prose = "I need more text\nto write a summary. " + "x" * 400
    with caplog.at_level(logging.WARNING, logger="digest.summarize"):
        result = summarize(make_post(), FakeClient(prose))
    assert result.summarized is False and result.summary == "E" * 300
    assert "I need more text to write a summary." in caplog.text
    assert "x" * 200 not in caplog.text
    assert "EEEE" not in caplog.text


def test_success_sets_summary_version_and_failure_does_not():
    from digest.summarize import SUMMARY_VERSION
    assert summarize(make_post(), FakeClient(GOOD)).summary_version == SUMMARY_VERSION
    assert summarize(make_post(), FakeClient("nope")).summary_version == 0


def test_prompt_asks_for_plain_language():
    client = FakeClient(GOOD)
    summarize(make_post(), client)
    content = client.calls[0]["messages"][0]["content"]
    assert "everyday words" in content
    assert "at most 2 short sentences" in content
    assert "explain it in a few plain words" in content
    assert "Reply with ONLY the JSON object" in content
    assert "<article>" in content
