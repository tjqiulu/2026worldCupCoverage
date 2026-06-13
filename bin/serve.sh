#!/usr/bin/env bash
# Start Flask as a detached daemon (survives shell exit).
#
# Usage:
#   bin/serve.sh                 # start in background, log to /tmp/wc_server.log
#   bin/serve.sh --foreground    # run in foreground (Ctrl+C to stop)
#   bin/serve.sh --stop          # stop the running daemon
#   bin/serve.sh --status        # show if it's running
#
# This is the recommended way to run the server for daily use:
#   $ bin/serve.sh
#   ✓ Server up (pid 12345)
# Then open http://127.0.0.1:8766 in any browser.
#
# To stop later: bin/serve.sh --stop
set -e
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_ROOT"

LOG=/tmp/wc_server.log
PIDFILE=/tmp/wc_server.pid
PORT=8766

start_detached() {
    if [ -f "$PIDFILE" ] && kill -0 $(cat "$PIDFILE") 2>/dev/null; then
        echo "Server already running (pid $(cat $PIDFILE))"
        return
    fi
    # Double-fork to fully detach from the parent shell.
    # This pattern works in OpenClaw exec sessions which would otherwise
    # propagate a SIGHUP/SIGTERM to the child on exit.
    (
        setsid bash -c "exec nohup env PYTHONPATH=. python3 -m src.app > $LOG 2>&1 < /dev/null & echo \$! > $PIDFILE" \
            </dev/null >/dev/null 2>&1 &
    )
    for i in 1 2 3 4 5 6 7 8; do
        sleep 1
        if curl -s -m 2 "http://127.0.0.1:$PORT/api/health" >/dev/null; then
            PID=$(cat "$PIDFILE" 2>/dev/null)
            echo "✓ Server up (pid $PID), log: $LOG"
            echo "  Open: http://127.0.0.1:$PORT"
            return
        fi
    done
    echo "✗ Server failed to start in 8s"
    tail -20 "$LOG" 2>/dev/null || true
    exit 1
}

start_foreground() {
    echo "Starting Flask in foreground on port $PORT (Ctrl+C to stop)..."
    exec env PYTHONPATH=. python3 -m src.app
}

stop_daemon() {
    if [ ! -f "$PIDFILE" ]; then
        echo "No PID file. Nothing to stop."
        return
    fi
    PID=$(cat "$PIDFILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping server (pid $PID)..."
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
        echo "Server running (pid $(cat $PIDFILE))"
        curl -s "http://127.0.0.1:$PORT/api/health"
    else
        echo "Server NOT running"
        return 1
    fi
}

case "${1:-start}" in
    --foreground|-f) start_foreground ;;
    --stop)          stop_daemon ;;
    --status|-s)     show_status ;;
    --restart)
        stop_daemon || true
        sleep 1
        start_detached
        ;;
    start|"")        start_detached ;;
    *)
        echo "Usage: $0 [start|--foreground|--stop|--status|--restart]"
        exit 2
        ;;
esac
