from dataclasses import asdict

from digest.models import Post


def test_post_defaults():
    p = Post(url="https://e.com/a", company="Acme", title="T", published="2026-10-20", excerpt="x")
    assert p.summary == ""
    assert p.tags == []
    assert p.summarized is False


def test_post_roundtrips_through_dict():
    p = Post(url="u", company="c", title="t", published="2026-10-20", excerpt="e",
             summary="s", tags=["ai"], summarized=True)
    assert Post(**asdict(p)) == p


def test_summary_version_defaults_to_zero():
    p = Post(url="u", company="c", title="t", published="2026-10-20", excerpt="e")
    assert p.summary_version == 0
