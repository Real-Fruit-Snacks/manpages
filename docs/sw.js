/* Service worker: precache the shell, stale-while-revalidate everything else.
   Version is stamped by build_site.py; a new corpus build invalidates all caches. */
var VERSION = '2026-07-10-20c9d17e';
var CACHE = 'manpages-' + VERSION;
var SHELL = [
  './', 'index.html', '404.html', 'about.html',
  'manifest.webmanifest', 'favicon.svg', 'favicon.ico',
  'assets/tokens.css', 'assets/app.css', 'assets/pet.css',
  'assets/app.js', 'assets/search-core.js', 'assets/pet.js',
  'assets/icon-192.png', 'assets/icon-512.png',
  'assets/fonts/JetBrainsMono-Regular.woff2', 'assets/fonts/JetBrainsMono-Bold.woff2',
  'assets/fonts/JetBrainsMono-Italic.woff2', 'assets/fonts/JetBrainsMono-BoldItalic.woff2',
  'data/index.js'
];

self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(SHELL); })
    .then(function () { return self.skipWaiting(); }));
});

self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k !== CACHE; })
      .map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

self.addEventListener('fetch', function (e) {
  if (e.request.method !== 'GET') return;
  var url = new URL(e.request.url);
  if (url.origin !== location.origin) return;
  e.respondWith(caches.open(CACHE).then(function (c) {
    return c.match(e.request).then(function (hit) {
      var refresh = fetch(e.request).then(function (res) {
        if (res && res.ok) c.put(e.request, res.clone());
        return res;
      }).catch(function () { return hit; });
      return hit || refresh;
    });
  }));
});
