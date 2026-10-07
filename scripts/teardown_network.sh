#!/usr/bin/env bash
# teardown_network.sh - Clean rollback of all single-mac network aliases and resolvers

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=========================================================="
echo " Tearing down Single-Mac Virtual Network Configuration"
echo "=========================================================="

# Stop any running services
"$DIR/scripts/stop_all.sh" 2>/dev/null || true

echo "[1/3] Removing IP aliases from interface lo0..."
sudo ifconfig lo0 -alias 10.0.0.1 2>/dev/null || true
sudo ifconfig lo0 -alias 10.0.0.2 2>/dev/null || true
sudo ifconfig lo0 -alias 10.0.0.3 2>/dev/null || true
sudo ifconfig lo0 -alias 10.0.0.4 2>/dev/null || true
sudo ifconfig lo0 -alias 10.0.0.5 2>/dev/null || true
sudo ifconfig lo0 -alias 10.0.0.6 2>/dev/null || true
echo "  ✓ Loopback aliases removed"

echo "[2/3] Removing /etc/resolver/test..."
sudo rm -f /etc/resolver/test
echo "  ✓ Resolver configuration removed"

echo "[3/3] Removing Project Root CA from macOS Keychain..."
if [ -f "$DIR/certs/ca.crt" ]; then
    sudo security remove-trusted-cert -d "$DIR/certs/ca.crt" 2>/dev/null || true
    echo "  ✓ CA certificate removed from Keychain"
fi

echo "=========================================================="
echo " System Restored to Original State."
echo "=========================================================="
