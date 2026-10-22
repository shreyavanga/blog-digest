const READ_KEY = "blog-digest-read";
const SUMMARY_MAX = 300;

const state = {
  posts: [],
  read: new Set(JSON.parse(localStorage.getItem(READ_KEY) || "[]")),
};

const $ = (id) => document.getElementById(id);

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function markRead(url) {
  state.read.add(url);
  localStorage.setItem(READ_KEY, JSON.stringify([...state.read]));
}

function formatDay(iso) {
  const date = new Date(iso + "T00:00:00");
  return date.toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric" });
}

function isSafeUrl(url) {
  return /^https?:\/\//i.test(url);
}

function card(post) {
  const a = el("a", "card" + (state.read.has(post.url) ? " read" : ""));
  if (isSafeUrl(post.url)) a.href = post.url;
  a.target = "_blank";
  a.rel = "noopener noreferrer";
  a.append(el("div", "meta", post.company));
  a.append(el("div", "title", post.title));
  a.append(el("div", "summary", (post.summary || post.excerpt || "").slice(0, SUMMARY_MAX)));
  if (post.tags && post.tags.length) {
    const tags = el("div", "tags");
    post.tags.forEach((t) => tags.append(el("span", "tag", t)));
    a.append(tags);
  }
  a.addEventListener("click", () => {
    markRead(post.url);
    a.classList.add("read");
  });
  return a;
}

function visiblePosts() {
  const company = $("company").value;
  const tag = $("tag").value;
  const unreadOnly = $("unread").checked;
  return state.posts.filter((p) =>
    (!company || p.company === company) &&
    (!tag || (p.tags || []).includes(tag)) &&
    (!unreadOnly || !state.read.has(p.url)));
}

function render() {
  const feed = $("feed");
  feed.replaceChildren();
  const posts = visiblePosts();
  if (!posts.length) {
    feed.append(el("p", "empty", "No posts to show."));
    return;
  }
  let day = null;
  for (const post of posts) {
    if (post.published !== day) {
      day = post.published;
      feed.append(el("h2", null, formatDay(day)));
    }
    feed.append(card(post));
  }
}

function fillSelect(select, values) {
  [...new Set(values)].sort().forEach((v) => select.append(new Option(v, v)));
}

async function load() {
  try {
    const response = await fetch("data/posts.json", { cache: "no-cache" });
    state.posts = await response.json();
  } catch (err) {
    $("feed").append(el("p", "empty", "Could not load posts."));
    return;
  }
  fillSelect($("company"), state.posts.map((p) => p.company));
  fillSelect($("tag"), state.posts.flatMap((p) => p.tags || []));
  render();
}

["company", "tag", "unread"].forEach((id) => $(id).addEventListener("change", render));
load();

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("sw.js");
}
