// 2026 World Cup Coverage - Service Worker
// Cache shell for offline use; /api/* always network-first
const CACHE_VERSION = 'wc2026-v2';
const CACHE_NAME = `${CACHE_VERSION}-shell`;
const SHELL_URLS = [
    '/',
    '/static/css/main.css',
    '/static/js/main.js',
    '/static/manifest.json',
    '/static/img/icon.svg',
    'https://cdn.jsdelivr.net/gh/lipis/flag-icons@6.6.6/css/flag-icons.min.css',
];

// Install: cache shell
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            // Use addAll with individual catches so one failure doesn't kill all
            return Promise.all(
                SHELL_URLS.map((url) =>
                    cache.add(url).catch((err) => {
                        console.warn(`SW: failed to cache ${url}: ${err}`);
                    })
                )
            );
        }).then(() => {
            return self.skipWaiting();
        })
    );
});

// Activate: cleanup old caches
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys
                    .filter((key) => key.startsWith('wc2026-') && key !== CACHE_NAME)
                    .map((key) => caches.delete(key))
            );
        }).then(() => {
            return self.clients.claim();
        })
    );
});

// Fetch: network-first for /api/*, cache-first for shell
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // API calls: always network (no caching)
    if (url.pathname.startsWith('/api/')) {
        return;  // default browser behavior (network)
    }

    // External CDN (flag-icons): stale-while-revalidate
    if (url.hostname === 'cdn.jsdelivr.net') {
        event.respondWith(
            caches.open(CACHE_NAME).then((cache) => {
                return cache.match(event.request).then((cached) => {
                    const fetchPromise = fetch(event.request).then((response) => {
                        if (response && response.ok) {
                            cache.put(event.request, response.clone());
                        }
                        return response;
                    }).catch(() => cached);
                    return cached || fetchPromise;
                });
            })
        );
        return;
    }

    // Same-origin (HTML, CSS, JS, manifest, icons): cache-first
    if (url.origin === self.location.origin) {
        event.respondWith(
            caches.match(event.request).then((cached) => {
                if (cached) {
                    return cached;
                }
                return fetch(event.request).then((response) => {
                    if (response && response.ok) {
                        const clone = response.clone();
                        caches.open(CACHE_NAME).then((cache) => {
                            cache.put(event.request, clone);
                        });
                    }
                    return response;
                });
            })
        );
        return;
    }
});
