from datetime import date

from digest.models import Post
from digest.store import load_posts, merge, prune, save_posts


def post(url, published="2026-10-20", **kw):
    return Post(url=url, company="Acme", title="T", published=published, excerpt="e", **kw)


def test_load_missing_returns_empty(tmp_path):
    assert load_posts(tmp_path / "nope.json") == []


def test_merge_keeps_existing_summary_and_adds_new():
    existing = [post("u1", summary="S", summarized=True)]
    merged = merge(existing, [post("u1"), post("u2")])
    assert [p.url for p in merged] == ["u1", "u2"]
    assert merged[0].summary == "S" and merged[0].summarized is True


def test_merge_dedupes_within_new():
    merged = merge([], [post("u1"), post("u1")])
    assert len(merged) == 1


def test_prune_drops_old_posts():
    today = date(2026, 10, 22)
    posts = [post("old", "2026-07-01"), post("edge", "2026-07-24"), post("new", "2026-10-20")]
    assert [p.url for p in prune(posts, today)] == ["edge", "new"]


def test_save_sorts_newest_first_and_roundtrips(tmp_path):
    path = tmp_path / "data" / "posts.json"
    posts = [post("a", "2026-10-18"), post("b", "2026-10-20", summary="S", tags=["ai"], summarized=True)]
    save_posts(path, posts)
    loaded = load_posts(path)
    assert [p.url for p in loaded] == ["b", "a"]
    assert loaded[0].tags == ["ai"] and loaded[0].summarized is True


def test_save_is_atomic_and_leaves_no_temp_file(tmp_path):
    import json
    path = tmp_path / "data" / "posts.json"
    save_posts(path, [post("a"), post("b")])
    save_posts(path, [post("a")])
    assert len(json.loads(path.read_text(encoding="utf-8"))) == 1
    assert [p.name for p in path.parent.iterdir()] == ["posts.json"]
