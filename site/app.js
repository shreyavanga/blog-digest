const READ_KEY = "blog-digest-read";
const SUMMARY_MAX = 300;

function loadRead() {
  try {
    const data = JSON.parse(localStorage.getItem(READ_KEY) || "[]");
    return new Set(Array.isArray(data) ? data : []);
  } catch (err) {
    return new Set();
  }
}

const state = {
  posts: [],
  read: loadRead(),
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
  try {
    localStorage.setItem(READ_KEY, JSON.stringify([...state.read]));
  } catch (err) {
    // storage unavailable or full; the card is still marked read for this session
  }
}

function formatDay(iso) {
  const date = new Date(iso + "T00:00:00");
  if (typeof iso !== "string" || isNaN(date.getTime())) return "Unknown date";
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
  const onOpen = () => {
    markRead(post.url);
    a.classList.add("read");
  };
  a.addEventListener("click", onOpen);
  a.addEventListener("auxclick", onOpen);
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
    if (!response.ok) throw new Error("HTTP " + response.status);
    const data = await response.json();
    if (!Array.isArray(data)) throw new Error("unexpected data");
    state.posts = data;
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
  navigator.serviceWorker.register("sw.js").catch(() => {});
}
