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

function pad2(n) {
  return String(n).padStart(2, "0");
}

// Returns YYYY-MM-DD (local date) for `days` before `now`, or null for "all".
function cutoffDate(days, now = new Date()) {
  if (days === "all") return null;
  const d = new Date(now.getFullYear(), now.getMonth(), now.getDate() - Number(days));
  return d.getFullYear() + "-" + pad2(d.getMonth() + 1) + "-" + pad2(d.getDate());
}

function inRange(post, cutoff) {
  if (cutoff === null) return true;
  const p = post && post.published;
  return typeof p === "string" && /^\d{4}-\d{2}-\d{2}$/.test(p) && p >= cutoff;
}

function rangePosts() {
  const cutoff = cutoffDate($("range").value);
  return state.posts.filter((p) => inRange(p, cutoff));
}

function visiblePosts() {
  const company = $("company").value;
  const tag = $("tag").value;
  const unreadOnly = $("unread").checked;
  return rangePosts().filter((p) =>
    (!company || p.company === company) &&
    (!tag || (p.tags || []).includes(tag)) &&
    (!unreadOnly || !state.read.has(p.url)));
}

function rangeWording(range) {
  if (range === "all") return null;
  return "in the last " + (range === "1" ? "day" : range + " days");
}

function render() {
  const feed = $("feed");
  feed.replaceChildren();
  const posts = visiblePosts();
  if (!posts.length) {
    const range = $("range").value;
    const wording = rangeWording(range);
    feed.append(el("p", "empty", wording ? "No posts " + wording + "." : "No posts to show."));
    if (range !== "all") feed.append(el("p", "empty", "Try a longer time range."));
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

// The company list always covers every stored post, so any company can be picked regardless of date.
function rebuildCompanies() {
  const select = $("company");
  const previous = select.value;
  select.options.length = 1;
  fillSelect(select, state.posts.map((p) => p.company));
  select.value = [...select.options].some((o) => o.value === previous) ? previous : "";
}

// Topics come from the posts matching the current time range and company.
function rebuildTags() {
  const company = $("company").value;
  const posts = rangePosts().filter((p) => !company || p.company === company);
  const select = $("tag");
  const previous = select.value;
  select.options.length = 1;
  fillSelect(select, posts.flatMap((p) => p.tags || []));
  select.value = [...select.options].some((o) => o.value === previous) ? previous : "";
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
  rebuildCompanies();
  rebuildTags();
  render();
}

["tag", "unread"].forEach((id) => $(id).addEventListener("change", render));

// Picking a company shows all of its stored posts (time range switches to "All");
// clearing the company puts the previous time range back.
$("company").addEventListener("change", () => {
  const range = $("range");
  if ($("company").value) {
    if (range.value !== "all") {
      state.rangeBeforeCompany = range.value;
      range.value = "all";
    }
  } else if (state.rangeBeforeCompany && range.value === "all") {
    range.value = state.rangeBeforeCompany;
    state.rangeBeforeCompany = null;
  } else {
    state.rangeBeforeCompany = null;
  }
  rebuildTags();
  render();
});

$("range").addEventListener("change", () => {
  state.rangeBeforeCompany = null;
  rebuildTags();
  render();
});
load();

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("sw.js").catch(() => {});
}
