#!/usr/bin/env bash
# setup_network.sh - Configures Single-Mac Virtual LAN Topology for CN Project
# Creates IP aliases on lo0 and macOS DNS resolver for *.test domains.

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=========================================================="
echo " Setting up Single-Mac Virtual Network Topology"
echo " Course: Computer Networks Course Project"
echo "=========================================================="

echo "[1/3] Adding Loopback IP Aliases to interface lo0..."
sudo ifconfig lo0 alias 10.0.0.1 255.255.255.0  # Mac 1: DNS Server
sudo ifconfig lo0 alias 10.0.0.2 255.255.255.0  # Mac 2: Edge Proxy / Load Balancer
sudo ifconfig lo0 alias 10.0.0.3 255.255.255.0  # Mac 3: Backend Server A
sudo ifconfig lo0 alias 10.0.0.4 255.255.255.0  # Mac 4: Backend Server B
sudo ifconfig lo0 alias 10.0.0.5 255.255.255.0  # Mac 5: Backup DNS (Phase 2 Ext A)
sudo ifconfig lo0 alias 10.0.0.6 255.255.255.0  # Mac 6: Standby Edge (Phase 2 Ext E)
echo "  ✓ Loopback aliases configured (10.0.0.1 - 10.0.0.6)"

echo "[2/3] Configuring macOS resolver for *.test domains (/etc/resolver/test)..."
sudo mkdir -p /etc/resolver
cat << 'EOF' | sudo tee /etc/resolver/test > /dev/null
# CN Project DNS Resolver
nameserver 10.0.0.1
port 53
EOF
echo "  ✓ Any *.test query will be routed to Mac 1 (10.0.0.1:53)"

echo "[3/3] Trusting Project Root CA in macOS System Keychain..."
if [ -f "$DIR/certs/ca.crt" ]; then
    sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain "$DIR/certs/ca.crt" || true
    echo "  ✓ CA certificate trusted (curl/browser works without -k)"
else
    echo "  ! ca.crt not found, generating now..."
    "$DIR/certs/generate_certs.sh"
    sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain "$DIR/certs/ca.crt" || true
fi

# Create logs and run directory
mkdir -p "$DIR/logs" "$DIR/run"

echo ""
echo "=========================================================="
echo " Single-Mac Topology Setup Complete!"
echo " Virtual Machines & Assigned IPs:"
echo "   - Mac 1 (DNS Server)      : 10.0.0.1"
echo "   - Mac 2 (Edge / Nginx)    : 10.0.0.2 (Port 8443)"
echo "   - Mac 3 (Backend A)       : 10.0.0.3 (Port 3001)"
echo "   - Mac 4 (Backend B)       : 10.0.0.4 (Port 3002)"
echo "   - Mac 5 (Backup DNS)      : 10.0.0.5"
echo "   - Mac 6 (Standby Edge)    : 10.0.0.6"
echo "=========================================================="
