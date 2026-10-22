from datetime import date

import httpx

from digest.run import run
from digest.store import load_posts
from tests.fakes import FakeClient
from tests.test_feeds import RSS

TODAY = date(2026, 10, 22)
GOOD_JSON = '{"summary": "A summary.", "tags": ["ai"]}'
SOURCES = [
    {"company": "Acme", "feed_url": "https://acme.test/feed"},
    {"company": "Broken", "feed_url": "https://broken.test/feed"},
]


def http_client():
    def handler(request):
        if request.url.host == "acme.test":
            return httpx.Response(200, content=RSS)
        return httpx.Response(500)
    return httpx.Client(transport=httpx.MockTransport(handler))


def do_run(tmp_path, client, **kw):
    return run(SOURCES, tmp_path / "posts.json", client, http_client(), TODAY, **kw)


def test_full_pipeline_isolates_bad_feed(tmp_path):
    report = do_run(tmp_path, FakeClient(GOOD_JSON))
    assert (report.new, report.summarized, report.failed) == (2, 2, 0)
    assert report.feeds_ok == 1
    assert len(report.feed_errors) == 1 and "Broken" in report.feed_errors[0]
    posts = load_posts(tmp_path / "posts.json")
    assert all(p.summary == "A summary." and p.summarized for p in posts)


def test_second_run_is_idempotent(tmp_path):
    client = FakeClient(GOOD_JSON)
    do_run(tmp_path, client)
    calls_after_first = len(client.calls)
    report = do_run(tmp_path, client)
    assert (report.new, report.summarized) == (0, 0)
    assert len(client.calls) == calls_after_first


def test_failed_summaries_are_retried_next_run(tmp_path):
    first = do_run(tmp_path, FakeClient(error=RuntimeError("down")))
    assert (first.summarized, first.failed) == (0, 2)
    second = do_run(tmp_path, FakeClient(GOOD_JSON))
    assert (second.new, second.summarized, second.failed) == (0, 2, 0)


def test_summary_cap_prefers_newest(tmp_path):
    report = do_run(tmp_path, FakeClient(GOOD_JSON), max_summaries=1)
    assert report.summarized == 1
    posts = {p.url: p for p in load_posts(tmp_path / "posts.json")}
    assert posts["https://example.com/b"].summarized is True   # published today
    assert posts["https://example.com/a"].summarized is False  # older


def test_all_feeds_failing_reports_zero_ok(tmp_path):
    failing = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    report = run(SOURCES, tmp_path / "posts.json", FakeClient(GOOD_JSON), failing, TODAY)
    assert report.feeds_ok == 0 and report.new == 0
