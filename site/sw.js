// Network-first for same-origin GETs, falling back to the cache so the last digest opens offline.
const CACHE = "digest-v1";
const SHELL = ["./", "index.html", "app.js", "style.css", "manifest.webmanifest", "icons/icon-192.png", "data/posts.json"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) =>
      Promise.all(SHELL.map((url) => c.add(url).catch(() => {})))));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET" || new URL(req.url).origin !== self.location.origin) return;
  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res.ok) {
          const copy = res.clone();
          event.waitUntil(
            caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {}));
        }
        return res;
      })
      .catch(async () => {
        const hit = await caches.match(req, { ignoreSearch: true });
        if (hit) return hit;
        if (req.mode === "navigate") {
          const shell = await caches.match("./");
          if (shell) return shell;
        }
        return Response.error();
      }));
});
