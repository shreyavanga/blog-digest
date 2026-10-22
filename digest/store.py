import json
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path

from .models import Post

RETENTION_DAYS = 90


def load_posts(path: Path) -> list[Post]:
    path = Path(path)
    if not path.exists():
        return []
    return [Post(**item) for item in json.loads(path.read_text())]


def merge(existing: list[Post], new: list[Post]) -> list[Post]:
    seen = {p.url for p in existing}
    added = []
    for p in new:
        if p.url not in seen:
            seen.add(p.url)
            added.append(p)
    return existing + added


def prune(posts: list[Post], today: date) -> list[Post]:
    cutoff = (today - timedelta(days=RETENTION_DAYS)).isoformat()
    return [p for p in posts if p.published >= cutoff]


def save_posts(path: Path, posts: list[Post]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(posts, key=lambda p: (p.published, p.url), reverse=True)
    path.write_text(json.dumps([asdict(p) for p in ordered], indent=2, ensure_ascii=False) + "\n")
