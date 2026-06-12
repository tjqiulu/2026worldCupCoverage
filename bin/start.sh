#!/bin/bash
# Desktop launcher wrapper.
# Convenience: ./bin/start.sh  →  python3 bin/launch.py
set -e
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_ROOT"
exec python3 "$SCRIPT_DIR/launch.py" "$@"
