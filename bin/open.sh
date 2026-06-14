#!/usr/bin/env bash
# Start the WC 2026 server (if needed) and open it in a NORMAL browser window.
#
# Unlike bin/launch.py (kiosk fullscreen, blocks focus), this:
#   1. Starts Flask in the background (via serve.sh)
#   2. Detects an installed browser
#   3. Opens the URL in a normal resizable window (no --kiosk)
#   4. Returns immediately — the script does not block
#
# Usage:
#   bin/open.sh                # normal window
#   bin/open.sh --widget       # compact 380x500 floating card
#   bin/open.sh --size 1280x800
#
# Close with the browser's X button, or run `wcup-stop`.
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
PORT=8766
URL="http://127.0.0.1:$PORT"
SIZE=""
USE_WIDGET=0

while [ $# -gt 0 ]; do
    case "$1" in
        --widget)   USE_WIDGET=1; shift ;;
        --size)     SIZE="$2"; shift 2 ;;
        -h|--help)
            sed -n '2,18p' "$0"
            exit 0
            ;;
        *) echo "Unknown arg: $1"; exit 2 ;;
    esac
done

# 1. Make sure the server is up.
"$SCRIPT_DIR/serve.sh" --status >/dev/null 2>&1 || "$SCRIPT_DIR/serve.sh"

# 2. Pick a browser (normal-mode args — no --kiosk).
BROWSER=""
for b in chromium google-chrome chrome firefox; do
    if command -v "$b" >/dev/null 2>&1; then
        BROWSER="$b"
        break
    fi
done
if [ -z "$BROWSER" ]; then
    echo "✗ No browser found (chromium / google-chrome / firefox)."
    echo "  Server is up — open $URL manually."
    exit 1
fi

# 3. Build the URL.
FINAL_URL="$URL"
if [ "$USE_WIDGET" = "1" ]; then
    FINAL_URL="$URL/?view=widget"
    [ -z "$SIZE" ] && SIZE="380x500"
fi

# 4. Launch in a normal (resizable) window.
ARGS=(--new-window)
[ -n "$SIZE" ] && ARGS+=(--window-size="$SIZE")
ARGS+=("$FINAL_URL")

# Browser-specific quirks.
case "$BROWSER" in
    firefox)
        # Firefox uses -new-window and ignores --window-size; user can resize.
        ARGS=(-new-window "$FINAL_URL")
        ;;
esac

echo "✓ Opening $FINAL_URL in $BROWSER (normal window)"
"$BROWSER" "${ARGS[@]}" >/dev/null 2>&1 &
disown 2>/dev/null || true
