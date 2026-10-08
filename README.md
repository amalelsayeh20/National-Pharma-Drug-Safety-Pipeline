\# RxVision Prototype — Troubleshooting \& Engineering Log



\## Overview



During the development of the \*\*RxVision Pharmacovigilance Data Pipeline\*\* prototype (`scripts/prototype.py`), several integration, networking, schema mapping, and runtime challenges were encountered. This document serves as an engineering post-mortem detailing confirmed bugs, their root causes, applied fixes, and architectural rationale to establish production-grade data engineering practices.



\---



\## Troubleshooting Summary



| Issue | Root Cause | Solution | Status |

|---|---|---|---|

| \*\*1. RxNorm API Connection Error\*\* | ISP/Geo-blocking \& local DNS resolution failure to US NIH servers (`rxnav.nlm.nih.gov`). | Encrypted DNS routing via Cloudflare WARP (1.1.1.1) VPN tunnel. | \*\*Resolved\*\* |

| \*\*2. OpenFDA API TLS Handshake Hang\*\* | OpenFDA API gateway drops/throttles generic Python `requests` User-Agent clients. | Injected explicit browser-emulating `User-Agent` headers in HTTP request payloads. | \*\*Resolved\*\* |

| \*\*3. OpenFDA 404 Not Found on RxCUI\*\* | OpenFDA indexes label data using brand-level RxCUIs or substance strings rather than base ingredient IDs. | Implemented a multi-tier fallback mechanism: query by `substance\_name` first, then fall back to `rxcui`. | \*\*Resolved\*\* |

| \*\*4. Raw `print()` Logging in Pipeline\*\* | Standard output lacks timestamping, severity levels, and structural persistence needed for orchestrators (Airflow). | Refactored pipeline logging to use Python's native `logging` module with standardized formats. | \*\*Resolved\*\* |



\---



\## Detailed Troubleshooting



\### Issue #1 — RxNorm API Network Isolation (DNS / Connection Error)



\*\*Problem:\*\*  

Execution failed during the initial call to `get\_rxcui("Ibuprofen")` with a `requests.exceptions.ConnectionError` and `NameResolutionError`. The script was unable to establish a socket connection to `rxnav.nlm.nih.gov`.



\*\*Root Cause:\*\*  

ISP-level filtering and regional geo-blocking isolated local network nodes from resolving DNS records or negotiating HTTPS connections directly with US National Institutes of Health (NIH) infrastructure.



\*\*Solution:\*\*  

Configured a secure, encrypted proxy tunnel using \*\*Cloudflare WARP (1.1.1.1)\*\* running on `Traffic and DNS (UDP)` mode\[cite: 4]. This bypassed local DNS hijacking and enabled stable transport-layer access to NIH endpoints.



\*\*Why the Solution Works:\*\*  

Tunneling routes traffic through Cloudflare's global edge network, presenting an egress IP located outside restricted regional ISP routing tables and providing validated upstream DNS resolvers.



\*\*Prevention:\*\*  

In production environments (AWS/GCP), deploy pipeline nodes inside VPCs equipped with static NAT Gateways, redundant DNS resolvers (e.g., 8.8.8.8, 1.1.1.1), and retry adapters (`urllib3.util.Retry`) to handle transient transit failures automatically.



\---



\### Issue #2 — OpenFDA API TLS Handshake Timeout (`KeyboardInterrupt`)



\*\*Problem:\*\*  

The request to `api.fda.gov` hung indefinitely during the SSL/TLS handshake phase (`self.\_sslobj.do\_handshake()`), forcing a manual termination via `Ctrl + C` (`KeyboardInterrupt`).



\*\*Root Cause:\*\*  

OpenFDA API security gateways enforce automated bot-mitigation policies. When a client sends a request without an explicit `User-Agent` header, Python's `requests` library sends `python-requests/2.31.0`. The gateway throttles or drops these requests before completing the TLS handshake.



\*\*Solution:\*\*  

Injected custom HTTP headers into all API outbound calls:

```python

HEADERS = {"User-Agent": "RxVision-Pipeline/1.0"}

