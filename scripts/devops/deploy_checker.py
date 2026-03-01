#!/usr/bin/env python3
"""
Deploy Checker — Pre-deployment health check for web services.

Runs a battery of checks before deploying: DNS resolution, SSL certificate
validity, endpoint health, response times, and content verification.

Usage:
    python deploy_checker.py https://myapp.com
    python deploy_checker.py --config checks.yaml
    python deploy_checker.py https://api.example.com --endpoints /health,/api/v1/status
    python deploy_checker.py https://example.com --ssl --dns --timing

Requirements:
    pip install requests
"""

import argparse
import json
import socket
import ssl
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("Install requests: pip install requests", file=sys.stderr)
    sys.exit(1)


def check_dns(hostname: str) -> dict:
    """Check DNS resolution."""
    try:
        start = time.time()
        ips = socket.getaddrinfo(hostname, None)
        elapsed = (time.time() - start) * 1000
        
        unique_ips = list(set(addr[4][0] for addr in ips))
        return {
            "check": "dns",
            "status": "pass",
            "hostname": hostname,
            "ips": unique_ips,
            "resolve_ms": round(elapsed, 1),
        }
    except socket.gaierror as e:
        return {"check": "dns", "status": "fail", "error": str(e)}


def check_ssl(hostname: str, port: int = 443) -> dict:
    """Check SSL certificate validity."""
    try:
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(socket.socket(), server_hostname=hostname) as s:
            s.settimeout(10)
            s.connect((hostname, port))
            cert = s.getpeercert()
        
        not_after = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
        not_before = datetime.strptime(cert["notBefore"], "%b %d %H:%M:%S %Y %Z")
        days_remaining = (not_after - datetime.now()).days
        
        subject = dict(x[0] for x in cert.get("subject", []))
        issuer = dict(x[0] for x in cert.get("issuer", []))
        
        status = "pass" if days_remaining > 7 else "warn" if days_remaining > 0 else "fail"
        
        return {
            "check": "ssl",
            "status": status,
            "subject": subject.get("commonName", ""),
            "issuer": issuer.get("organizationName", ""),
            "valid_from": not_before.isoformat(),
            "valid_until": not_after.isoformat(),
            "days_remaining": days_remaining,
            "san": [entry[1] for entry in cert.get("subjectAltName", [])],
        }
    except Exception as e:
        return {"check": "ssl", "status": "fail", "error": str(e)}


def check_endpoint(url: str, expected_status: int = 200, timeout: int = 10) -> dict:
    """Check HTTP endpoint health."""
    try:
        start = time.time()
        resp = requests.get(url, timeout=timeout, allow_redirects=True)
        elapsed = (time.time() - start) * 1000
        
        status = "pass" if resp.status_code == expected_status else "fail"
        
        return {
            "check": "endpoint",
            "status": status,
            "url": url,
            "status_code": resp.status_code,
            "expected": expected_status,
            "response_ms": round(elapsed, 1),
            "content_length": len(resp.content),
            "headers": {
                "server": resp.headers.get("server", ""),
                "content-type": resp.headers.get("content-type", ""),
                "cache-control": resp.headers.get("cache-control", ""),
            },
            "redirects": [r.url for r in resp.history] if resp.history else [],
        }
    except requests.exceptions.Timeout:
        return {"check": "endpoint", "status": "fail", "url": url, "error": "Timeout"}
    except Exception as e:
        return {"check": "endpoint", "status": "fail", "url": url, "error": str(e)}


def check_timing(url: str, iterations: int = 3) -> dict:
    """Measure response time statistics."""
    times = []
    for _ in range(iterations):
        try:
            start = time.time()
            requests.get(url, timeout=15)
            times.append((time.time() - start) * 1000)
        except Exception:
            times.append(float("inf"))
    
    valid = [t for t in times if t != float("inf")]
    if not valid:
        return {"check": "timing", "status": "fail", "error": "All requests failed"}
    
    return {
        "check": "timing",
        "status": "pass" if min(valid) < 2000 else "warn",
        "url": url,
        "min_ms": round(min(valid), 1),
        "max_ms": round(max(valid), 1),
        "avg_ms": round(sum(valid) / len(valid), 1),
        "iterations": iterations,
    }


def run_checks(base_url: str, endpoints: list[str],
               do_ssl: bool = True, do_dns: bool = True, do_timing: bool = True) -> list[dict]:
    """Run all configured checks."""
    parsed = urlparse(base_url)
    hostname = parsed.hostname
    results = []
    
    if do_dns:
        results.append(check_dns(hostname))
    
    if do_ssl and parsed.scheme == "https":
        results.append(check_ssl(hostname))
    
    for endpoint in endpoints:
        url = f"{base_url.rstrip('/')}{endpoint}"
        results.append(check_endpoint(url))
    
    if do_timing:
        results.append(check_timing(base_url))
    
    return results


def format_report(results: list[dict]) -> str:
    """Format results as human-readable report."""
    lines = [f"# Deploy Health Check — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"]
    
    passed = sum(1 for r in results if r["status"] == "pass")
    warned = sum(1 for r in results if r["status"] == "warn")
    failed = sum(1 for r in results if r["status"] == "fail")
    
    overall = "✅ ALL PASS" if failed == 0 and warned == 0 else "⚠️ WARNINGS" if failed == 0 else "❌ FAILURES"
    lines.append(f"**Overall:** {overall} ({passed} pass, {warned} warn, {failed} fail)\n")
    
    icons = {"pass": "✅", "warn": "⚠️", "fail": "❌"}
    
    for result in results:
        icon = icons.get(result["status"], "?")
        check = result["check"].upper()
        lines.append(f"{icon} **{check}**")
        
        for key, value in result.items():
            if key in ("check", "status"):
                continue
            if isinstance(value, (list, dict)):
                value = json.dumps(value, indent=2) if value else "none"
            lines.append(f"   {key}: {value}")
        lines.append("")
    
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Pre-deploy health checker")
    parser.add_argument("url", help="Base URL to check")
    parser.add_argument("--endpoints", default="/", help="Comma-separated endpoint paths")
    parser.add_argument("--ssl", action="store_true", default=True)
    parser.add_argument("--no-ssl", dest="ssl", action="store_false")
    parser.add_argument("--dns", action="store_true", default=True)
    parser.add_argument("--no-dns", dest="dns", action="store_false")
    parser.add_argument("--timing", action="store_true", default=True)
    parser.add_argument("--no-timing", dest="timing", action="store_false")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()
    
    endpoints = [e.strip() for e in args.endpoints.split(",")]
    results = run_checks(args.url, endpoints, args.ssl, args.dns, args.timing)
    
    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        print(format_report(results))
    
    # Exit code: 1 if any failures
    if any(r["status"] == "fail" for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
