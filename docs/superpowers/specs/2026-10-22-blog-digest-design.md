# Blog Digest — Design

## Goal

A personal app, usable on iPhone and iPad, that pulls new posts every day from popular tech engineering and AI company blogs, shows a short AI summary of each, and opens the original article on tap.

## Constraints

- Personal side project on personal accounts: personal GitHub and a personal Anthropic API key. No Apple credentials, Apple internal URLs, or Apple data anywhere in the project.
- Must be reachable from iPhone/iPad anywhere without VPN.
- No server to maintain; free hosting apart from Claude API usage.
- Out of scope for v1: push notifications, accounts/login, native iOS app, full-text search.

## Architecture

```
GitHub Actions (daily cron)
  └─ Python job: fetch feeds → dedupe → summarize (Claude API) → write data/posts.json → commit
GitHub Pages (static, public repo)
  └─ PWA (HTML/JS/CSS) reads data/posts.json
```

Repo layout:

```
blog-digest/
  sources.yaml            # list of {company, feed_url}
  digest/                 # Python package
    feeds.py              # fetch + parse feeds into Post records
    store.py              # load/merge/save posts.json, dedupe by URL
    summarize.py          # Claude API call, fallback to excerpt
    run.py                # orchestrates one daily run, prints run report
  tests/
  site/                   # static PWA (index.html, app.js, style.css, manifest.webmanifest, sw.js, icons)
    data/posts.json       # generated output, served with the site
  .github/workflows/daily.yml
```

## Components

### sources.yaml
About 25 engineering and AI blogs with feed URLs (e.g. Google, Meta, Microsoft, Amazon, Netflix, Uber, Stripe, Cloudflare, GitHub, OpenAI, Anthropic). Each entry: `company`, `feed_url`. Adding a source is a one-line edit. Companies without a working feed are omitted.

### feeds.py
`fetch_posts(source) -> list[Post]`. Uses `feedparser` with a request timeout. `Post` fields: `url`, `company`, `title`, `published` (ISO date), `excerpt`. A feed that fails to load or parse raises `FeedError`; `run.py` catches it per feed, logs it, and continues with the other feeds.

### store.py
Loads `site/data/posts.json` (empty list if missing), merges new posts keyed by `url`, keeps existing summaries untouched, and prunes posts older than 90 days. Writes sorted newest first.

### summarize.py
`summarize(post) -> (summary, tags)`. Sends title and article text (or excerpt if text is unavailable) to a small Claude model and requests a 2–3 sentence summary and 1–3 topic tags as JSON. On any API or parse failure, returns the feed excerpt as the summary with no tags and marks the post `summarized: false` so the next run retries it. The API key comes from the `ANTHROPIC_API_KEY` environment variable.

### run.py
One daily run: for each source fetch posts, merge into the store, summarize posts not yet summarized (capped at 50 per run to bound cost), save, and print a report (new / summarized / failed counts, failing feeds). Exits non-zero only if every feed failed.

### PWA (site/)
- Mobile-first feed, newest first, grouped by day. Card: company, title, summary, tags, date.
- Tap a card to open the original URL in a new tab.
- Filter by company and by tag.
- Read/unread state in `localStorage`; unread cards visually distinct.
- `manifest.webmanifest` and icons for Add to Home Screen; service worker caches the shell and the last `posts.json` for offline reading.

### daily.yml
Scheduled daily cron (plus manual `workflow_dispatch`). Steps: checkout, set up Python, install, run `python -m digest.run` with `ANTHROPIC_API_KEY` from Actions secrets, commit `site/data/posts.json` if changed. GitHub Pages serves `site/`.

## Data format

`site/data/posts.json`: array of
`{url, company, title, published, excerpt, summary, tags[], summarized}`.

## Error handling

- Per-feed isolation: one bad feed never stops the run.
- Summary failures fall back to the excerpt and are retried next run.
- Network calls have timeouts.
- The API key is never written to the repo or logs.

## Testing

- Unit tests: feed parsing (fixture XML for RSS and Atom), dedupe/merge/prune in the store, summarizer fallback paths.
- Claude API is mocked in all tests.
- Pipeline test: fixture feeds → run → expected `posts.json`.
- PWA checked manually in a browser and on a device after deploy.

## Setup (user steps after build)

1. Create a personal public GitHub repo and push.
2. Add `ANTHROPIC_API_KEY` as a repository Actions secret.
3. Enable GitHub Pages for the `site/` content (via Actions deploy).
4. Open the Pages URL in Safari on iPhone/iPad → Share → Add to Home Screen.
