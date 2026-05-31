/* Jordan's Recipes — service worker */
const CACHE_VERSION = 'recipes-0b86ccd3';
const SHELL = [
  '/',
  '/index.html',
  '/assets/style.css?v=0b86ccd3',
  '/assets/app.js?v=0b86ccd3',
  '/manifest.json',
  '/app-icons/icon-192.png',
  '/app-icons/icon-512.png',
  '/app-icons/icon-180.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => cache.addAll(SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  // PDFs are large — let them hit the network directly.
  if (url.pathname.startsWith('/pdfs/')) return;

  event.respondWith(
    fetch(req)
      .then((resp) => {
        if (resp && resp.ok && resp.type === 'basic') {
          const copy = resp.clone();
          caches.open(CACHE_VERSION).then((cache) => cache.put(req, copy));
        }
        return resp;
      })
      .catch(() => caches.match(req).then((hit) => hit || caches.match('/index.html')))
  );
});
