'use strict';
// Release number mirrors boiler-room.json; changing it invalidates the app shell.
const RELEASE = 2;
const BASE = new URL(self.registration.scope);
const PREFIX = `strike-shell:${BASE.href}:`;
const CACHE = `${PREFIX}${RELEASE}`;
const META = new URL('boiler-room.json', BASE).href;
const ENTRY = new URL('index.html', BASE).href;

self.addEventListener('install', event => {
  // Install only a complete shell. Keep the previous active worker until all
  // its clients close; never force a reload that would lose a working kit.
  event.waitUntil((async () => {
    const response = await fetch(META, {cache: 'reload'});
    if (!response.ok) throw new Error('Boiler Room metadata unavailable');
    const data = await response.clone().json();
    if (data.schema_version !== 2 || data.version !== RELEASE || !Array.isArray(data.files)) {
      throw new Error('Release metadata mismatch');
    }
    const urls = data.files.map(file => {
      const url = new URL(file, BASE);
      if (!url.href.startsWith(BASE.href) || url.search || url.hash) throw new Error('Invalid offline path');
      return url.href;
    });
    if (!urls.includes(ENTRY) || !urls.includes(META)) throw new Error('Incomplete app shell');
    const resources = await Promise.all(urls.map(async url => {
      const res = url === META ? response : await fetch(url, {cache: 'reload'});
      if (!res.ok || res.redirected) throw new Error(`Offline resource unavailable: ${url}`);
      return [url, res];
    }));
    const cache = await caches.open(CACHE);
    // A failure prevents activation. Do not remove another worker's active cache.
    await Promise.all(resources.map(([url, res]) => cache.put(url, res)));
  })());
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names.filter(name => name.startsWith(PREFIX) && name !== CACHE).map(name => caches.delete(name)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET' || req.headers.has('range')) return;
  const url = new URL(req.url);
  if (url.origin !== BASE.origin || !url.pathname.startsWith(BASE.pathname)) return;
  // Both the directory URL and explicit entry work offline, including queries.
  const isEntry = req.mode === 'navigate' && (url.pathname === BASE.pathname || url.pathname === new URL(ENTRY).pathname);
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const cached = await cache.match(isEntry ? ENTRY : req);
    return cached || fetch(req);
  })());
});
