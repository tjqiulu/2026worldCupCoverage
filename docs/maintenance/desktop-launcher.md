# Desktop Launcher (Plan 013)

> One-command desktop launcher: starts Flask + opens browser in fullscreen kiosk mode.

## What it does

`bin/launch.py` is a Python script that:

1. Starts the Flask app (`src/app.py`) as a background subprocess
2. Waits for the HTTP server to respond (health check)
3. Detects an installed browser (chromium / google-chrome / firefox)
4. Launches the browser in **kiosk mode** (fullscreen, no browser chrome)
5. Blocks until the browser is closed
6. Sends SIGTERM to Flask to shut it down cleanly
7. Exits

## How to use

```bash
# Default: start Flask + open browser in kiosk
cd /home/lqiu/.openclaw/workspace/2026worldCupCoverage
python3 bin/launch.py

# Or via shell wrapper
./bin/start.sh

# Debug mode: just start Flask, no browser
python3 bin/launch.py --no-browser

# Use a specific browser
python3 bin/launch.py --browser firefox

# Custom URL (if Flask is on a different port)
python3 bin/launch.py --url http://localhost:5000
```

To stop the app: **close the browser window** (Ctrl+W or click the X). Flask will shut down automatically.

## Browser support

Detection order (first match wins):

| Browser | Command | Tested |
|----------|---------|--------|
| Chromium | `chromium-browser` | ✓ |
| Chromium | `chromium` | ✓ |
| Google Chrome | `google-chrome` | ✓ |
| Google Chrome (alt) | `chrome` | ✓ |
| Firefox | `firefox` | ✓ |
| Chrome (Debian) | `google-chrome-stable` | ✓ |

### Install a browser (if missing)

```bash
# Debian / Ubuntu
sudo apt install chromium

# Fedora / RHEL
sudo dnf install chromium

# macOS (Chrome already installed at /Applications)
# Should be auto-detected

# Windows
# Install Chrome or Firefox, ensure on PATH
```

## Kiosk mode args

| Browser | Args |
|---------|------|
| Chrome/Chromium | `--kiosk --noerrdialogs --disable-infobars --disable-features=Translate --no-first-run` |
| Firefox | `--kiosk --new-instance` |

`--kiosk` puts the browser in fullscreen, hides all chrome (URL bar, tabs, etc).

## Troubleshooting

### "No browser found"

```
[launcher] ERROR: No supported browser found.
  Install one of: chromium-browser, chromium, google-chrome, firefox
  Or use --no-browser to run without GUI
```

Install a browser (see above) or use `--no-browser` for headless use.

### Flask didn't start in 30s

```
[launcher] ERROR: Flask did not start within 30s
```

Possible causes:
- Port 8766 is already in use → run with `--url http://localhost:OTHER_PORT` (and update app.py)
- `playwright` not installed → `pip install --user playwright`
- `flag-icons` CDN blocked → check network

Increase timeout: `--health-timeout 60`

### Browser opens but shows "Site can't be reached"

The browser was launched BEFORE Flask was ready. This shouldn't happen with the health check, but if it does:
- Increase `--health-timeout`
- Or run `--no-browser` first to verify Flask works, then try again

## Why not a real desktop app (Electron / Tauri)?

Reasons we chose the launcher approach:
- **Simpler**: no build step, no packaging
- **Smaller**: zero new dependencies
- **Cross-platform**: works on any OS with Python 3 + a browser
- **Maintainable**: launcher is ~200 lines of Python
- **Honest**: the app IS a web app; kiosk mode gives the desktop experience

If you want a true desktop binary (single .exe / .dmg / .AppImage), consider:
- **Tauri**: Rust + WebView, ~5MB binary
- **Electron**: Chromium + Node, ~150MB binary
- **PWA**: Make the Flask app a Progressive Web App with `manifest.json` + service worker

(PWA would be the cheapest upgrade — ~20 lines of HTML/JS. Could be Plan 014.)

## Files

- `bin/launch.py` — the launcher (Python)
- `bin/start.sh` — shell wrapper (calls `launch.py`)
- `tests/test_launch.py` — unit tests (14 cases)
- `docs/plans/013-desktop-launcher.md` — the plan
