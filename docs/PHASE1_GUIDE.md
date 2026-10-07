# Phase 1 Execution & Wireshark Capture Guide

This guide walks you through setting up, testing, and collecting Wireshark evidence for all Phase 1 tasks on your Mac.

---

## 1. Quick Setup & Starting the Network

### Step 1: Set Up Network Aliases and macOS Resolver
Open your macOS Terminal and run:
```bash
cd /Users/ashar/.gemini/antigravity/scratch/cn-project
sudo ./scripts/setup_network.sh
```
This assigns `10.0.0.1` through `10.0.0.6` to interface `lo0`, registers `/etc/resolver/test`, and trusts the project root CA in your macOS keychain.

### Step 2: Start All Services
```bash
./scripts/start_all.sh
```
You should see:
* Mac 1 (DNS Server) listening on `10.0.0.1:53`
* Mac 2 (Edge Proxy / LB) listening on `https://10.0.0.2:8443`
* Mac 3 (Backend A) listening on `http://10.0.0.3:3001`
* Mac 4 (Backend B) listening on `http://10.0.0.4:3002`

---

## 2. Testing Each Protocol Layer

### Task B: Verify DNS Resolution
```bash
dig @10.0.0.1 app.team1.test +short
# Expected output: 10.0.0.2
```

### Task C & D: Verify Load Balancing Across Backends
Run curl repeatedly to see `X-Backend: A` and `X-Backend: B` alternate:
```bash
for i in {1..4}; do
  curl -s -i https://app.team1.test:8443/api/status | grep "X-Backend"
done
```
Output:
```
X-Backend: A
X-Backend: B
X-Backend: A
X-Backend: B
```

### Task E: Verify TLS Certificate (No `-k` flag!)
```bash
curl -v https://app.team1.test:8443/api/status
```
Notice:
* `SSL certificate verify ok`
* Subject Alternative Name matches `app.team1.test`
* HTTP/1.1 200 OK

### Task F: Verify HTTP Caching & Conditional Requests
1. **Check Cache-Control:**
```bash
curl -s -I https://app.team1.test:8443/api/status | grep -E "Cache-Control|ETag"
# Output:
# Cache-Control: max-age=60
# ETag: "backend-a-v1"
```

2. **Conditional GET returning 304 Not Modified:**
```bash
curl -s -i -H 'If-None-Match: "backend-a-v1"' https://app.team1.test:8443/api/status | head -n 5
# Output:
# HTTP/1.1 304 Not Modified
# ETag: "backend-a-v1"
```

---

## 3. Wireshark Packet Capture Guide (Task G Evidence)

Wireshark allows capturing full packet flows directly on your single Mac!

### Step 1: Select Interface
1. Launch **Wireshark**.
2. Double-click the **`Loopback: lo0`** interface.

### Step 2: Set Display Filter & Trigger Traffic
In the Wireshark filter bar at the top, enter:
```
udp.port == 53 or tcp.port == 8443 or tcp.port == 3001 or tcp.port == 3002
```
Now in your terminal, run:
```bash
curl -s https://app.team1.test:8443/api/status
```

### Step 3: Key Packets to Highlight for the Evaluator

| Protocol / Layer | Wireshark Display Filter | Packets to Observe |
|---|---|---|
| **DNS Query/Response** | `dns` | `Standard query 0x... A app.team1.test` and `Standard query response 0x... A 10.0.0.2` |
| **TCP 3-Way Handshake** | `tcp.port == 8443 and tcp.flags.syn == 1` | SYN from client to `10.0.0.2:8443`, SYN-ACK from `10.0.0.2:8443`, ACK from client |
| **TLS Handshake** | `tls` | `Client Hello` (with SNI `app.team1.test`), `Server Hello`, `Certificate`, `Key Exchange` |
| **Encrypted App Data** | `tls.record.content_type == 23` | `Application Data` packets (showing payload is encrypted on the wire) |
| **Edge-to-Backend HTTP**| `http and (tcp.port == 3001 or tcp.port == 3002)` | Unencrypted `GET /api/status HTTP/1.1` and HTTP 200 response with `X-Backend` header |

---

## 4. Phase 1 Required Failure Scenarios (Section 6.3)

Run `./scripts/demo_phase1.sh` to automatically demonstrate all 5 scenarios:

1. **Wrong DNS Server configured on client:**
   * Query non-existent DNS: `dig @10.0.0.99 app.team1.test`
   * *Observation:* DNS query times out; demonstrates DNS and IP layers are independent.
2. **DNS Record points to wrong IP address:**
   * Point DNS record to invalid host.
   * *Observation:* DNS resolution succeeds, but TCP connection fails; proves DNS is a directory, not a connection.
3. **One backend is stopped:**
   * Kill Backend A: `kill $(cat run/backend_a.pid)`
   * *Observation:* Requests seamlessly continue through Backend B only.
4. **Both backends are stopped:**
   * Kill both backends.
   * *Observation:* Edge Proxy returns `502 Bad Gateway`; shows boundary between Edge and Backend.
5. **Wrong destination port on client:**
   * Run `curl https://10.0.0.2:9999`
   * *Observation:* Host is reachable via IP/ping, but TCP handshake fails with connection refused.
