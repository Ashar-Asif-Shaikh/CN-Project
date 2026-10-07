#!/usr/bin/env bash
# stop_all.sh - Gracefully terminates all background services

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Stopping all project services..."

# Kill by PID if recorded
for pidfile in "$DIR/run"/*.pid; do
    if [ -f "$pidfile" ]; then
        PID=$(cat "$pidfile")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID" 2>/dev/null || sudo kill "$PID" 2>/dev/null || true
        fi
        rm -f "$pidfile"
    fi
done

# Secondary safety kill by process pattern
pkill -f "dns/dns_server.py" 2>/dev/null || sudo pkill -f "dns/dns_server.py" 2>/dev/null || true
pkill -f "proxy/load_balancer.py" 2>/dev/null || true
pkill -f "backend/backend_a.py" 2>/dev/null || true
pkill -f "backend/backend_b.py" 2>/dev/null || true
pkill -f "nginx -c" 2>/dev/null || true

echo "All services stopped."
