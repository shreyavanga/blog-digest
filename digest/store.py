import json
import os
import tempfile
from dataclasses import asdict
from datetime import date, timedelta
from pathlib import Path

from .models import Post

RETENTION_DAYS = 90


def load_posts(path: Path) -> list[Post]:
    path = Path(path)
    if not path.exists():
        return []
    return [Post(**item) for item in json.loads(path.read_text(encoding="utf-8"))]


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
    data = json.dumps([asdict(p) for p in ordered], indent=2, ensure_ascii=False) + "\n"
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
