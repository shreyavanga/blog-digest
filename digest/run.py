import argparse
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import httpx
import yaml

from .feeds import FeedError, fetch_posts
from .store import load_posts, merge, prune, save_posts
from .summarize import summarize

log = logging.getLogger("digest")

ROOT = Path(__file__).resolve().parent.parent
SOURCES_PATH = ROOT / "sources.yaml"
STORE_PATH = ROOT / "site" / "data" / "posts.json"
MAX_SUMMARIES = 50
HTTP_TIMEOUT = 15.0
USER_AGENT = "blog-digest/1.0 (personal feed reader)"


@dataclass
class Report:
    new: int = 0
    summarized: int = 0
    failed: int = 0
    feeds_ok: int = 0
    feed_errors: list[str] = field(default_factory=list)


def run(sources, store_path, client, http_client, today, max_summaries=MAX_SUMMARIES) -> Report:
    report = Report()
    existing = load_posts(store_path)

    fetched = []
    for source in sources:
        try:
            fetched += fetch_posts(source, http_client, today)
            report.feeds_ok += 1
        except FeedError as exc:
            log.warning("feed failed: %s", exc)
            report.feed_errors.append(str(exc))

    merged = merge(existing, fetched)
    report.new = len(merged) - len(existing)
    posts = prune(merged, today)

    pending = sorted((p for p in posts if not p.summarized),
                     key=lambda p: (p.published, p.url), reverse=True)[:max_summaries]
    updated = {}
    for post in pending:
        result = summarize(post, client)
        updated[post.url] = result
        if result.summarized:
            report.summarized += 1
        else:
            report.failed += 1
    posts = [updated.get(p.url, p) for p in posts]

    save_posts(store_path, posts)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="digest.run")
    parser.add_argument("--check", action="store_true",
                        help="fetch every feed and print post counts; no summaries, nothing saved")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    sources = yaml.safe_load(SOURCES_PATH.read_text())
    today = date.today()
    http_client = httpx.Client(timeout=HTTP_TIMEOUT, headers={"User-Agent": USER_AGENT})

    if args.check:
        ok = 0
        for source in sources:
            try:
                count = len(fetch_posts(source, http_client, today))
                ok += 1
                print(f"OK    {source['company']:<22} {count} posts")
            except FeedError as exc:
                print(f"FAIL  {exc}")
        return 0 if ok else 1

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set")
    import anthropic
    report = run(sources, STORE_PATH, anthropic.Anthropic(), http_client, today)
    print(f"feeds ok: {report.feeds_ok}/{len(sources)}  new: {report.new}  "
          f"summarized: {report.summarized}  failed: {report.failed}")
    for err in report.feed_errors:
        print(f"  feed error: {err}")
    return 0 if report.feeds_ok else 1


if __name__ == "__main__":
    sys.exit(main())
