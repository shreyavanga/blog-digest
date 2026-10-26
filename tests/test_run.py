from datetime import date

import httpx

import pytest

from digest.run import Report, exit_code, load_sources, run
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


def test_exit_code():
    assert exit_code(Report(feeds_ok=0)) == 1
    assert exit_code(Report(feeds_ok=1, summarized=0, failed=3)) == 1
    assert exit_code(Report(feeds_ok=1, summarized=2, failed=1)) == 0
    assert exit_code(Report(feeds_ok=1)) == 0


def test_load_sources_valid(tmp_path):
    f = tmp_path / "s.yaml"
    f.write_text("- company: A\n  feed_url: https://a.test/f\n", encoding="utf-8")
    assert load_sources(f) == [{"company": "A", "feed_url": "https://a.test/f"}]


@pytest.mark.parametrize("content", [
    "", "{}", "[]", "- just a string", "- company: A", "- feed_url: https://a.test",
    "- company: ''\n  feed_url: https://a.test", "- company: A\n  feed_url: ' '",
])
def test_load_sources_invalid_exits(tmp_path, content):
    f = tmp_path / "s.yaml"
    f.write_text(content, encoding="utf-8")
    with pytest.raises(SystemExit):
        load_sources(f)


def many_items_http(n):
    items = "".join(
        f"<item><title>P{i}</title><link>https://acme.test/p{i}</link>"
        f"<pubDate>{'%02d' % (i + 1)} Oct 2026 10:00:00 GMT</pubDate>"
        f"<description>d{i}</description></item>" for i in range(n))
    body = f'<?xml version="1.0"?><rss version="2.0"><channel><title>E</title>{items}</channel></rss>'.encode()
    return httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=body)))


def test_per_company_cap_limits_store_and_summaries(tmp_path, monkeypatch):
    monkeypatch.setattr("digest.run.MAX_PER_COMPANY", 5)
    client = FakeClient(GOOD_JSON)
    path = tmp_path / "posts.json"
    src = [{"company": "Acme", "feed_url": "https://acme.test/feed"}]
    first = run(src, path, client, many_items_http(9), TODAY)
    stored = load_posts(path)
    assert len(stored) == 5 and first.new == 5
    assert {p.url for p in stored} == {f"https://acme.test/p{i}" for i in range(4, 9)}
    assert len(client.calls) == 5 and first.summarized == 5
    second = run(src, path, client, many_items_http(9), TODAY)
    assert second.new == 0 and len(client.calls) == 5


def seed(tmp_path, posts):
    from dataclasses import asdict
    import json
    (tmp_path / "posts.json").write_text(json.dumps([asdict(p) for p in posts]), encoding="utf-8")


def old_post(url, published, version=1):
    from digest.models import Post
    return Post(url=url, company="Acme", title="T", published=published, excerpt="e",
                summary="old summary", tags=["x"], summarized=True, summary_version=version)


def one_src_http(urls_dates):
    items = "".join(
        f"<item><title>T</title><link>{u}</link><pubDate>{d} Oct 2026 10:00:00 GMT</pubDate>"
        f"<description>d</description></item>" for u, d in urls_dates)
    body = f'<?xml version="1.0"?><rss version="2.0"><channel><title>E</title>{items}</channel></rss>'.encode()
    return httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=body)))


SRC = [{"company": "Acme", "feed_url": "https://acme.test/feed"}]
NO_FEED = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500)))


def test_old_version_post_is_resummarized(tmp_path):
    from digest.summarize import SUMMARY_VERSION
    seed(tmp_path, [old_post("https://acme.test/p1", "2026-10-20")])
    report = run(SRC, tmp_path / "posts.json", FakeClient(GOOD_JSON), NO_FEED, TODAY)
    assert (report.summarized, report.failed) == (1, 0)
    p = load_posts(tmp_path / "posts.json")[0]
    assert p.summary == "A summary." and p.summary_version == SUMMARY_VERSION


def test_current_version_post_is_not_resent(tmp_path):
    from digest.summarize import SUMMARY_VERSION
    seed(tmp_path, [old_post("https://acme.test/p1", "2026-10-20", version=SUMMARY_VERSION)])
    client = FakeClient(GOOD_JSON)
    report = run(SRC, tmp_path / "posts.json", client, NO_FEED, TODAY)
    assert client.calls == [] and report.summarized == 0


def test_failed_resummary_keeps_original(tmp_path):
    seed(tmp_path, [old_post("https://acme.test/p1", "2026-10-20")])
    report = run(SRC, tmp_path / "posts.json", FakeClient("not json"), NO_FEED, TODAY)
    assert (report.summarized, report.failed) == (0, 1)
    p = load_posts(tmp_path / "posts.json")[0]
    assert p.summary == "old summary" and p.summarized is True
    assert p.summary_version == 1 and p.tags == ["x"]


def test_cap_applies_across_new_and_old_newest_first(tmp_path):
    seed(tmp_path, [old_post("https://acme.test/old1", "2026-10-10"),
                    old_post("https://acme.test/old2", "2026-10-15")])
    http = one_src_http([("https://acme.test/new", "20")])
    client = FakeClient(GOOD_JSON)
    report = run(SRC, tmp_path / "posts.json", client, http, TODAY, max_summaries=2)
    assert report.summarized == 2
    posts = {p.url: p for p in load_posts(tmp_path / "posts.json")}
    assert posts["https://acme.test/new"].summary == "A summary."
    assert posts["https://acme.test/old2"].summary == "A summary."
    assert posts["https://acme.test/old1"].summary == "old summary"
