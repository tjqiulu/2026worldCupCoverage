# PWA (Progressive Web App) (Plan 014)

> The app is installable as a PWA from any modern browser. Desktop kiosk mode is handled by the [Desktop Launcher](./desktop-launcher.md) — this doc covers the **browser-install** path.

## What it does

The app meets the baseline PWA install criteria, so Chrome / Edge / Android / iOS will offer "Install App" out of the box:

1. **Web App Manifest** (`static/manifest.json`) — declares name, icons, theme color, start URL, display mode.
2. **Service Worker** (`static/sw.js`) — caches the app shell so the page works offline; refreshes `/api/*` from network.
3. **Install button** — a "📲 安装" button in the header appears only after the browser fires `beforeinstallprompt` (i.e., the browser has decided the site is installable).

## How to install (user-side)

1. Open `http://127.0.0.1:8766` in Chrome / Edge.
2. Look for the **📲 安装** button in the top-right header (it shows up after the page has finished loading + SW is active).
3. Click it → browser shows install dialog → confirm.
4. The app icon appears in your launcher / desktop. Opens in fullscreen, no URL bar.

On iOS Safari: tap Share → "Add to Home Screen" (the button is hidden on Safari because Safari does not fire `beforeinstallprompt`).

## What's in scope

- **Offline shell** — the app shell (HTML / CSS / JS / manifest / icons / flag-icons CSS) is cached and served cache-first.
- **Fresh API** — `/api/*` requests always hit the network (never cached) so match scores stay current.
- **Installability** — meets the install criteria; both desktop and mobile browsers will offer the install prompt.
- **Shortcuts** — manifest declares "赛程 Matches" and "对阵 Bracket" shortcuts (right-click the installed icon to see them).

## What's NOT in scope

- ❌ Push notifications
- ❌ Background sync
- ❌ Web Share API / WebRTC
- ❌ Custom PNG icon design (the icons are auto-rasterized from `icon.svg` via Inkscape / rsvg-convert)
- ❌ Full iOS Safari PWA polish (Safari has limited PWA support)

## Files

| File | Purpose |
|------|---------|
| `static/manifest.json` | PWA manifest (name, icons, display: standalone) |
| `static/sw.js` | Service Worker (install / activate / fetch handlers) |
| `static/img/icon.svg` | Source icon (used by browser + rasterized to PNG) |
| `static/img/icon-192.png` | 192×192 PNG (small icon) |
| `static/img/icon-512.png` | 512×512 PNG (large + maskable) |
| `tests/e2e/test_pwa.py` | 15 e2e tests covering manifest / icons / SW / HTML / install |

## Cache strategy

| Request type | Strategy | Why |
|--------------|----------|-----|
| `/static/*` (CSS, JS, manifest, icons) | **cache-first** | Static, versioned; offline-first |
| `/api/*` (matches, scores) | **network-first (no SW)** | Always fresh; never show stale scores |
| `cdn.jsdelivr.net/.../flag-icons.min.css` | **stale-while-revalidate** | Show cached version immediately, refresh in background |
| Other (none expected) | **default browser** | Pass through |

Cache name: `wc2026-v1-shell`. Bump the `CACHE_VERSION` constant in `sw.js` when you ship a new app shell and old caches will be cleaned up on activate.

## Updating the app (cache invalidation)

When you change HTML / CSS / JS / icons:

1. Bump `CACHE_VERSION` in `static/sw.js` (e.g., `wc2026-v1` → `wc2026-v2`).
2. Commit + deploy.
3. On next page load, the new SW installs in the background, then `skipWaiting()` makes it active immediately. Old `wc2026-v1-*` caches are deleted on activate.

API responses are not cached by the SW, so changes to match data do not require a cache bump.

## Updating the icons

1. Edit `static/img/icon.svg`.
2. Re-rasterize the PNGs:

   ```bash
   # Inkscape (preferred, full control)
   inkscape static/img/icon.svg -o static/img/icon-192.png -w 192
   inkscape static/img/icon.svg -o static/img/icon-512.png -w 512

   # Or rsvg-convert (faster, simpler)
   rsvg-convert -w 192 static/img/icon.svg -o static/img/icon-192.png
   rsvg-convert -w 512 static/img/icon.svg -o static/img/icon-512.png
   ```

3. Bump `CACHE_VERSION` in `sw.js` so users pick up the new icons.
4. Run `tests/e2e/test_pwa.py` to verify file sizes still pass the thresholds.

## Browser support

| Browser | Install | Offline | Notes |
|---------|---------|---------|-------|
| Chrome / Edge (desktop) | ✅ via button or URL-bar icon | ✅ | Full support |
| Android Chrome | ✅ via button | ✅ | Full support |
| iOS Safari | ⚠️ "Add to Home Screen" only | ⚠️ limited | Install button hidden; manual path |
| Firefox | ⚠️ limited | ✅ | Firefox has restricted PWA install |

The app is still fully functional as a regular website on any browser — PWA features are progressive enhancements, not requirements.

## Why the SW scope is `/static/`

The SW is registered at `/static/sw.js`, which gives it scope `/static/`. This means it **does not control the root page** (`/`). The home page HTML is therefore not controlled by the SW, but the page only loads static resources, which ARE served cache-first by the SW.

This is intentional:
- We don't want to cache the root HTML (the app is a single page; the root is just the shell).
- All interactive assets (CSS / JS / manifest / icons / flag-icons CSS) live under `/static/` and are cached.
- `/api/*` is never cached (always network-first), so we get the freshest data.

If you ever add more routes (e.g., `/about`, `/settings`), either:
- Add the route to the SW `fetch` handler so the route works offline, **or**
- Move the SW to `/sw.js` and add a `Service-Worker-Allowed: /` header so it can control the whole site.

## Running the tests

```bash
cd /home/lqiu/.openclaw/workspace/2026worldCupCoverage
PYTHONPATH=. python3 -m pytest tests/e2e/test_pwa.py -v
```

The tests start Flask, launch headless Chromium, and check:
- `manifest.json` is served and has required fields
- All icons are accessible
- SW file is served correctly
- SW registers successfully in the browser
- HTML has manifest link, theme color, apple-touch-icon
- Install button is in the DOM and hidden by default
- No console errors on page load
- Screenshot saved to `tests/e2e/screenshots/pwa_view.png`

## Troubleshooting

### Install button never shows up

The browser only fires `beforeinstallprompt` when **all** of the following are true:
- HTTPS or `localhost` / `127.0.0.1` (we use `127.0.0.1` for local dev)
- A valid manifest is linked from the HTML
- A service worker is registered
- The user has visited the site at least once
- The user has not already installed / dismissed the prompt recently

Check: open DevTools → Application → Manifest. If there's a yellow warning, the manifest is missing something. Application → Service Workers shows the SW status.

### Offline page is blank

1. Open DevTools → Application → Cache Storage.
2. Confirm `wc2026-v1-shell` exists and has entries.
3. If it's empty, the SW `install` event failed — check the console for errors. Most common cause: the flag-icons CDN was unreachable during install (the SW catches that error and continues, but if many shell URLs fail, the install may abort).

### Changes not visible after deploy

1. Hard-reload (Ctrl+Shift+R) to bypass HTTP cache.
2. Check `static/sw.js` has the new `CACHE_VERSION`.
3. In DevTools → Application → Service Workers, click "Unregister" + "Update" to force a fresh SW.
4. Re-test offline mode after the new SW is active.
