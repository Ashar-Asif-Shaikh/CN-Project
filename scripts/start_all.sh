#!/usr/bin/env bash
# start_all.sh - Starts all 4 virtual machine services in the background

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$DIR/logs" "$DIR/run"

echo "=========================================================="
echo " Starting All Services (Single-Mac Network Topology)"
echo "=========================================================="

# Check if 10.0.0.1 loopback alias is active
if ifconfig lo0 | grep -q "10.0.0.1"; then
    MODE="ALIAS"
    DNS_IP="10.0.0.1"
    EDGE_IP="10.0.0.2"
    BACKEND_A_IP="10.0.0.3"
    BACKEND_B_IP="10.0.0.4"
    echo "[Mode] IP Alias Mode active (Virtual LAN 10.0.0.0/24)"
else
    MODE="LOCALHOST"
    DNS_IP="127.0.0.1"
    EDGE_IP="127.0.0.1"
    BACKEND_A_IP="127.0.0.1"
    BACKEND_B_IP="127.0.0.1"
    echo "[Mode] Localhost Mode (127.0.0.1) - Aliases not active"
    echo "       (Tip: Run 'sudo ./scripts/setup_network.sh' for 10.0.0.x IP aliases)"
fi

# Stop any existing instances first
"$DIR/scripts/stop_all.sh" >/dev/null 2>&1 || true

# 1. Start Backend A (Mac 3)
echo "[1/4] Starting Mac 3: Backend A on $BACKEND_A_IP:3001..."
python3 "$DIR/backend/backend_a.py" "$BACKEND_A_IP" 3001 > "$DIR/logs/backend_a.log" 2>&1 &
echo $! > "$DIR/run/backend_a.pid"

# 2. Start Backend B (Mac 4)
echo "[2/4] Starting Mac 4: Backend B on $BACKEND_B_IP:3002..."
python3 "$DIR/backend/backend_b.py" "$BACKEND_B_IP" 3002 > "$DIR/logs/backend_b.log" 2>&1 &
echo $! > "$DIR/run/backend_b.pid"

# Wait a second for backends to start
sleep 1

# 3. Start Edge Reverse Proxy & Load Balancer (Mac 2)
echo "[3/4] Starting Mac 2: Edge Reverse Proxy on $EDGE_IP:8443 (TLS)..."
python3 "$DIR/proxy/load_balancer.py" \
  --host "$EDGE_IP" \
  --port 8443 \
  --cert "$DIR/certs/server.crt" \
  --key "$DIR/certs/server.key" \
  --backend-a-host "$BACKEND_A_IP" \
  --backend-a-port 3001 \
  --backend-b-host "$BACKEND_B_IP" \
  --backend-b-port 3002 \
  > "$DIR/logs/proxy.log" 2>&1 &
echo $! > "$DIR/run/proxy.pid"

# 4. Start DNS Server (Mac 1)
# Note: Port 53 requires sudo. If not root, check if we can run or use port 53 / 5353.
echo "[4/4] Starting Mac 1: Private DNS Server on $DNS_IP:53..."
if [ "$EUID" -eq 0 ]; then
    python3 "$DIR/dns/dns_server.py" --host "$DNS_IP" --port 53 --target-ip "$EDGE_IP" > "$DIR/logs/dns.log" 2>&1 &
    echo $! > "$DIR/run/dns.pid"
else
    # Attempt port 53 via sudo or fallback to port 5353
    if sudo -n true 2>/dev/null; then
        sudo python3 "$DIR/dns/dns_server.py" --host "$DNS_IP" --port 53 --target-ip "$EDGE_IP" > "$DIR/logs/dns.log" 2>&1 &
        echo $! > "$DIR/run/dns.pid"
    else
        echo "  Notice: Port 53 binding needs sudo. Starting DNS with sudo prompt:"
        sudo python3 "$DIR/dns/dns_server.py" --host "$DNS_IP" --port 53 --target-ip "$EDGE_IP" > "$DIR/logs/dns.log" 2>&1 &
        echo $! > "$DIR/run/dns.pid"
    fi
fi

sleep 1
echo ""
echo "=========================================================="
echo " All 4 Virtual Services are Running!"
echo "   - Mac 1 (DNS Server)      : $DNS_IP:53 (UDP)"
echo "   - Mac 2 (Edge Proxy / LB) : https://$EDGE_IP:8443 (HTTPS)"
echo "   - Mac 3 (Backend A)       : http://$BACKEND_A_IP:3001"
echo "   - Mac 4 (Backend B)       : http://$BACKEND_B_IP:3002"
echo " Logs directory: $DIR/logs/"
echo " To stop all services: ./scripts/stop_all.sh"
echo "=========================================================="
