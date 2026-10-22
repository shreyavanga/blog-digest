import html
import re
from datetime import date

import feedparser
import httpx

from .models import Post

MAX_TEXT = 4000
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


class FeedError(Exception):
    pass


def clean_text(raw: str) -> str:
    text = html.unescape(_TAG_RE.sub(" ", raw or ""))
    return _WS_RE.sub(" ", text).strip()[:MAX_TEXT]


def _entry_text(entry) -> str:
    content = entry.get("content")
    raw = content[0].get("value", "") if content else entry.get("summary", "")
    return clean_text(raw)


def _entry_date(entry, today: date) -> str:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return date(parsed.tm_year, parsed.tm_mon, parsed.tm_mday).isoformat()
    return today.isoformat()


def parse_feed(content: bytes, company: str, today: date) -> list[Post]:
    parsed = feedparser.parse(content)
    if parsed.bozo and not parsed.entries:
        raise FeedError(f"{company}: not a valid feed")
    posts = []
    for entry in parsed.entries:
        url = entry.get("link")
        title = clean_text(entry.get("title", ""))
        if not url or not title:
            continue
        posts.append(Post(
            url=url,
            company=company,
            title=title,
            published=_entry_date(entry, today),
            excerpt=_entry_text(entry),
        ))
    return posts


def fetch_posts(source: dict, client: httpx.Client, today: date) -> list[Post]:
    try:
        response = client.get(source["feed_url"], follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise FeedError(f"{source['company']}: {exc}") from exc
    return parse_feed(response.content, source["company"], today)
