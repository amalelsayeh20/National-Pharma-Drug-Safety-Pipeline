\# RxVision Prototype — Troubleshooting \& Engineering Log



\## Overview



During the development of the \*\*RxVision Pharmacovigilance Data Pipeline\*\* prototype (`scripts/prototype.py`), several integration, networking, API schema, and runtime challenges were encountered.



This document serves as an engineering post-mortem documenting the confirmed issues, root causes, applied solutions, and engineering practices adopted during development.



\---



\## Troubleshooting Summary



| # | Issue                          | Root Cause                                                                                | Solution                                                    | Status       |

| - | ------------------------------ | ----------------------------------------------------------------------------------------- | ----------------------------------------------------------- | ------------ |

| 1 | RxNorm API Connection Error    | DNS / network connectivity failure to NIH infrastructure                                  | Cloudflare WARP encrypted DNS/network routing               | \*\*Resolved\*\* |

| 2 | OpenFDA API TLS Handshake Hang | Connection request could hang without proper client identification and timeout protection | Custom `User-Agent` + request timeout                       | \*\*Resolved\*\* |

| 3 | OpenFDA 404 on RxCUI           | OpenFDA and RxNorm do not have a guaranteed 1:1 identifier mapping                        | Multi-tier search using ingredient name with RxCUI fallback | \*\*Resolved\*\* |

| 4 | Unstructured `print()` Logging | `print()` lacks timestamps, severity levels, and structured execution context             | Python `logging` module                                     | \*\*Resolved\*\* |



\---



\# Detailed Troubleshooting



\## Issue #1 — RxNorm API Network Isolation



\### Problem



The initial execution of:



```python

get\_rxcui("Ibuprofen")

```



failed with a:



```text

requests.exceptions.ConnectionError

NameResolutionError

```



The application was unable to establish a connection to:



```text

rxnav.nlm.nih.gov

```



\### Root Cause



The issue was caused by a local network/DNS connectivity problem preventing reliable resolution or connection to the RxNorm NIH endpoint.



\### Solution



A secure network tunnel using \*\*Cloudflare WARP\*\* was configured with encrypted DNS/network routing.



This restored connectivity to the RxNorm API.



\### Why the Solution Works



The network tunnel routes DNS and HTTP traffic through Cloudflare's infrastructure, avoiding the local DNS/routing path that was causing the connection failure.



\### Prevention



For production deployments, API connectivity should be designed with:



\* Reliable DNS resolution

\* Network redundancy

\* Retry mechanisms

\* Request timeouts

\* Monitoring for external API availability



For example, retry logic can be implemented using `urllib3.util.Retry`.



\---



\# Issue #2 — OpenFDA API TLS Handshake Hang



\### Problem



Requests to:



```text

api.fda.gov

```



could hang during the SSL/TLS handshake:



```text

self.\_sslobj.do\_handshake()

```



The process eventually had to be manually terminated with:



```text

Ctrl + C

```



resulting in:



```text

KeyboardInterrupt

```



\### Root Cause



The request did not initially provide a custom application identity and did not have sufficient protection against indefinitely hanging network requests.



The default `requests` User-Agent is:



```text

python-requests/2.31.0

```



which can be treated differently by some API gateways or network security systems.



\### Solution



A custom `User-Agent` was added to all outbound API requests:



```python

HEADERS = {

&#x20;   "User-Agent": "RxVision-Pipeline/1.0"

}

```



A request timeout was also enforced:



```python

TIMEOUT = 10

```



and passed to every API call:



```python

response = requests.get(

&#x20;   url,

&#x20;   headers=HEADERS,

&#x20;   timeout=TIMEOUT

)

```



\### Why the Solution Works



The explicit `User-Agent` identifies the application as a named client, while the timeout prevents the pipeline from waiting indefinitely for an external service.



\### Prevention



External API calls in data pipelines should always include:



\* A defined `User-Agent`

\* Request timeouts

\* Exception handling

\* Retry logic where appropriate

\* Centralized API configuration



Avoid making unprotected HTTP requests such as:



```python

requests.get(url)

```



without a timeout.



\---



\# Issue #3 — OpenFDA 404 on Ingredient-Level RxCUI



\### Problem



A request such as:



```python

search\_fda\_by\_rxcui("5640")

```



for Ibuprofen returned:



```text

HTTP 404 Not Found

```



even though `5640` is a valid RxNorm RxCUI.



\### Root Cause



\*\*RxNorm and OpenFDA use different data models and identifiers.\*\*



An RxCUI can represent an ingredient-level concept, while OpenFDA label records may be indexed using different identifiers or searchable substance names.



Therefore, a valid RxNorm identifier does not guarantee that the same identifier exists in OpenFDA's label index.



\### Solution



A multi-tier search strategy was implemented.



\#### Primary Search



Search OpenFDA using the active ingredient:



```python

fda\_record = search\_fda\_by\_ingredient(ingredient\_name)

```



\#### Secondary Fallback



If no result is returned and an RxCUI is available:



```python

if not fda\_record and rxcui:

&#x20;   fda\_record = search\_fda\_by\_rxcui(rxcui)

```



HTTP `404` responses are also treated as an empty result rather than an unexpected application crash.



\### Why the Solution Works



Searching by the active substance provides a broader way to locate relevant FDA labels, while the RxCUI search provides an additional lookup strategy.



This makes the pipeline more resilient to differences between external healthcare data models.



\### Prevention



When integrating heterogeneous healthcare APIs:



> Never assume that identifiers from two independent systems have a guaranteed 1:1 mapping.



Instead, use:



\* Multiple lookup attributes

\* Fallback strategies

\* Explicit handling of empty results

\* Defensive API response parsing



\---



\# Issue #4 — Unstructured Terminal Output



\## `print()` vs. `logging`



\### Problem



The original prototype relied heavily on:



```python

print()

```



for execution tracking.



For example:



```python

print("Searching OpenFDA by ingredient...")

```



\### Root Cause



`print()` writes plain text directly to standard output without standardized metadata such as:



\* Timestamp

\* Severity level

\* Logger name

\* Execution context



This becomes limiting when the application evolves into an automated data pipeline.



\### Solution



Python's native `logging` module was introduced:



```python

import logging



logging.basicConfig(

&#x20;   level=logging.INFO,

&#x20;   format="%(asctime)s \[%(levelname)s] %(message)s"

)



logger = logging.getLogger(\_\_name\_\_)

```



Operational messages were then changed from:



```python

print("Searching OpenFDA by ingredient...")

```



to:



```python

logger.info("Searching OpenFDA by ingredient...")

```



Warnings use:



```python

logger.warning("No RxCUI found for %s", ingredient\_name)

```



and errors use:



```python

logger.error("API request failed: %s", e)

```



\### Why the Solution Works



Logging provides structured execution information, including timestamps and severity levels.



This makes application behavior easier to:



\* Debug

\* Monitor

\* Search

\* Aggregate

\* Analyze



It also integrates naturally with future orchestration tools such as \*\*Apache Airflow\*\* and \*\*Prefect\*\*, where pipeline execution logs need to be monitored systematically.



\### Prevention



Adopt Python `logging` as the standard for all operational messages from the beginning of the project.



Use appropriate levels:



| Level      | Purpose                                       |

| ---------- | --------------------------------------------- |

| `DEBUG`    | Detailed development/debugging information    |

| `INFO`     | Normal pipeline execution                     |

| `WARNING`  | Unexpected but non-fatal situations           |

| `ERROR`    | Failed operations                             |

| `CRITICAL` | Severe failures requiring immediate attention |



\---



\# Engineering Lessons Learned



The troubleshooting process highlighted several important Data Engineering principles:



1\. \*\*External APIs are unreliable dependencies.\*\*

&#x20;  Network failures, timeouts, empty responses, and service changes must be expected.



2\. \*\*Never assume identical schemas between different healthcare systems.\*\*

&#x20;  RxNorm and OpenFDA may represent the same drug using different identifiers and structures.



3\. \*\*Use defensive programming when consuming external data.\*\*

&#x20;  API responses should be validated before accessing nested fields.



4\. \*\*Every external HTTP request should have a timeout.\*\*



5\. \*\*Fallback strategies improve pipeline resilience.\*\*



6\. \*\*Logging is preferable to `print()` for automated pipelines.\*\*



7\. \*\*Prototype decisions should anticipate future orchestration and production deployment.\*\*



\---



\# Current Prototype Scope



The current prototype focuses on validating the integration between:



```text

Drug / Active Ingredient

&#x20;       ↓

&#x20;    RxNorm

&#x20;       ↓

&#x20;     RxCUI

&#x20;       ↓

&#x20;    OpenFDA

&#x20;       ↓

Safety Information

```



It is currently an \*\*API integration prototype\*\*, not a complete clinical or production pharmacovigilance system.



\--This prototype is intended for \*\*software engineering, data engineering, and pharmacovigilance research/education purposes\*\*.



The retrieved information should not be treated as a medical diagnosis or as a replacement for professional clinical judgment.



