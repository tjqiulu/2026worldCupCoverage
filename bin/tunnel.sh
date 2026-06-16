#!/usr/bin/env bash
# Start Cloudflare quick tunnel (no account, no card).
# Mirrors bin/serve.sh interface for consistency.
#
# Usage:
#   bin/tunnel.sh                 # start in background, log to /tmp/cf_tunnel.log
#   bin/tunnel.sh --foreground    # run in foreground (Ctrl+C to stop)
#   bin/tunnel.sh --stop          # stop the running daemon
#   bin/tunnel.sh --status        # show if it's running + public URL
#   bin/tunnel.sh --url           # print just the public URL
#
# Requires:
#   - cloudflared installed (apt or ~/.local/bin/cloudflared)
#   - Flask running on http://localhost:8766 (start with bin/serve.sh)
#
# This is a "quick tunnel" — no Cloudflare account needed.
# URL is random and changes on each restart (e.g., https://abc-def-ghi.trycloudflare.com)
# For stable URLs, see Plan 022.1 (named tunnel with free Cloudflare account).
set -e
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_ROOT"

LOG=/tmp/cf_tunnel.log
PIDFILE=/tmp/cf_tunnel.pid
FLASK_URL=http://localhost:8766
TUNNEL_CMD="cloudflared tunnel --url $FLASK_URL"

# Ensure cloudflared is in PATH
if ! command -v cloudflared >/dev/null 2>&1; then
    # Try ~/.local/bin
    if [ -x "$HOME/.local/bin/cloudflared" ]; then
        export PATH="$HOME/.local/bin:$PATH"
    else
        echo "ERROR: cloudflared not found in PATH or ~/.local/bin/" >&2
        echo "Install: dpkg-deb -x <cloudflared.deb> /tmp/cf && cp /tmp/cf/usr/bin/cloudflared ~/.local/bin/" >&2
        exit 1
    fi
fi

start_detached() {
    if [ -f "$PIDFILE" ] && kill -0 $(cat "$PIDFILE") 2>/dev/null; then
        echo "Tunnel already running (pid $(cat $PIDFILE))"
        return
    fi
    # Double-fork to fully detach from the parent shell
    (
        setsid bash -c "exec nohup $TUNNEL_CMD > $LOG 2>&1 < /dev/null & echo \$! > $PIDFILE" \
            </dev/null >/dev/null 2>&1 &
    )
    # Wait for URL to appear in log (max 15s)
    for i in $(seq 1 15); do
        sleep 1
        if grep -qE 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG" 2>/dev/null; then
            PID=$(cat "$PIDFILE" 2>/dev/null)
            URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG" | head -1)
            echo "✓ Tunnel up (pid $PID)"
            echo "  Public URL: $URL"
            echo "  Log: $LOG"
            return
        fi
    done
    echo "✗ Tunnel didn't start in 15s. Last 10 log lines:"
    tail -10 "$LOG" 2>/dev/null
    exit 1
}

start_foreground() {
    echo "Starting cloudflared tunnel in foreground (Ctrl+C to stop)..."
    exec $TUNNEL_CMD
}

stop_daemon() {
    if [ ! -f "$PIDFILE" ]; then
        echo "No PID file. Nothing to stop."
        return
    fi
    PID=$(cat "$PIDFILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping tunnel (pid $PID)..."
        kill "$PID"
        for i in 1 2 3 4 5; do
            sleep 1
            if ! kill -0 "$PID" 2>/dev/null; then
                rm -f "$PIDFILE"
                echo "✓ Stopped"
                return
            fi
        done
        kill -9 "$PID" 2>/dev/null
        rm -f "$PIDFILE"
        echo "✓ Force-stopped"
    else
        echo "Stale PID file (pid $PID not running). Cleaning up."
        rm -f "$PIDFILE"
    fi
}

show_status() {
    if [ -f "$PIDFILE" ] && kill -0 $(cat "$PIDFILE") 2>/dev/null; then
        echo "Tunnel running (pid $(cat $PIDFILE))"
        URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG" 2>/dev/null | head -1)
        if [ -n "$URL" ]; then
            echo "Public URL: $URL"
        else
            echo "(URL not yet extracted from log)"
        fi
    else
        echo "Tunnel NOT running"
        return 1
    fi
}

print_url() {
    "$SCRIPT_DIR/tunnel-url.sh"
}

case "${1:-start}" in
    --foreground|-f) start_foreground ;;
    --stop)          stop_daemon ;;
    --status|-s)     show_status ;;
    --url)           print_url ;;
    --restart)
        stop_daemon || true
        sleep 1
        start_detached
        ;;
    start|"")        start_detached ;;
    *)
        echo "Usage: $0 [start|--foreground|--stop|--status|--url|--restart]"
        exit 2
        ;;
esac
