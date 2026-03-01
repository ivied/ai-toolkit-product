#!/usr/bin/env python3
"""
Port Scanner — Quick network port scanner for security audits.

Scans common ports on a host to check for open services.
Uses concurrent scanning for speed.

Usage:
    python port_scanner.py example.com
    python port_scanner.py 192.168.1.1 --ports 80,443,8080,3000
    python port_scanner.py 10.0.0.1 --range 1-1024 --threads 100

No external dependencies required.
"""

import argparse
import json
import socket
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

COMMON_PORTS = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS",
    465: "SMTPS", 587: "SMTP/TLS", 993: "IMAPS", 995: "POP3S",
    3306: "MySQL", 5432: "PostgreSQL", 6379: "Redis", 8080: "HTTP-Alt",
    8443: "HTTPS-Alt", 27017: "MongoDB", 5672: "RabbitMQ",
    9200: "Elasticsearch", 3000: "Dev", 4000: "Dev", 5000: "Dev",
}


def scan_port(host, port, timeout=2):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            service = COMMON_PORTS.get(port, "unknown")
            try:
                service = socket.getservbyport(port) or service
            except OSError:
                pass
            return {"port": port, "state": "open", "service": service}
        return {"port": port, "state": "closed"}
    except socket.timeout:
        return {"port": port, "state": "filtered"}
    except Exception as e:
        return {"port": port, "state": "error", "error": str(e)}


def scan_host(host, ports, threads=50, timeout=2, show_closed=False):
    print(f"🔍 Scanning {host} ({len(ports)} ports, {threads} threads)...\n", file=sys.stderr)
    
    results = []
    with ThreadPoolExecutor(max_workers=threads) as executor:
        futures = {executor.submit(scan_port, host, port, timeout): port for port in ports}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            if result["state"] == "open":
                print(f"  ✅ {result['port']:>5}/tcp  open  {result.get('service', '')}", file=sys.stderr)
    
    results.sort(key=lambda r: r["port"])
    
    if not show_closed:
        results = [r for r in results if r["state"] != "closed"]
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Network port scanner")
    parser.add_argument("host", help="Target host or IP")
    parser.add_argument("--ports", help="Comma-separated ports")
    parser.add_argument("--range", help="Port range (e.g., 1-1024)")
    parser.add_argument("--common", action="store_true", default=True, help="Scan common ports")
    parser.add_argument("--threads", type=int, default=50)
    parser.add_argument("--timeout", type=float, default=2)
    parser.add_argument("--show-closed", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    
    if args.ports:
        ports = [int(p.strip()) for p in args.ports.split(",")]
    elif args.range:
        start, end = args.range.split("-")
        ports = list(range(int(start), int(end) + 1))
    else:
        ports = sorted(COMMON_PORTS.keys())
    
    try:
        ip = socket.gethostbyname(args.host)
        print(f"Host: {args.host} ({ip})", file=sys.stderr)
    except socket.gaierror:
        print(f"❌ Cannot resolve {args.host}", file=sys.stderr)
        sys.exit(1)
    
    results = scan_host(args.host, ports, args.threads, args.timeout, args.show_closed)
    
    open_ports = [r for r in results if r["state"] == "open"]
    filtered = [r for r in results if r["state"] == "filtered"]
    
    if args.json:
        print(json.dumps({"host": args.host, "ip": ip, "results": results,
                         "open": len(open_ports), "filtered": len(filtered)}, indent=2))
    else:
        print(f"\n{'='*40}", file=sys.stderr)
        print(f"Open: {len(open_ports)} | Filtered: {len(filtered)} | Scanned: {len(ports)}", file=sys.stderr)


if __name__ == "__main__":
    main()
