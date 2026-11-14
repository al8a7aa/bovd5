/* BÖVD service worker – caches the static UI so the app shell opens offline.
   API calls are never cached (health data stays in the encrypted local database). */
const CACHE = "bovd-v2";
const ASSETS = ["/", "/index.html", "/styles.css", "/i18n.js", "/app.js", "/voice.js", "/features.js", "/brand.js", "/motion.js", "/body3d.js", "/pose.js", "/science.js", "/tour.js", "/icon.svg", "/manifest.webmanifest"];
self.addEventListener("install", (e) => e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS))));
self.addEventListener("activate", (e) => e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k))))));
self.addEventListener("fetch", (e) => {
  const u = new URL(e.request.url);
  if (u.pathname.startsWith("/api/") || u.pathname.startsWith("/media/") || e.request.method !== "GET") return;
  e.respondWith(fetch(e.request).then((r) => { const cp = r.clone(); caches.open(CACHE).then((c) => c.put(e.request, cp)); return r; }).catch(() => caches.match(e.request)));
});
