#!/usr/bin/env python3
"""
Custom DNS Server for CN Course Project (Team 1)
Represents Mac 1 (Primary Managed DNS / Route 53 equivalent).
Standard RFC 1035 UDP DNS Server written with pure Python standard library.

Responds to queries for:
  - app.team1.test -> Target Edge IP (default: 10.0.0.2 or 127.0.0.1)
  - api.team1.test -> Target Edge IP (default: 10.0.0.2 or 127.0.0.1)
  - Supports configurable TTL (Task B & Extension B: 30 seconds)
  - Supports dynamic IP cutover (Extension E: Controlled Edge Migration)
"""

import socket
import struct
import sys
import argparse
import signal

DEFAULT_PORT = 53
DEFAULT_HOST = "0.0.0.0"
DEFAULT_TARGET_IP = "10.0.0.2"
DEFAULT_TTL = 30  # 30 seconds visible TTL for Extension B

# Global state for dynamic updates
target_ip = DEFAULT_TARGET_IP
current_ttl = DEFAULT_TTL
role_name = "Primary DNS (Mac 1)"

def parse_domain_name(data, offset):
    """Parses DNS label-encoded domain name from packet."""
    labels = []
    curr = offset
    while curr < len(data):
        length = data[curr]
        if length == 0:
            curr += 1
            break
        curr += 1
        labels.append(data[curr:curr+length].decode('utf-8', errors='ignore'))
        curr += length
    return ".".join(labels), curr

def build_dns_response(query_data, client_ip):
    global target_ip, current_ttl
    if len(query_data) < 12:
        return None

    # Parse header
    tx_id = query_data[:2]
    flags = query_data[2:4]
    qdcount = struct.unpack("!H", query_data[4:6])[0]

    # Parse Question
    offset = 12
    domain_name, offset = parse_domain_name(query_data, offset)
    if offset + 4 > len(query_data):
        return None
    qtype, qclass = struct.unpack("!HH", query_data[offset:offset+4])
    question_bytes = query_data[12:offset+4]

    print(f"[{role_name}] Query from {client_ip}: domain='{domain_name}', type={qtype}")

    # Check if this is an A record query (qtype 1) for our .test domain
    domain_lower = domain_name.lower()
    is_project_domain = domain_lower.endswith(".test") or "team1" in domain_lower

    if is_project_domain and qtype == 1:
        # Resolve to target IP
        ip_parts = [int(p) for p in target_ip.split(".")]
        ip_bytes = bytes(ip_parts)

        # Response flags: Standard response, No error, Authoritative Answer (0x8580)
        resp_flags = struct.pack("!H", 0x8580)
        counts = struct.pack("!HHHH", 1, 1, 0, 0) # 1 Question, 1 Answer, 0 Auth, 0 Add

        header = tx_id + resp_flags + counts

        # Answer Section
        # Name pointer offset 12 (0xc00c)
        ans_name = struct.pack("!H", 0xc00c)
        ans_type = struct.pack("!H", 1)       # A record
        ans_class = struct.pack("!H", 1)      # IN class
        ans_ttl = struct.pack("!I", current_ttl) # TTL in seconds (Extension B)
        ans_len = struct.pack("!H", 4)        # 4 bytes for IPv4

        answer = ans_name + ans_type + ans_class + ans_ttl + ans_len + ip_bytes

        print(f"[{role_name}] Resolved '{domain_name}' -> {target_ip} (TTL={current_ttl}s)")
        return header + question_bytes + answer
    else:
        # NXDOMAIN response (0x8183)
        resp_flags = struct.pack("!H", 0x8183)
        counts = struct.pack("!HHHH", 1, 0, 0, 0)
        return tx_id + resp_flags + counts + question_bytes

def run_server(host, port, ip_to_resolve, ttl, role):
    global target_ip, current_ttl, role_name
    target_ip = ip_to_resolve
    current_ttl = ttl
    role_name = role

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind((host, port))
    except PermissionError:
        print(f"\n[ERROR] Port {port} requires root privileges (sudo) on macOS.")
        print(f"Try running with sudo, or specify a non-privileged port like --port 5353.")
        sys.exit(1)
    except OSError as e:
        print(f"\n[ERROR] Could not bind to {host}:{port} - {e}")
        print(f"If another DNS server or mDNSResponder is using port 53, check with: sudo lsof -i :{port}")
        sys.exit(1)

    print("==========================================================")
    print(f" {role_name} Running")
    print(f" Listening: {host}:{port} (UDP)")
    print(f" Resolves *.team1.test -> {target_ip} (TTL={current_ttl}s)")
    print(f" Press Ctrl+C to stop.")
    print("==========================================================")

    try:
        while True:
            data, addr = sock.recvfrom(512)
            response = build_dns_response(data, addr[0])
            if response:
                sock.sendto(response, addr)
    except KeyboardInterrupt:
        print(f"\n[{role_name}] Stopping DNS server...")
    finally:
        sock.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CN Project DNS Server")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Host to bind (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port (default: {DEFAULT_PORT})")
    parser.add_argument("--target-ip", default=DEFAULT_TARGET_IP, help=f"Resolved IP (default: {DEFAULT_TARGET_IP})")
    parser.add_argument("--ttl", type=int, default=DEFAULT_TTL, help=f"TTL in seconds (default: {DEFAULT_TTL})")
    parser.add_argument("--role", default="Primary DNS (Mac 1)", help="Role label")
    args = parser.parse_args()

    run_server(args.host, args.port, args.target_ip, args.ttl, args.role)
