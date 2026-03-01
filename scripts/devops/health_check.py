#!/usr/bin/env python3
"""
Service Health Checker
=====================
Monitor HTTP endpoints, check response times, status codes, and content.
Supports parallel checks, retries, and multi-channel notifications.

Usage:
    python health_check.py config.json
    python health_check.py --url https://api.example.com/health
    python health_check.py config.json --notify slack --interval 60

Config file format (JSON):
    {
        "checks": [
            {"name": "API", "url": "https://api.example.com/health", "expect_status": 200, "timeout": 5},
            {"name": "Website", "url": "https://example.com", "expect_text": "Welcome", "timeout": 10}
        ]
    }

Environment:
    SLACK_WEBHOOK_URL — for Slack notifications
"""

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)


@dataclass
class CheckResult:
    name: str
    url: str
    status: str  # "ok", "warn", "fail"
    status_code: int | None = None
    response_time_ms: float = 0
    error: str | None = None


async def check_endpoint(client: httpx.AsyncClient, config: dict) -> CheckResult:
    """Check a single endpoint."""
    name = config.get("name", config["url"])
    url = config["url"]
    timeout = config.get("timeout", 10)
    expect_status = config.get("expect_status", 200)
    expect_text = config.get("expect_text")
    retries = config.get("retries", 1)

    for attempt in range(retries + 1):
        try:
            start = time.monotonic()
            resp = await client.get(url, timeout=timeout, follow_redirects=True)
            elapsed = (time.monotonic() - start) * 1000

            # Check status code
            if resp.status_code != expect_status:
                return CheckResult(name, url, "fail", resp.status_code, elapsed,
                                   f"Expected {expect_status}, got {resp.status_code}")

            # Check content
            if expect_text and expect_text not in resp.text:
                return CheckResult(name, url, "warn", resp.status_code, elapsed,
                                   f"Expected text not found: '{expect_text}'")

            # Check response time
            slow_threshold = config.get("slow_ms", 3000)
            status = "warn" if elapsed > slow_threshold else "ok"

            return CheckResult(name, url, status, resp.status_code, elapsed)

        except httpx.TimeoutException:
            if attempt < retries:
                await asyncio.sleep(1)
                continue
            return CheckResult(name, url, "fail", error=f"Timeout after {timeout}s")
        except Exception as e:
            if attempt < retries:
                await asyncio.sleep(1)
                continue
            return CheckResult(name, url, "fail", error=str(e))

    return CheckResult(name, url, "fail", error="Max retries exceeded")


def format_results(results: list[CheckResult]) -> str:
    """Format results for display."""
    icons = {"ok": "✅", "warn": "⚠️", "fail": "❌"}
    lines = []
    for r in results:
        icon = icons[r.status]
        time_str = f"{r.response_time_ms:.0f}ms" if r.response_time_ms else "—"
        code_str = f" [{r.status_code}]" if r.status_code else ""
        err = f" — {r.error}" if r.error else ""
        lines.append(f"  {icon} {r.name}{code_str} {time_str}{err}")
    return "\n".join(lines)


async def notify_slack(message: str):
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        return
    async with httpx.AsyncClient() as client:
        await client.post(url, json={"text": message})


async def run_checks(configs: list[dict], notify: str | None = None):
    """Run all checks and report results."""
    async with httpx.AsyncClient() as client:
        tasks = [check_endpoint(client, cfg) for cfg in configs]
        results = await asyncio.gather(*tasks)

    # Display
    total = len(results)
    ok = sum(1 for r in results if r.status == "ok")
    warn = sum(1 for r in results if r.status == "warn")
    fail = sum(1 for r in results if r.status == "fail")

    print(f"\n🏥 Health Check — {ok}/{total} healthy", end="")
    if warn:
        print(f", {warn} warning", end="")
    if fail:
        print(f", {fail} failed", end="")
    print(f"\n{'─' * 50}")
    print(format_results(results))

    # Notify on failures
    if notify and fail > 0:
        failed = [r for r in results if r.status == "fail"]
        msg = f"🚨 Health Check Alert — {fail} service(s) down!\n\n"
        msg += format_results(failed)
        if notify == "slack":
            await notify_slack(msg)
            print(f"\n📬 Alert sent to Slack")

    return results


async def main():
    parser = argparse.ArgumentParser(description="Check service health")
    parser.add_argument("config", nargs="?", help="Config JSON file")
    parser.add_argument("--url", help="Single URL to check")
    parser.add_argument("--notify", choices=["slack"], help="Notification channel")
    parser.add_argument("--interval", type=int, help="Repeat interval in seconds")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    # Build check configs
    if args.url:
        configs = [{"name": args.url, "url": args.url}]
    elif args.config:
        data = json.loads(Path(args.config).read_text())
        configs = data.get("checks", data if isinstance(data, list) else [data])
    else:
        print("Provide a config file or --url")
        sys.exit(1)

    if args.interval:
        print(f"Running every {args.interval}s (Ctrl+C to stop)")
        while True:
            results = await run_checks(configs, args.notify)
            if args.json:
                print(json.dumps([{
                    "name": r.name, "status": r.status, "ms": r.response_time_ms, "error": r.error
                } for r in results]))
            await asyncio.sleep(args.interval)
    else:
        results = await run_checks(configs, args.notify)
        if args.json:
            print(json.dumps([{
                "name": r.name, "status": r.status, "ms": r.response_time_ms, "error": r.error
            } for r in results]))

        # Exit code: 1 if any failures
        if any(r.status == "fail" for r in results):
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
