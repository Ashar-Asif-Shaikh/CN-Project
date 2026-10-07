#!/usr/bin/env python3
"""
Backend Server B (Represents Mac 4 in the CN Project topology)
Listens on TCP port 3002.

Endpoints:
  GET /            -> Service health page confirming service is running
  GET /api/status  -> JSON: {"backend": "B", "status": "ok"}

Mandatory Headers:
  X-Backend: B
  Cache-Control: max-age=60
  ETag: "backend-b-v1" (supports HTTP 304 Not Modified conditional requests)
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import sys

BACKEND_ID = "B"
DEFAULT_PORT = 3002
DEFAULT_HOST = "0.0.0.0"
ETAG_VALUE = '"backend-b-v1"'

class BackendHandler(BaseHTTPRequestHandler):
    def send_standard_headers(self, content_type="application/json"):
        # Mandatory project headers (Task C and Task F)
        self.send_header("X-Backend", BACKEND_ID)
        self.send_header("Cache-Control", "max-age=60")
        self.send_header("ETag", ETAG_VALUE)
        self.send_header("Content-Type", content_type)

    def do_GET(self):
        # Task F: Check for conditional GET request (HTTP caching verification)
        if_none_match = self.headers.get("If-None-Match")
        if if_none_match and if_none_match.strip() == ETAG_VALUE:
            self.send_response(304)  # Not Modified
            self.send_header("X-Backend", BACKEND_ID)
            self.send_header("Cache-Control", "max-age=60")
            self.send_header("ETag", ETAG_VALUE)
            self.end_headers()
            return

        if self.path == "/api/status":
            self.send_response(200)
            self.send_standard_headers("application/json")
            self.end_headers()
            response_data = {
                "backend": BACKEND_ID,
                "status": "ok",
                "message": f"Hello from Backend {BACKEND_ID}!",
                "service": "Private Network Service Platform"
            }
            self.wfile.write(json.dumps(response_data, indent=2).encode("utf-8"))

        elif self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_standard_headers("text/html")
            self.end_headers()
            html = f"""<!DOCTYPE html>
<html>
<head><title>Backend {BACKEND_ID}</title></head>
<body style="font-family: sans-serif; text-align: center; padding: 40px;">
  <h1 style="color: #38a169;">Backend {BACKEND_ID} Service is Running</h1>
  <p>Response served by: <strong>Backend {BACKEND_ID} (Port {self.server.server_port})</strong></p>
  <p>Status: <a href="/api/status">/api/status</a></p>
</body>
</html>"""
            self.wfile.write(html.encode("utf-8"))

        else:
            self.send_response(404)
            self.send_standard_headers("application/json")
            self.end_headers()
            err_data = {"backend": BACKEND_ID, "error": "Not Found", "path": self.path}
            self.wfile.write(json.dumps(err_data).encode("utf-8"))

    def log_message(self, format, *args):
        # Clean terminal logging
        sys.stderr.write(f"[Backend {BACKEND_ID}] {self.client_address[0]}:{self.client_address[1]} - {format % args}\n")

def run(host=DEFAULT_HOST, port=DEFAULT_PORT):
    server_address = (host, port)
    httpd = HTTPServer(server_address, BackendHandler)
    print(f"==================================================")
    print(f" Backend {BACKEND_ID} running on http://{host}:{port}")
    print(f" Listening interface: {host} (Port {port})")
    print(f" Press Ctrl+C to stop.")
    print(f"==================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print(f"\n[Backend {BACKEND_ID}] Shutting down...")
        httpd.server_close()

if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PORT
    run(host, port)
