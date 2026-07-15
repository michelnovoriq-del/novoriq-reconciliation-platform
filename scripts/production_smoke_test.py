#!/usr/bin/env python3
"""Non-destructive production HTTP and CORS checks (stdlib only)."""
import json
import os
import sys
import urllib.error
import urllib.request

FRONTEND_URL = os.getenv("FRONTEND_URL", "https://agenticreconcilliation.netlify.app").rstrip("/")
BACKEND_URL = os.getenv("BACKEND_URL", "https://novoriq-reconciliation-platform.onrender.com").rstrip("/")
CREATE_USER = os.getenv("SMOKE_CREATE_TEST_USER", "false").lower() == "true"


def request(url: str, method: str = "GET", headers=None, data=None):
    req = urllib.request.Request(url, method=method, headers=headers or {}, data=data)
    try:
        return urllib.request.urlopen(req, timeout=45)
    except urllib.error.HTTPError as exc:
        return exc


def check(name: str, condition: bool) -> None:
    print(f"{'PASS' if condition else 'FAIL'} {name}")
    if not condition:
        raise SystemExit(1)


for path in ("/", "/pricing", "/login"):
    response = request(FRONTEND_URL + path)
    check(f"frontend {path}", 200 <= response.status < 400)
for path in ("/health", "/ready"):
    response = request(BACKEND_URL + path)
    check(f"backend {path}", response.status == 200)

preflight_headers = {
    "Origin": FRONTEND_URL,
    "Access-Control-Request-Method": "POST",
    "Access-Control-Request-Headers": "content-type,authorization",
}
response = request(BACKEND_URL + "/auth/login", "OPTIONS", preflight_headers)
check("exact-origin CORS", response.headers.get("Access-Control-Allow-Origin") == FRONTEND_URL)
malicious = dict(preflight_headers, Origin="https://malicious.example")
response = request(BACKEND_URL + "/auth/login", "OPTIONS", malicious)
check("malicious origin rejected", response.headers.get("Access-Control-Allow-Origin") is None)

for path in ("/auth/register", "/auth/login"):
    response = request(BACKEND_URL + path, "POST", {"Content-Type": "application/json", "Origin": FRONTEND_URL}, b"{}")
    check(f"{path} reachable", response.status in {400, 401, 422})
response = request(BACKEND_URL + "/billing/current", headers={"Origin": FRONTEND_URL})
check("protected billing endpoint", response.status == 401)

if CREATE_USER:
    print("FAIL SMOKE_CREATE_TEST_USER is intentionally not implemented until production test-account cleanup exists.")
    sys.exit(2)
print(json.dumps({"status": "passed", "destructive": False}))
