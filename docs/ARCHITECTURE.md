# Architecture Document: Private Network Service Platform (Single-Mac Architecture)

## 1. Executive Summary & Design Rationale
The Computer Networks Course Project specifies a private network service platform traditionally distributed across 4 physical laptops (Mac 1: DNS, Mac 2: Edge Proxy/LB, Mac 3: Backend A, Mac 4: Backend B).

In modern cloud computing (e.g. AWS, GCP, Docker, Kubernetes, and Service Meshes), distinct network nodes and microservices frequently execute on shared physical hardware through **virtual network interfaces and isolated IP aliases**.

To demonstrate this project on a single Mac without requiring 4 physical laptops, we use macOS native loopback network aliasing on the `lo0` interface. Each machine role is assigned a distinct, dedicated IP address in the private `10.0.0.0/24` subnet:
* **Mac 1 (DNS Server)**: `10.0.0.1`
* **Mac 2 (Edge Reverse Proxy & Load Balancer)**: `10.0.0.2`
* **Mac 3 (Backend Server A)**: `10.0.0.3`
* **Mac 4 (Backend Server B)**: `10.0.0.4`
* **Mac 5 (Backup DNS - Phase 2)**: `10.0.0.5`
* **Mac 6 (Standby Edge - Phase 2)**: `10.0.0.6`

Because all packets travel across interface `lo0` between distinct source and destination IP addresses, **Wireshark captures the exact same protocol packets (DNS, TCP 3-way handshake, TLS handshake, HTTP traffic) as 4 separate physical laptops on a Wi-Fi LAN**.

---

## 2. Network Topology Diagram

```
                             macOS Loopback Interface (lo0)
                          Private Virtual LAN: 10.0.0.0/24
  ====================================================================================
           |                                                      |
           v                                                      v
  +-----------------------------------+                 +-----------------------------------+
  | Virtual Mac 1 (10.0.0.1)          |                 | Virtual Mac 2 (10.0.0.2)          |
  | Role: Private DNS Server          |                 | Role: Edge Reverse Proxy & LB     |
  | Service: RFC 1035 DNS / dnsmasq   |                 | Service: Nginx / TLS LB Proxy     |
  | Port: 53 UDP/TCP                  |                 | Port: 8443 TCP (TLS 1.2/1.3)      |
  | Resolves: *.team1.test -> 10.0.0.2|                 | Certificates: SAN (server.crt)    |
  +-----------------------------------+                 +-----------------+-----------------+
                   ^                                                      |
                   | DNS Query: app.team1.test                            | Round-Robin LB
                   |                                                      v
  +----------------+------------------+                 +-----------------+-----------------+
  | Test Client (macOS Host)          |                 |                                   |
  | - dig @10.0.0.1 app.team1.test    |        +--------+--------+                 +--------+--------+
  | - curl https://app.team1.test:8443|        |                 |                 |                 |
  | - Wireshark on lo0                |        v                 v                 v                 v
  +-----------------------------------+ +--------------+ +--------------+  +--------------+ +--------------+
                                        | Virtual Mac 3| | Virtual Mac 4|  | Virtual Mac 5| | Virtual Mac 6|
                                        | (10.0.0.3)   | | (10.0.0.4)   |  | (10.0.0.5)   | | (10.0.0.6)   |
                                        | Backend A    | | Backend B    |  | Backup DNS   | | Standby Edge |
                                        | Port 3001    | | Port 3002    |  | Port 5354    | | Port 8443    |
                                        | X-Backend: A | | X-Backend: B |  | (Phase 2)    | | (Phase 2)    |
                                        +--------------+ +--------------+  +--------------+ +--------------+
  ====================================================================================
```

---

## 3. Node Inventory & Service Matrix

| Virtual Node | Assigned IP | Service Name | Protocol & Port | Cloud Equivalent | Purpose in Project |
|---|---|---|---|---|---|
| **Mac 1** | `10.0.0.1` | Private DNS Server | `53 / UDP, TCP` | AWS Route 53 / CoreDNS | Resolves `app.team1.test` & `api.team1.test` to `10.0.0.2` with 30s TTL |
| **Mac 2** | `10.0.0.2` | Edge Reverse Proxy & LB | `8443 / TCP` (HTTPS) | AWS ALB / Cloudflare Edge | Terminates TLS, round-robins between backends, handles failover |
| **Mac 3** | `10.0.0.3` | Backend Server A | `3001 / TCP` (HTTP) | EC2 App Instance A | Serves `/` and `/api/status`, returns `X-Backend: A`, `Cache-Control` |
| **Mac 4** | `10.0.0.4` | Backend Server B | `3002 / TCP` (HTTP) | EC2 App Instance B | Serves `/` and `/api/status`, returns `X-Backend: B`, `Cache-Control` |
| **Mac 5** | `10.0.0.5` | Backup DNS (Phase 2) | `5354 / UDP` | Secondary DNS / Route 53 Replica | Handles DNS resolution when Primary DNS fails (Extension A) |
| **Mac 6** | `10.0.0.6` | Standby Edge (Phase 2)| `8443 / TCP` (HTTPS) | Multi-Region Active-Standby LB | Demonstrates zero-downtime DNS cutover migration (Extension E) |

---

## 4. End-to-End Request Protocol Journey

When the user runs:
```bash
curl -i https://app.team1.test:8443/api/status
```

The request progresses through all 7 layers of the OSI stack:

### Layer 1: DNS Resolution (Application / UDP Transport)
1. Client generates DNS Query `A app.team1.test` (Source Port: Ephemeral e.g. 52341, Destination Port: 53/UDP).
2. DNS Server (`10.0.0.1`) receives packet, matches zone `.team1.test`, and replies with A-record `10.0.0.2`, TTL = 30s.
3. Client caches the DNS response.

### Layer 2: TCP 3-Way Handshake (Transport Layer)
1. **SYN**: Client (`10.0.0.1` or host ephemeral port e.g. 52342) -> Edge Server (`10.0.0.2:8443`). `SYN=1, Seq=0`.
2. **SYN-ACK**: Edge Server (`10.0.0.2:8443`) -> Client. `SYN=1, ACK=1, Seq=0, Ack=1`.
3. **ACK**: Client -> Edge Server. `ACK=1, Seq=1, Ack=1`.
*TCP connection established.*

### Layer 3: TLS 1.2/1.3 Handshake (Presentation / Security Layer)
1. **ClientHello**: Supported cipher suites, TLS version, SNI extension (`app.team1.test`).
2. **ServerHello & Certificate**: Edge Server selects cipher suite, transmits `server.crt` containing Subject Alternative Names (`app.team1.test`).
3. **Key Exchange & Finished**: Ephemeral Diffie-Hellman parameters exchanged, session keys derived, symmetric encryption activated.

### Layer 4: HTTP Request & Edge Proxy Processing
1. Client sends encrypted HTTP request `GET /api/status HTTP/1.1` over TLS.
2. Edge Proxy (`10.0.0.2:8443`) decrypts packet, inspects `Host: app.team1.test`.
3. Load Balancer selects next upstream target using Round-Robin (alternating between `10.0.0.3:3001` and `10.0.0.4:3002`).

### Layer 5: Backend Request & Response
1. Edge Proxy opens TCP connection to chosen backend (e.g. `10.0.0.3:3001`).
2. Backend A receives `GET /api/status`, creates JSON response `{"backend": "A", "status": "ok"}`.
3. Backend A attaches headers:
   * `X-Backend: A`
   * `Cache-Control: max-age=60`
   * `ETag: "backend-a-v1"`
4. Backend sends response to Edge Proxy.

### Layer 6: TLS Encryption & Delivery to Client
1. Edge Proxy receives backend response, adds `X-Proxy-Edge: Mac 2`.
2. Edge Proxy encrypts HTTP response and sends back over TLS socket to Client.
3. Client terminal displays response and verified headers.
