# Computer Networks Course Project: Private Network Service Platform
## Single-Mac Implementation (Fully Local, No Cloud Required)

[![macOS](https://img.shields.io/badge/Platform-macOS%20(Single--Mac)-blue.svg)]()
[![AWS](https://img.shields.io/badge/Cloud-AWS%20(Free%20Tier)-orange.svg)]()
[![Python](https://img.shields.io/badge/Language-Python%203.10%2B-brightgreen.svg)]()
[![TLS](https://img.shields.io/badge/Security-TLS%201.3%20%2F%20HTTPS-green.svg)]()
[![Status](https://img.shields.io/badge/Phase%201%20%26%202-Complete-success.svg)]()

This repository implements the **Computer Networks Course Project: Private Network Service Platform** with support for **two deployment modes**:
1. **Single-Mac Local Virtual LAN Mode**: Runs all 4 machine roles on your Mac using `lo0` IP aliases (`10.0.0.1` - `10.0.0.4`), 100% offline and free.
2. **AWS Cloud Mode (Approved by Faculty)**: Deploys 4 EC2 instances in an AWS VPC (`10.0.0.0/16`) via 1-click CloudFormation, while your Mac acts as the client. See [docs/AWS_DEPLOYMENT_GUIDE.md](file:///Users/ashar/.gemini/antigravity/scratch/cn-project/docs/AWS_DEPLOYMENT_GUIDE.md).

Traditionally, this project requires 4 physical Mac laptops connected to a Wi-Fi LAN. Using **macOS native loopback IP aliasing** (`lo0`), this project maps each physical machine role to an isolated IP address on the private `10.0.0.0/24` subnet. Every packet (DNS, TCP 3-way handshake, TLS handshake, reverse proxy traffic) flows across distinct IP endpoints, enabling full packet inspection in Wireshark on interface `lo0`.

---

## 1. Network Topology (Single-Mac Architecture)

| Node Role | Virtual Machine | Assigned IP | Protocol & Port | Cloud Equivalent |
|---|---|---|---|---|
| **Private DNS Server** | Virtual Mac 1 | `10.0.0.1` | `53 / UDP, TCP` | AWS Route 53 / CoreDNS |
| **Edge Reverse Proxy & LB** | Virtual Mac 2 | `10.0.0.2` | `8443 / TCP` (HTTPS) | AWS Application Load Balancer |
| **Backend Server A** | Virtual Mac 3 | `10.0.0.3` | `3001 / TCP` (HTTP) | EC2 App Instance A |
| **Backend Server B** | Virtual Mac 4 | `10.0.0.4` | `3002 / TCP` (HTTP) | EC2 App Instance B |
| **Backup DNS (Phase 2)** | Virtual Mac 5 | `10.0.0.5` | `5354 / UDP` | Secondary DNS / Route 53 Replica |
| **Standby Edge (Phase 2)** | Virtual Mac 6 | `10.0.0.6` | `8443 / TCP` (HTTPS) | Active-Standby Edge Replica |

---

## 2. Project Layout

```
cn-project/
├── README.md                           # Main Project Guide
├── backend/
│   ├── backend_a.py                    # Mac 3: Backend A (Port 3001, X-Backend: A)
│   └── backend_b.py                    # Mac 4: Backend B (Port 3002, X-Backend: B)
├── certs/
│   ├── generate_certs.sh               # OpenSSL SAN Certificate Generator
│   ├── openssl_san.cnf                 # OpenSSL configuration with SubjectAltName (.test)
│   ├── ca.crt / ca.key                 # Trusted Local Certificate Authority
│   └── server.crt / server.key         # Edge Server TLS Certificate
├── config/
│   ├── dnsmasq.conf                    # Mac 1 DNS config (for dnsmasq)
│   ├── dnsmasq_backup.conf             # Backup DNS config (Phase 2 Extension A)
│   ├── nginx.conf                      # Mac 2 Edge reverse proxy config (for nginx)
│   ├── nginx_standby.conf              # Standby Edge config (Phase 2 Extension E)
│   └── pf_rules.conf                   # macOS Packet Filter rules (Phase 2 Extension C)
├── dns/
│   └── dns_server.py                   # Zero-dependency RFC 1035 DNS Responder (Python)
├── proxy/
│   └── load_balancer.py                # Zero-dependency TLS Reverse Proxy & LB (Python)
├── scripts/
│   ├── setup_network.sh                # Configures lo0 IP aliases & /etc/resolver/test
│   ├── teardown_network.sh             # Cleans up aliases & restores network state
│   ├── start_all.sh                    # Launches all 4 services in background
│   ├── stop_all.sh                     # Stops all running services
│   ├── demo_phase1.sh                  # Automated script for Phase 1 demo & 5 failure tests
│   ├── demo_phase2.sh                  # Automated script for Phase 2 extensions
│   └── test_local.py                   # End-to-end self-test verification
├── docs/
│   ├── ARCHITECTURE.md                 # Full topology, service matrix, protocol journey
│   ├── PHASE1_GUIDE.md                 # Step-by-step Phase 1 & Wireshark capture guide
│   ├── PHASE2_GUIDE.md                 # Phase 2 extensions & troubleshooting guide
│   └── VIVA_CHEATSHEET.md              # Viva Q&A cheatsheet for evaluation (20 marks)
└── evidence/
    └── instructions.md                 # Checklist for saving Wireshark .pcapng files
```

---

## 3. Quick Start Guide (3 Simple Steps)

### Step 1: Initialize the Virtual LAN
In your terminal, navigate to the project directory and run:
```bash
cd /Users/ashar/.gemini/antigravity/scratch/cn-project
sudo ./scripts/setup_network.sh
```
*Creates loopback IP aliases (`10.0.0.1` - `10.0.0.6`), registers `/etc/resolver/test`, and trusts the Root CA in your macOS System Keychain.*

### Step 2: Start All Services
```bash
./scripts/start_all.sh
```
*Starts Mac 1 (DNS), Mac 2 (Edge Proxy), Mac 3 (Backend A), and Mac 4 (Backend B).*

### Step 3: Run the Automated Demonstration
```bash
./scripts/demo_phase1.sh
```
*Executes all Review 1 tasks:*
1. Shows IP inventory & ping reachability
2. Verifies DNS resolution via `dig app.team1.test`
3. Connects via HTTPS over domain name without `-k` flag
4. Demonstrates Round-Robin load balancing (`X-Backend: A` and `B` alternating)
5. Verifies HTTP caching (`Cache-Control: max-age=60`, conditional `304 Not Modified`)
6. Executes all 5 mandatory failure scenarios!

---

## 4. Running the Phase 2 Resilience Demo
```bash
./scripts/demo_phase2.sh
```
*Tests all Phase 2 extensions:*
* **Extension A:** Primary DNS server failure and failover to Backup DNS
* **Extension B:** 30-second TTL demonstration and cache flushing
* **Extension C:** macOS `pf` firewall rules isolating backend ports 3001/3002
* **Extension D:** HA failover when Backend A crashes
* **Extension E:** DNS-based edge migration to standby edge

---

## 5. Capturing Wireshark Evidence on a Single Mac
1. Open **Wireshark**.
2. Select interface **`Loopback: lo0`**.
3. Apply filter:
   ```
   udp.port == 53 or tcp.port == 8443 or tcp.port == 3001 or tcp.port == 3002
   ```
4. Run:
   ```bash
   curl https://app.team1.test:8443/api/status
   ```
5. You will see:
   * **DNS Query & Answer:** Client -> `10.0.0.1:53` -> returns `10.0.0.2`
   * **TCP 3-Way Handshake:** Client -> `10.0.0.2:8443` (SYN, SYN-ACK, ACK)
   * **TLS Handshake:** ClientHello (SNI: `app.team1.test`), ServerHello, Certificate, Key Exchange
   * **HTTP Proxy Traffic:** `10.0.0.2` -> `10.0.0.3:3001` or `10.0.0.4:3002`

---

## 6. Teardown / Cleanup
When evaluation is finished, cleanly remove all aliases and restore original settings:
```bash
sudo ./scripts/teardown_network.sh
```
