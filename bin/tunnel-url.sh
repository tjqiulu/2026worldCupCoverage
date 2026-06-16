#!/usr/bin/env bash
# Print the current Cloudflare quick tunnel URL from the log file.
# Usage: bin/tunnel-url.sh
set -e

LOG="/tmp/cf_tunnel.log"

if [ ! -f "$LOG" ]; then
    echo "ERROR: $LOG not found. Is the tunnel running?" >&2
    echo "" >&2
    echo "Start with:" >&2
    echo "  nohup cloudflared tunnel --url http://localhost:8766 > $LOG 2>&1 &" >&2
    exit 1
fi

URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG" | head -1)

if [ -z "$URL" ]; then
    echo "ERROR: no trycloudflare.com URL found in $LOG" >&2
    echo "Tunnel may still be starting. Last 10 log lines:" >&2
    tail -10 "$LOG" >&2
    exit 1
fi

echo "$URL"
