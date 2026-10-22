# Blog Digest

A daily digest of tech engineering and AI company blogs, installable on iPhone/iPad as a home-screen app.
A GitHub Actions job fetches new posts, summarizes them with Claude, and publishes a static PWA to GitHub Pages.

## Local development

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/pytest                          # run tests
.venv/bin/python -m digest.run --check    # verify every feed in sources.yaml
ANTHROPIC_API_KEY=... .venv/bin/python -m digest.run   # full run, updates site/data/posts.json
python3 -m http.server 8000 --directory site           # preview the app
```

Add or remove blogs by editing `sources.yaml`.

## Deploy (personal accounts only)

1. Create a **public** repo on your personal GitHub account and push this project to `main`.
2. Repo Settings → Secrets and variables → Actions → add secret `ANTHROPIC_API_KEY` (your personal key).
3. Repo Settings → Pages → Source: **GitHub Actions**.
4. Actions tab → *daily-digest* → **Run workflow** to do the first run.
5. On iPhone/iPad open `https://<your-user>.github.io/<repo>/` in Safari → Share → **Add to Home Screen**.

Keep this project off any Apple accounts, networks, or credentials.
