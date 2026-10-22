from datetime import date

import httpx
import pytest

from digest.feeds import FeedError, clean_text, fetch_posts, parse_feed

TODAY = date(2026, 10, 22)

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>Eng</title>
<item><title>Hello &amp; welcome</title><link>https://example.com/a</link>
<pubDate>Mon, 20 Oct 2026 10:00:00 GMT</pubDate>
<description>&lt;p&gt;Short &lt;b&gt;excerpt&lt;/b&gt;&lt;/p&gt;</description></item>
<item><title>No date</title><link>https://example.com/b</link><description>Body</description></item>
<item><title>No link</title><description>skip me</description></item>
</channel></rss>"""

ATOM = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Eng</title>
<entry><title>Atom post</title><link href="https://example.com/c"/>
<published>2026-10-19T08:30:00Z</published>
<content type="html">&lt;p&gt;Full &lt;i&gt;content&lt;/i&gt; here&lt;/p&gt;</content></entry></feed>"""


def test_clean_text_strips_html_and_whitespace():
    assert clean_text("<p>Hi&nbsp;<b>there</b>\n\n  you &amp; me</p>") == "Hi there you & me"


def test_clean_text_truncates():
    assert len(clean_text("a" * 10000)) == 4000


def test_parse_rss():
    posts = parse_feed(RSS, "Acme", TODAY)
    assert [p.url for p in posts] == ["https://example.com/a", "https://example.com/b"]
    first, second = posts
    assert first.company == "Acme"
    assert first.title == "Hello & welcome"
    assert first.published == "2026-10-20"
    assert first.excerpt == "Short excerpt"
    assert second.published == "2026-10-22"  # falls back to today


def test_parse_atom_uses_content():
    (post,) = parse_feed(ATOM, "Acme", TODAY)
    assert post.url == "https://example.com/c"
    assert post.published == "2026-10-19"
    assert post.excerpt == "Full content here"


def test_parse_garbage_raises():
    with pytest.raises(FeedError):
        parse_feed(b"this is not a feed", "Acme", TODAY)


def _client(status, body=b""):
    return httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(status, content=body)))


def test_fetch_posts_ok():
    source = {"company": "Acme", "feed_url": "https://example.com/feed"}
    posts = fetch_posts(source, _client(200, RSS), TODAY)
    assert len(posts) == 2


def test_fetch_posts_http_error_raises_feed_error():
    source = {"company": "Acme", "feed_url": "https://example.com/feed"}
    with pytest.raises(FeedError):
        fetch_posts(source, _client(500), TODAY)
