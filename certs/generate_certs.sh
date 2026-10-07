#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "=========================================================="
echo " Generating TLS Certificates with Subject Alternative Names"
echo " Course: Computer Networks Project (Team 1)"
echo " Domains: app.team1.test, api.team1.test, localhost"
echo "=========================================================="

# 1. Generate Root CA private key and certificate
echo "[1/4] Generating Private Root CA key & certificate..."
openssl req -x509 -new -nodes -keyout ca.key -sha256 -days 365 \
  -out ca.crt \
  -subj "/C=IN/ST=Karnataka/L=Bengaluru/O=CN Team CA/OU=Root/CN=CN-Team1-Local-CA" \
  -config openssl_san.cnf \
  -extensions v3_ca

# 2. Generate Server private key
echo "[2/4] Generating Server private key..."
openssl genrsa -out server.key 2048

# 3. Generate Certificate Signing Request (CSR)
echo "[3/4] Generating Certificate Signing Request (CSR)..."
openssl req -new -key server.key -out server.csr \
  -config openssl_san.cnf

# 4. Sign the Server Certificate with our Root CA
echo "[4/4] Signing Server Certificate with Root CA..."
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt -days 365 -sha256 \
  -extfile openssl_san.cnf -extensions v3_server

echo ""
echo "=========================================================="
echo " Certificates Generated Successfully in $DIR:"
echo "   - ca.crt      (Root Certificate Authority)"
echo "   - ca.key      (Root CA Private Key)"
echo "   - server.crt  (Edge Server TLS Certificate)"
echo "   - server.key  (Edge Server Private Key)"
echo "=========================================================="
echo ""
echo "To trust the Root CA on macOS so curl/browsers don't warn (NO -k needed):"
echo "Run this command in your terminal:"
echo "  sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain \"$DIR/ca.crt\""
echo ""
echo "To remove it later when the project evaluation is done:"
echo "  sudo security remove-trusted-cert -d \"$DIR/ca.crt\""
echo "=========================================================="
