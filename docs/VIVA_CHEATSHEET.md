# Computer Networks Project: Viva Preparation & Questions Cheatsheet

Use this cheatsheet to ace the individual viva (10 marks in Review 1, 10 marks in Review 2).

---

### Q1: Why did you implement this on a single Mac using loopback aliases (10.0.0.x)?
**Answer:**
"In modern cloud architecture (like Kubernetes pods, AWS VPCs, and Docker containers), microservices often run on shared physical hardware communicating across virtual network interfaces.
Using macOS loopback aliasing on `lo0` (`sudo ifconfig lo0 alias 10.0.0.x`), each role receives an isolated IPv4 address on the private `10.0.0.0/24` subnet. In Wireshark, every packet has distinct source and destination IP addresses, demonstrating the exact same protocol interactions (DNS, TCP 3-way handshake, TLS handshake, reverse proxying, load balancing, and firewall isolation) as 4 physical laptops, while allowing rapid, repeatable automated testing."

---

### Q2: What is the difference between DNS resolution and the TCP/HTTPS connection?
**Answer:**
* **DNS Resolution:** Occurs first over UDP (port 53). It is purely a **directory lookup service** that translates human-readable domain names (`app.team1.test`) into an IP address (`10.0.0.2`). No application data is exchanged.
* **TCP/HTTPS Connection:** Occurs next over TCP (port 8443). Using the resolved IP, the client performs the 3-way handshake (SYN, SYN-ACK, ACK), establishes a TLS session, and transmits the HTTP request. DNS finds where to go; TCP/TLS creates the secure transport tunnel to get there.

---

### Q3: Explain the TCP 3-way handshake and its role in reliable data transfer.
**Answer:**
1. **SYN (Synchronize):** Client sends a TCP segment with `SYN=1` and an Initial Sequence Number (`Seq=ISN_c`).
2. **SYN-ACK:** Server responds with `SYN=1, ACK=1`, acknowledges client's sequence number (`Ack=ISN_c + 1`), and provides its own sequence number (`Seq=ISN_s`).
3. **ACK:** Client acknowledges server's sequence number (`ACK=1, Ack=ISN_s + 1`).
* **Why it matters:** Establishes connection state, negotiates Maximum Segment Size (MSS), synchronizes sequence numbers for flow control and reliable packet ordering.

---

### Q4: Walk through the TLS Handshake captured in Wireshark.
**Answer:**
1. **ClientHello:** Sent in plaintext. Contains supported TLS versions, cipher suites, random bytes, and the **SNI (Server Name Indication)** extension indicating `app.team1.test`.
2. **ServerHello:** Server selects the highest mutual TLS version (TLS 1.3/1.2) and chosen cipher suite.
3. **Certificate:** Server sends its X.509 certificate chain (`server.crt`). The client validates the signature against the trusted Local Root CA (`ca.crt`).
4. **Key Exchange (ECDHE):** Ephemeral Diffie-Hellman parameters are exchanged to establish symmetric session keys (providing Forward Secrecy).
5. **Finished / Application Data:** Handshake completes. All subsequent HTTP packets are encrypted symmetric payloads.

---

### Q5: Why is traffic encrypted on port 8443 but visible in plaintext on ports 3001 and 3002?
**Answer:**
"Because **TLS termination** occurs at the Edge Reverse Proxy (Mac 2).
* **Client to Edge (Port 8443):** Traverses the public/untrusted boundary, so it must be encrypted with TLS.
* **Edge to Backends (Ports 3001 & 3002):** Traverses the private internal backend network. Terminating TLS at the edge offloads cryptographic computation from the backend application servers and allows the edge to inspect headers, perform load balancing, and cache responses."

---

### Q6: How does HTTP Caching with `max-age=60` and `ETag` work?
**Answer:**
* **Fresh Cache Hit:** `Cache-Control: max-age=60` tells the client or intermediate caches that the response is fresh for 60 seconds. During this window, the client reuses the local cached copy without contacting the server.
* **Conditional Request (304 Not Modified):** Once the cache expires, or if revalidation is requested, the client sends `If-None-Match: "backend-a-v1"`. If the content hasn't changed, the backend returns `HTTP 304 Not Modified` with zero body bytes, saving network bandwidth.

---

### Q7: What happens when one backend crashes vs when both backends crash?
**Answer:**
* **One Backend Crashes:** The Edge Load Balancer detects upstream connection failure (via passive health check / `max_fails=1`) and automatically retries the request against the healthy backend. The client receives a seamless HTTP 200 response.
* **Both Backends Crash:** The Edge Load Balancer cannot reach any upstream server. Because the edge itself is still alive, it returns **`HTTP 502 Bad Gateway`**. This cleanly illustrates the boundary between the Edge layer and the Application layer.

---

### Q8: What is the Single Point of Failure (SPOF) in the Phase 1 architecture?
**Answer:**
"The Edge Reverse Proxy (Mac 2 / Nginx). If Mac 2 fails, no client can reach any backend, even if both Backend A and Backend B are perfectly healthy.
In Phase 2, this is addressed via **Extension E (Standby Edge with DNS Cutover)**, or in production using **Anycast IP, AWS Route 53 Health Checks, or Keepalived/VRRP (Virtual Router Redundancy Protocol)**."
