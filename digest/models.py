from dataclasses import dataclass, field


@dataclass(frozen=True)
class Post:
    url: str
    company: str
    title: str
    published: str  # YYYY-MM-DD
    excerpt: str
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    summarized: bool = False
