# Evidence Folder Organization & Capture Instructions

Deliverable checklist for the **Evidence Folder** (required by Section 9 of the project rubric):

```
evidence/
├── 01_dns_resolution/
│   ├── dig_query_screenshot.png
│   └── wireshark_dns_query_response.pcapng
├── 02_tcp_handshake/
│   └── wireshark_tcp_syn_synack_ack.pcapng
├── 03_tls_handshake/
│   ├── wireshark_tls_handshake.pcapng
│   └── curl_verbose_tls_cert.png
├── 04_load_balancing/
│   ├── curl_alternating_backends.png
│   └── access_log_evidence.png
├── 05_http_caching/
│   ├── cache_control_headers.png
│   └── conditional_get_304_not_modified.png
└── 06_failure_scenarios/
    ├── backend_failover.png
    └── 502_bad_gateway.png
```

### How to export Wireshark captures:
1. In Wireshark, select the packets matching your filter (e.g. `tcp.port == 8443`).
2. Go to **File -> Export Specified Packets...**
3. Select **All packets** or **Displayed** packets.
4. Save as `.pcapng` into the appropriate subfolder.
