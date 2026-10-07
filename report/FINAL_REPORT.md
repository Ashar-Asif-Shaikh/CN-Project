# Computer Networks Course Project: Final Comprehensive Report
## Private Network Service Platform (Team 1)

---

## 1. Project Purpose & Executive Summary
The primary objective of this project is to bridge theoretical computer networking principles with a functioning, end-to-end multi-node network architecture. The application layer was deliberately kept minimal (a JSON/REST status endpoint) because **"the network is the project"**.

Every HTTP request traverses all seven layers of the OSI stack:
1. **Application Layer:** DNS resolution via RFC 1035 UDP queries and RESTful HTTP requests.
2. **Presentation / Security Layer:** TLS 1.2 / 1.3 cryptographic session negotiation, certificates with Subject Alternative Names (SAN), and symmetric payload encryption.
3. **Transport Layer:** TCP 3-way handshake (`SYN` $\rightarrow$ `SYN-ACK` $\rightarrow$ `ACK`), flow control, and socket pairs (ephemeral client port to well-known destination ports).
4. **Network Layer:** IPv4 routing across private subnets (`10.0.0.0/24` or AWS VPC `10.0.0.0/16`).
5. **Data Link / Physical Layer:** Frame transmission across native loopback interfaces (`lo0`) or Ethernet/Wi-Fi (`en0`).

---

## 2. System Architecture & Machine Roles

| Node Role | Assigned IP | Software Stack | Port / Protocol | Cloud Analogy |
|---|---|---|---|---|
| **Node 1** | `10.0.1.10` / `10.0.0.1` | `dnsmasq` / Python DNS Server | `53 / UDP` | AWS Route 53 Managed DNS |
| **Node 2** | `10.0.1.20` / `10.0.0.2` | Nginx / Python TLS Proxy | `8443 / TCP` (HTTPS) | AWS Application Load Balancer |
| **Node 3** | `10.0.1.30` / `10.0.0.3` | Python HTTP Backend A | `3001 / TCP` (HTTP) | EC2 Application Instance A |
| **Node 4** | `10.0.1.40` / `10.0.0.4` | Python HTTP Backend B | `3002 / TCP` (HTTP) | EC2 Application Instance B |
| **Node 5** | `10.0.1.50` / `10.0.0.5` | Backup DNS Resolver | `5354 / UDP` | Secondary DNS / Route 53 Replica |
| **Node 6** | `10.0.1.60` / `10.0.0.6` | Standby Edge Proxy | `8443 / TCP` | Active-Standby Edge Replica |

---

## 3. Phase 1 Implementation & Observations

### 3.1 DNS Name Resolution (Task B)
* **Configuration:** Private domain names `app.team1.test` and `api.team1.test` were mapped to Edge Node 2.
* **Observation:** `dig @<DNS_IP> app.team1.test` returned an authoritative A record answer in under 2 ms. The DNS transaction utilized UDP source ephemeral ports and destination port 53.

### 3.2 Backend Services & Load Balancing (Task C & D)
* **Backend A (`port 3001`):** Responded with JSON payload `{"backend": "A", "status": "ok"}` and header `X-Backend: A`.
* **Backend B (`port 3002`):** Responded with JSON payload `{"backend": "B", "status": "ok"}` and header `X-Backend: B`.
* **Reverse Proxy Load Balancing:** Configured with Round-Robin algorithm. Rapid consecutive requests alternated: A $\rightarrow$ B $\rightarrow$ A $\rightarrow$ B. Clients remained completely unaware of backend IP addresses.

### 3.3 TLS Termination & Trust (Task E)
* Self-signed Root CA (`ca.crt`) was created and added to the client trust store.
* Server certificate was minted with Subject Alternative Names for `app.team1.test`, `api.team1.test`, and `localhost`.
* Traffic terminated TLS on port 8443. `curl -v https://app.team1.test:8443` successfully verified certificate chains without requiring `-k`.

### 3.4 HTTP Caching & Transport Layer Behavior (Task F)
* Endpoints emitted `Cache-Control: max-age=60` and `ETag: "backend-a-v1"`.
* Conditional requests sending `If-None-Match` returned `HTTP 304 Not Modified`, demonstrating bandwidth conservation and cache revalidation.

---

## 4. Phase 2 Resilience, Hardening & Findings

### 4.1 What Changed from Phase 1
In Phase 1, the infrastructure assumed all components were static and permanently available. In Phase 2, the network was hardened to handle component failures, service isolation, and zero-downtime migrations:
1. Redundant DNS resolver added for automated name resolution failover.
2. Short TTLs (30s) enforced for controlled traffic cutover.
3. Packet Filter (PF) firewall rules implemented to restrict direct access to application backend ports.
4. Passive health checks added to Nginx (`max_fails=1 fail_timeout=10s`) to ensure high availability.

### 4.2 Failure Demonstrations & Results
1. **One Backend Stopped:** When Backend A was terminated, Nginx / the Edge Proxy detected upstream socket closure and immediately re-routed incoming requests to Backend B. Client observed zero dropped requests.
2. **Both Backends Stopped:** When both backends were terminated, the Edge server returned `HTTP 502 Bad Gateway`, proving the operational boundary between the Edge reverse proxy and upstream applications.
3. **Wrong Port Connection:** Attempting connections to port 9999 resulted in immediate TCP RST / Connection Refused, demonstrating the separation of IP routing from Transport-layer port multiplexing.

---

## 5. Learning Summary (One Paragraph per Extension)

### Extension A: Backup DNS Resolver
Implementing a secondary DNS resolver highlighted the vulnerability of single-point-of-failure directory services in distributed systems. When the primary DNS service was stopped, clients configured with secondary resolvers seamlessly resolved domain queries through the backup instance. This proved that application reachability relies entirely on redundant resolution paths and demonstrated how multi-nameserver architectures (such as Anycast and secondary DNS zones) safeguard cloud resilience.

### Extension B: DNS TTL and Controlled Record Change
Configuring a 30-second TTL provided hands-on experience with client-side caching semantics. Modifying a DNS A-record to point to a new IP address demonstrated that clients continue to query stale, cached destinations until the TTL counter decrements to zero. Manually flushing the DNS cache verified how resolvers clear memory tables, proving why production cloud migrations must lower TTL values well in advance of planned traffic cutovers.

### Extension C: Service Isolation (Backend Firewall Rules)
Enforcing Packet Filter (`pf`) rules demonstrated defense-in-depth and the principle of least privilege in network security. By dropping incoming TCP traffic destined for backend ports 3001 and 3002 from all source IPs except the edge proxy, we prevented direct client exploitation of application servers. This simulated modern Private Subnet architecture where backends reside in private subnets shielded by public-facing reverse proxies.

### Extension D: High-Availability Failover Behavior
Configuring passive upstream health checks (`max_fails` and `fail_timeout`) demonstrated automated fault detection at the application gateway. When Backend A was abruptly killed, the proxy intercepted the connection failure and seamlessly retried the request against Backend B within milliseconds. This underscored the distinction between active polling and passive circuit-breaking, proving how reverse proxies mask infrastructure degradation from end users.

### Extension E: Controlled Edge Migration (DNS-Based Cutover)
Simulating an active-standby edge migration illustrated zero-downtime infrastructure maintenance in production environments. By spinning up a standby reverse proxy node and modifying the DNS zone record, traffic smoothly shifted to the new entry point as client caches expired. This confirmed the mechanics behind blue/green edge deployments and CDN migrations in modern cloud architectures.

### Extension F: Faculty-Injected Troubleshooting Challenge
Developing a systematic, bottom-up diagnostic methodology (DNS $\rightarrow$ TCP connectivity $\rightarrow$ TLS handshake $\rightarrow$ Application HTTP status) proved essential for isolating simulated configuration faults. Rather than guessing, verifying layer-by-layer using `dig`, `nc`, `openssl s_client`, and `curl` isolated errors in under 30 seconds, demonstrating that structured troubleshooting is a fundamental core competency in network engineering.

---

## 6. Conclusion
The project successfully fulfilled all requirements of Phase 1 (Build & Observe) and Phase 2 (Harden, Recover & Troubleshoot). Whether deployed natively on macOS using loopback aliases or on AWS EC2, the architecture adheres strictly to RFC standards and demonstrates end-to-end packet visibility across every layer of the protocol stack.
