#!/usr/bin/env python3
"""
API Monitor — Monitor API endpoints for uptime, latency, and schema changes.

Usage:
    python api_monitor.py --url "https://api.example.com/health"
    python api_monitor.py --config endpoints.json --interval 60
    python api_monitor.py --url "https://api.example.com/v1/users" --assert-status 200 --assert-schema

Requirements:
    pip install requests
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("Install requests: pip install requests", file=sys.stderr)
    sys.exit(1)

STATE_FILE = Path.home() / ".cache" / "api-monitor" / "state.json"


def load_state():
    if STATE_FILE.exists(): return json.loads(STATE_FILE.read_text())
    return {}

def save_state(s):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(s, indent=2))


def check_endpoint(url, method="GET", headers=None, expected_status=200,
                   timeout=10, body=None) -> dict:
    try:
        start = time.time()
        resp = requests.request(method, url, headers=headers or {},
                               json=body, timeout=timeout)
        latency = (time.time() - start) * 1000
        
        result = {
            "url": url, "status_code": resp.status_code,
            "latency_ms": round(latency, 1),
            "ok": resp.status_code == expected_status,
            "content_length": len(resp.content),
            "timestamp": datetime.now().isoformat(),
        }
        
        try:
            result["response_json"] = resp.json()
        except Exception:
            result["response_text"] = resp.text[:500]
        
        return result
    except requests.exceptions.Timeout:
        return {"url": url, "ok": False, "error": "timeout", "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {"url": url, "ok": False, "error": str(e), "timestamp": datetime.now().isoformat()}


def check_schema_change(url, response_json, state):
    """Detect if API response schema changed."""
    def get_schema(obj, prefix=""):
        keys = set()
        if isinstance(obj, dict):
            for k, v in obj.items():
                keys.add(f"{prefix}{k}:{type(v).__name__}")
                if isinstance(v, (dict, list)):
                    keys.update(get_schema(v, f"{prefix}{k}."))
        elif isinstance(obj, list) and obj:
            keys.update(get_schema(obj[0], f"{prefix}[]."))
        return keys
    
    current_schema = get_schema(response_json)
    prev_schema = set(state.get(f"schema:{url}", []))
    
    state[f"schema:{url}"] = list(current_schema)
    
    if prev_schema and current_schema != prev_schema:
        added = current_schema - prev_schema
        removed = prev_schema - current_schema
        return {"changed": True, "added": list(added), "removed": list(removed)}
    return {"changed": False}


def main():
    parser = argparse.ArgumentParser(description="Monitor API endpoints")
    parser.add_argument("--url", help="Single URL to check")
    parser.add_argument("--config", help="JSON config with endpoints array")
    parser.add_argument("--method", default="GET")
    parser.add_argument("--assert-status", type=int, default=200)
    parser.add_argument("--assert-schema", action="store_true", help="Detect schema changes")
    parser.add_argument("--interval", type=int, default=0, help="Check interval (seconds)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    
    endpoints = []
    if args.url:
        endpoints = [{"url": args.url, "method": args.method, "expected_status": args.assert_status}]
    elif args.config:
        with open(args.config) as f:
            endpoints = json.load(f)
    else:
        parser.error("Provide --url or --config")
    
    state = load_state()
    
    while True:
        results = []
        for ep in endpoints:
            result = check_endpoint(
                ep.get("url", ep) if isinstance(ep, dict) else ep,
                ep.get("method", "GET") if isinstance(ep, dict) else "GET",
                ep.get("headers") if isinstance(ep, dict) else None,
                ep.get("expected_status", 200) if isinstance(ep, dict) else 200,
            )
            
            if args.assert_schema and result.get("response_json"):
                schema_check = check_schema_change(result["url"], result["response_json"], state)
                result["schema_change"] = schema_check
            
            results.append(result)
        
        save_state(state)
        
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for r in results:
                icon = "✅" if r.get("ok") else "❌"
                latency = f" {r.get('latency_ms', '?')}ms" if "latency_ms" in r else ""
                print(f"{icon} [{r.get('status_code', 'ERR')}]{latency} {r['url']}")
                if r.get("schema_change", {}).get("changed"):
                    print(f"  ⚠️  Schema changed! Added: {r['schema_change']['added']}")
        
        if args.interval <= 0:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
