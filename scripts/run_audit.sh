#!/usr/bin/env bash
# Run the 8-gate audit and start/restart the dev server.
#
# Usage:
#   scripts/run_audit.sh            # audit (assumes server is up)
#   scripts/run_audit.sh --restart  # kill old server, start new, audit
#   scripts/run_audit.sh --start    # start server in background (no audit)
#
# Exit code 0 = all 8 gates pass, safe to declare done.
# Exit code 1 = at least one gate failed (DO NOT commit).
set -e
cd "$(dirname "$0")/.."

PORT=8766
PID=$(pgrep -f "src.app" | head -1 || true)

start_server() {
    if [ -n "$PID" ]; then
        echo "Server already running (pid $PID) on port $PORT"
        return
    fi
    echo "Starting dev server on port $PORT..."
    nohup env PYTHONPATH=. python3 -m src.app > /tmp/wc_server.log 2>&1 &
    disown
    sleep 4
    # Health check
    for i in 1 2 3 4 5; do
        if curl -s -m 2 "http://127.0.0.1:$PORT/api/health" >/dev/null; then
            echo "✓ Server up (pid $(pgrep -f 'src.app' | head -1))"
            return
        fi
        sleep 1
    done
    echo "✗ Server failed to start. Check /tmp/wc_server.log"
    tail -20 /tmp/wc_server.log
    exit 1
}

restart_server() {
    echo "Killing old server (pid $PID)..."
    [ -n "$PID" ] && kill -9 $PID 2>/dev/null || true
    sleep 1
    start_server
}

run_audit() {
    echo
    echo "================================================================"
    echo "8-GATE AUDIT (Plan 016 follow-up)"
    echo "================================================================"
    PYTHONPATH=. python3 tests/audit_gates.py
}

case "${1:-audit}" in
    --restart)
        restart_server
        run_audit
        ;;
    --start)
        start_server
        ;;
    audit|"")
        start_server
        run_audit
        ;;
    *)
        echo "Usage: $0 [--restart|--start|audit]"
        exit 2
        ;;
esac
