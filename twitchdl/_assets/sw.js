/* Twitch Downloader — minimal, safe service worker (installable PWA + offline shell).
   Deliberately does NOT touch /api/ (the proxy), range requests, POSTs or cross-origin —
   so downloads are never intercepted. Stale-while-revalidate for same-origin GET pages/assets. */
const CACHE = "twdl-v2";

self.addEventListener("install", (e) => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(
  caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim())
));

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;                         // never touch POST (GQL proxy)
  if (req.headers.has("range")) return;                     // never touch media range fetches
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;          // never touch cross-origin
  if (url.pathname.startsWith("/api/")) return;             // never touch the proxy
  if (url.pathname.startsWith("/.netlify/")) return;

  // HTML documents: network-FIRST. Content (facts, prices, disclosures) must never be served
  // from a stale cache — a returning PWA user must not see yesterday's claims. Fall back to
  // cache only when offline. Assets stay stale-while-revalidate (fast, and safe to be a beat old).
  const isDoc = req.mode === "navigate" ||
    (req.headers.get("accept") || "").includes("text/html");

  event.respondWith(
    caches.open(CACHE).then(async (cache) => {
      const cached = await cache.match(req);
      const network = fetch(req).then((res) => {
        if (res && res.status === 200 && res.type === "basic") cache.put(req, res.clone());
        return res;
      }).catch(() => cached);
      return isDoc ? (network.then((r) => r || cached) || cached) : (cached || network);
    })
  );
});
