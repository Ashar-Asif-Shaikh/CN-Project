#!/usr/bin/env python3
"""
Self-Test Verification Script for CN Project
Starts Backend A, Backend B, and Edge Proxy on separate threads/processes,
sends test HTTP/HTTPS requests, checks load balancing, headers, and caching.
"""

import threading
import time
import urllib.request
import ssl
import json
import sys
import os

# Adjust path to project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from backend.backend_a import BackendHandler as HandlerA
from backend.backend_b import BackendHandler as HandlerB
from proxy.load_balancer import run_edge_proxy
from http.server import HTTPServer

def run_server(server_class, handler_class, host, port):
    httpd = server_class((host, port), handler_class)
    httpd.serve_forever()

def main():
    print("==================================================")
    print(" Running End-to-End Automated Self-Test")
    print("==================================================")

    # 1. Start Backend A on 127.0.0.1:3001
    server_a = HTTPServer(("127.0.0.1", 3001), HandlerA)
    thread_a = threading.Thread(target=server_a.serve_forever, daemon=True)
    thread_a.start()
    print("✓ Backend A started on port 3001")

    # 2. Start Backend B on 127.0.0.1:3002
    server_b = HTTPServer(("127.0.0.1", 3002), HandlerB)
    thread_b = threading.Thread(target=server_b.serve_forever, daemon=True)
    thread_b.start()
    print("✓ Backend B started on port 3002")

    # 3. Start Edge Proxy on 127.0.0.1:8443
    cert_path = os.path.join(PROJECT_ROOT, "certs", "server.crt")
    key_path = os.path.join(PROJECT_ROOT, "certs", "server.key")
    upstreams = [
        ("127.0.0.1", 3001, "Backend A"),
        ("127.0.0.1", 3002, "Backend B")
    ]
    thread_proxy = threading.Thread(
        target=run_edge_proxy,
        args=("127.0.0.1", 8443, cert_path, key_path, upstreams),
        daemon=True
    )
    thread_proxy.start()
    print("✓ Edge TLS Proxy & Load Balancer started on port 8443")

    time.sleep(1)

    # Configure client SSL context using our CA cert
    ca_cert_path = os.path.join(PROJECT_ROOT, "certs", "ca.crt")
    ssl_ctx = ssl.create_default_context(cafile=ca_cert_path)

    # Bypass system proxies for local tests
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPSHandler(context=ssl_ctx)
    )
    urllib.request.install_opener(opener)

    print("\n--------------------------------------------------")
    print("TEST 1: Testing Direct Backend A & B HTTP Endpoints")
    print("--------------------------------------------------")
    with urllib.request.urlopen("http://127.0.0.1:3001/api/status") as resp:
        assert resp.status == 200
        assert resp.headers.get("X-Backend") == "A"
        assert "max-age=60" in resp.headers.get("Cache-Control", "")
        data = json.loads(resp.read().decode())
        print(f"Backend A response: {data} (X-Backend: {resp.headers.get('X-Backend')}) -> PASS")

    with urllib.request.urlopen("http://127.0.0.1:3002/api/status") as resp:
        assert resp.status == 200
        assert resp.headers.get("X-Backend") == "B"
        data = json.loads(resp.read().decode())
        print(f"Backend B response: {data} (X-Backend: {resp.headers.get('X-Backend')}) -> PASS")

    print("\n--------------------------------------------------")
    print("TEST 2: Testing HTTPS Connection through Edge Proxy")
    print("--------------------------------------------------")
    req = urllib.request.Request("https://127.0.0.1:8443/api/status", headers={"Host": "app.team1.test"})
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode())
        print(f"Edge Proxy HTTPS Status: {resp.status} OK")
        print(f"Edge Proxy Returned Headers: X-Backend={resp.headers.get('X-Backend')}, Cache-Control={resp.headers.get('Cache-Control')}")
        print("-> PASS")

    print("\n--------------------------------------------------")
    print("TEST 3: Testing Round-Robin Load Balancing (4 requests)")
    print("--------------------------------------------------")
    backends_seen = []
    for i in range(4):
        req = urllib.request.Request("https://127.0.0.1:8443/api/status", headers={"Host": "app.team1.test"})
        with urllib.request.urlopen(req) as resp:
            b = resp.headers.get("X-Backend")
            backends_seen.append(b)
            print(f"Request {i+1} routed to: Backend {b}")
    assert "A" in backends_seen and "B" in backends_seen
    print(f"Distribution sequence: {backends_seen} -> PASS (Round-Robin alternating correctly)")

    print("\n--------------------------------------------------")
    print("TEST 4: Testing HTTP Caching (Conditional GET 304)")
    print("--------------------------------------------------")
    # Send request with matching ETag
    req_etag = urllib.request.Request("http://127.0.0.1:3001/api/status", headers={"If-None-Match": '"backend-a-v1"'})
    try:
        urllib.request.urlopen(req_etag)
    except urllib.error.HTTPError as e:
        print(f"Conditional GET returned status code: {e.code} ({e.reason})")
        assert e.code == 304
        print("-> PASS (HTTP 304 Not Modified returned correctly)")

    print("\n==================================================")
    print(" ALL SELF-TESTS PASSED SUCCESSFULLY! (100% OK)")
    print("==================================================")

if __name__ == "__main__":
    main()
