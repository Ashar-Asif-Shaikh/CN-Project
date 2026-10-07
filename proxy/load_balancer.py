#!/usr/bin/env python3
"""
Edge Reverse Proxy & Load Balancer (Represents Mac 2 in the CN Project topology)
Listens on TCP port 8443 with TLS termination (HTTPS).
Performs Round-Robin Load Balancing across Backend A and Backend B.

Features:
  - TLS 1.2 / 1.3 Termination using certs/server.crt and certs/server.key
  - Round-Robin distribution between Backend A and Backend B
  - Passive Health Checking & Instant Failover (Extension D)
  - Returns HTTP 502 Bad Gateway when both backends are unreachable (Task G Failure Demo)
  - Passes through Cache-Control and ETag headers (Task F)
  - Real-time logging of upstream choices
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import ssl
import sys
import os
import urllib.request
import urllib.error
import itertools
import threading
import argparse

DEFAULT_PORT = 8443
DEFAULT_HOST = "0.0.0.0"

class LoadBalancerHandler(BaseHTTPRequestHandler):
    # Lock for thread-safe round-robin selection
    lb_lock = threading.Lock()

    def do_GET(self):
        self.proxy_request("GET")

    def do_HEAD(self):
        self.proxy_request("HEAD")

    def proxy_request(self, method):
        upstreams = self.server.upstreams
        num_upstreams = len(upstreams)
        
        # Round-robin attempt
        with LoadBalancerHandler.lb_lock:
            start_idx = self.server.current_index
            self.server.current_index = (self.server.current_index + 1) % num_upstreams

        response_sent = False

        # Try upstreams starting with chosen one (supports HA failover)
        for i in range(num_upstreams):
            target_idx = (start_idx + i) % num_upstreams
            target_host, target_port, backend_name = upstreams[target_idx]
            target_url = f"http://{target_host}:{target_port}{self.path}"

            try:
                # Bypass any system HTTP proxies for local loopback/alias backends
                proxy_handler = urllib.request.ProxyHandler({})
                opener = urllib.request.build_opener(proxy_handler)

                # Prepare forwarded request
                req = urllib.request.Request(target_url, method=method)
                for header_key, header_val in self.headers.items():
                    if header_key.lower() not in ["host"]:
                        req.add_header(header_key, header_val)
                req.add_header("Host", self.headers.get("Host", "app.team1.test"))
                req.add_header("X-Forwarded-For", self.client_address[0])
                req.add_header("X-Forwarded-Proto", "https")

                # Forward request to upstream backend with 2s timeout
                with opener.open(req, timeout=2.0) as resp:
                    resp_status = resp.status
                    resp_body = resp.read() if method != "HEAD" else b""
                    resp_headers = resp.headers

                    # Send response back to client
                    self.send_response(resp_status)
                    for key, value in resp_headers.items():
                        # Pass all headers from backend (including X-Backend, Cache-Control, ETag)
                        if key.lower() not in ["transfer-encoding", "connection"]:
                            self.send_header(key, value)
                    self.send_header("X-Proxy-Edge", "Mac 2 (Reverse Proxy & Load Balancer)")
                    self.end_headers()

                    if method != "HEAD":
                        self.wfile.write(resp_body)

                    backend_tag = resp_headers.get("X-Backend", backend_name)
                    print(f"[Edge Proxy] {self.path} -> Forwarded to {backend_name} ({target_host}:{target_port}) -> {resp_status} OK (X-Backend: {backend_tag})")
                    response_sent = True
                    break

            except urllib.error.HTTPError as e:
                # Upstream returned 304 Not Modified or 4xx/5xx
                self.send_response(e.code)
                for key, value in e.headers.items():
                    if key.lower() not in ["transfer-encoding", "connection"]:
                        self.send_header(key, value)
                self.send_header("X-Proxy-Edge", "Mac 2 (Reverse Proxy & Load Balancer)")
                self.end_headers()
                if method != "HEAD":
                    self.wfile.write(e.read())
                print(f"[Edge Proxy] {self.path} -> Backend {backend_name} returned status {e.code}")
                response_sent = True
                break

            except (urllib.error.URLError, ConnectionRefusedError, TimeoutError, OSError) as e:
                # Backend unavailable - trigger HA Failover (Extension D)
                print(f"[Edge Proxy WARNING] Backend {backend_name} ({target_host}:{target_port}) is DOWN ({e.reason if hasattr(e, 'reason') else e}). Failing over to next backend...")
                continue

        if not response_sent:
            # Both backends are down -> 502 Bad Gateway (PDF Section 6.3 Failure Demo)
            print("[Edge Proxy ERROR] ALL backend servers are unreachable! Returning HTTP 502 Bad Gateway.")
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("X-Proxy-Edge", "Mac 2 (Reverse Proxy & Load Balancer)")
            self.end_headers()
            err_msg = {
                "error": "502 Bad Gateway",
                "message": "All backend servers (Mac 3 & Mac 4) are currently unavailable.",
                "edge": "Mac 2 Nginx/Edge Load Balancer",
                "status": "failover_exhausted"
            }
            import json
            self.wfile.write(json.dumps(err_msg, indent=2).encode("utf-8"))

    def log_message(self, format, *args):
        # Suppress standard http.server logger to keep terminal output clean
        pass

class EdgeProxyServer(HTTPServer):
    def __init__(self, server_address, RequestHandlerClass, upstreams):
        super().__init__(server_address, RequestHandlerClass)
        self.upstreams = upstreams
        self.current_index = 0

def run_edge_proxy(host, port, cert_file, key_file, upstreams):
    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        print(f"[ERROR] TLS Certificate or Key not found at:\n  {cert_file}\n  {key_file}")
        print("Run `certs/generate_certs.sh` first to generate TLS certificates.")
        sys.exit(1)

    server_address = (host, port)
    httpd = EdgeProxyServer(server_address, LoadBalancerHandler, upstreams)

    # Configure TLS Context (Task E)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=cert_file, keyfile=key_file)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

    print("==========================================================")
    print(" Edge Reverse Proxy & Load Balancer (Mac 2) Running")
    print(f" Listening: https://{host}:{port} (TLS / HTTPS)")
    print(" Upstream Pool (Round-Robin):")
    for u_host, u_port, name in upstreams:
        print(f"   - {name}: http://{u_host}:{u_port}")
    print(f" TLS Cert: {cert_file}")
    print(" Press Ctrl+C to stop.")
    print("==========================================================")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[Edge Proxy] Shutting down...")
        httpd.server_close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Edge Reverse Proxy & Load Balancer")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Host to bind (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port (default: {DEFAULT_PORT})")
    parser.add_argument("--cert", default="certs/server.crt", help="Path to server.crt")
    parser.add_argument("--key", default="certs/server.key", help="Path to server.key")
    parser.add_argument("--backend-a-host", default="127.0.0.1", help="Backend A host")
    parser.add_argument("--backend-a-port", type=int, default=3001, help="Backend A port")
    parser.add_argument("--backend-b-host", default="127.0.0.1", help="Backend B host")
    parser.add_argument("--backend-b-port", type=int, default=3002, help="Backend B port")
    args = parser.parse_args()

    # Define upstream pool
    upstreams = [
        (args.backend_a_host, args.backend_a_port, "Backend A (Mac 3)"),
        (args.backend_b_host, args.backend_b_port, "Backend B (Mac 4)"),
    ]

    run_edge_proxy(args.host, args.port, args.cert, args.key, upstreams)
