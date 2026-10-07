# Phase 2 Resilience, Hardening & Troubleshooting Guide

This guide covers all Phase 2 extensions and troubleshooting scenarios for your evaluation.

---

## Extension A: Backup DNS Resolver

* **Goal:** Run a secondary DNS server and demonstrate seamless name resolution when the primary fails.
* **Topology:**
  * Primary DNS (Mac 1): `10.0.0.1:53`
  * Backup DNS (Mac 5): `10.0.0.5:5354`
* **Test Steps:**
  1. Start Backup DNS:
     ```bash
     python3 dns/dns_server.py --host 10.0.0.5 --port 5354 --target-ip 10.0.0.2 --role "Backup DNS"
     ```
  2. Verify Backup DNS resolves the domain:
     ```bash
     dig @10.0.0.5 -p 5354 app.team1.test +short
     # Returns: 10.0.0.2
     ```
  3. Stop Primary DNS (`pkill -f "Primary DNS"`).
  4. Query Backup DNS to prove clients still receive answers.

---

## Extension B: DNS TTL and Controlled Record Change

* **Goal:** Prove how DNS TTL affects client-side caching and traffic migration.
* **Test Steps:**
  1. Query DNS and inspect TTL:
     ```bash
     dig @10.0.0.1 app.team1.test
     ```
     Observe `30` in the answer section:
     ```
     app.team1.test.  30  IN  A  10.0.0.2
     ```
  2. Switch record to a new IP in DNS server:
     `app.team1.test` -> `10.0.0.6`
  3. Query immediately: client continues to receive old cached answer until the 30-second TTL expires.
  4. Flush client cache manually:
     ```bash
     sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder
     ```
     Client now immediately receives the updated IP!

---

## Extension C: Service Isolation (Backend Firewall Rules)

* **Goal:** Protect backend application servers from direct external access. Only the edge load balancer (`10.0.0.2`) may contact ports 3001 and 3002.
* **Implementation:** macOS Packet Filter (`pfctl`).
* **Config File:** `config/pf_rules.conf`
* **Commands:**
  1. Enable PF with project rules:
     ```bash
     sudo pfctl -ef config/pf_rules.conf
     ```
  2. Verify:
     * Request through Edge (`curl https://app.team1.test:8443/api/status`): **SUCCEEDS**
     * Direct connection from client to backend port 3001: **BLOCKED / DROPPED**
  3. Rollback / Disable PF:
     ```bash
     sudo pfctl -d
     ```

---

## Extension D: High-Availability Failover Behavior

* **Goal:** Zero-downtime routing when a backend crashes.
* **Test Steps:**
  1. While sending requests in a loop, kill Backend A:
     ```bash
     kill $(cat run/backend_a.pid)
     ```
  2. Requests continue without failure, served 100% by Backend B (`X-Backend: B`).
  3. Restart Backend A:
     ```bash
     python3 backend/backend_a.py 10.0.0.3 3001 > logs/backend_a.log 2>&1 &
     echo $! > run/backend_a.pid
     ```
  4. Edge proxy detects Backend A is back and resumes round-robin balancing!

---

## Extension E: Controlled Edge Migration (DNS Cutover)

* **Goal:** Migrate production traffic from Primary Edge (`10.0.0.2`) to Standby Edge (`10.0.0.6`) without downtime.
* **Test Steps:**
  1. Start Standby Edge on `10.0.0.6:8443` using `config/nginx_standby.conf`.
  2. Update DNS record: `app.team1.test -> 10.0.0.6`.
  3. Existing clients with cached DNS hit old edge until TTL expires; new clients hit standby edge with `X-Edge-Node: Standby-Edge-Mac5`.

---

## Extension F: Systematic Fault Diagnosis Methodology

During evaluation, when the faculty injects a fault, follow this 4-step diagnostic protocol:

1. **Layer 1: DNS Resolution Check**
   ```bash
   dig @10.0.0.1 app.team1.test
   ```
   * If failure: Issue is in the DNS service or port 53.
2. **Layer 2: Network / TCP Connectivity Check**
   ```bash
   nc -zv 10.0.0.2 8443
   ```
   * If connection refused: Edge server process is stopped or port is blocked.
3. **Layer 3: TLS Handshake Check**
   ```bash
   openssl s_client -connect 10.0.0.2:8443 -servername app.team1.test
   ```
   * If handshake error: Certificate expired, SAN mismatch, or untrusted CA.
4. **Layer 4: Application / Upstream Check**
   ```bash
   curl -i http://10.0.0.3:3001/api/status
   curl -i http://10.0.0.4:3002/api/status
   ```
   * If 502 Bad Gateway at edge: Check if backend processes are running.
