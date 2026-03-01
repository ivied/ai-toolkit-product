#!/usr/bin/env python3
"""
Email Alert — Send email notifications via SMTP.

Supports Gmail, Outlook, and custom SMTP servers. Great for
automated alerts from scripts and cron jobs.

Usage:
    python email_alert.py --to user@example.com --subject "Alert" --body "Server down!"
    python email_alert.py --to user@example.com --subject "Report" --file report.pdf
    python email_alert.py --to user@example.com --subject "Test" --html "<h1>Hello</h1>"

Environment variables:
    SMTP_HOST     - SMTP server (default: smtp.gmail.com)
    SMTP_PORT     - SMTP port (default: 587)
    SMTP_USER     - Username/email
    SMTP_PASSWORD  - Password or app password
"""

import argparse
import os
import smtplib
import sys
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

PRESETS = {
    "gmail": {"host": "smtp.gmail.com", "port": 587},
    "outlook": {"host": "smtp-mail.outlook.com", "port": 587},
    "yahoo": {"host": "smtp.mail.yahoo.com", "port": 587},
}


def send_email(to: str, subject: str, body: str = "", html: str = None,
               attachments: list = None, cc: str = None, bcc: str = None,
               smtp_host: str = None, smtp_port: int = None,
               smtp_user: str = None, smtp_password: str = None) -> dict:
    """Send an email via SMTP."""
    host = smtp_host or os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
    user = smtp_user or os.getenv("SMTP_USER", "")
    password = smtp_password or os.getenv("SMTP_PASSWORD", "")
    
    if not user or not password:
        return {"ok": False, "error": "Set SMTP_USER and SMTP_PASSWORD environment variables"}
    
    msg = MIMEMultipart("alternative" if html else "mixed")
    msg["From"] = user
    msg["To"] = to
    msg["Subject"] = subject
    if cc: msg["Cc"] = cc
    
    if body:
        msg.attach(MIMEText(body, "plain"))
    if html:
        msg.attach(MIMEText(html, "html"))
    
    if attachments:
        for filepath in attachments:
            path = Path(filepath)
            if not path.exists():
                continue
            with open(path, "rb") as f:
                part = MIMEApplication(f.read(), Name=path.name)
            part["Content-Disposition"] = f'attachment; filename="{path.name}"'
            msg.attach(part)
    
    recipients = [to]
    if cc: recipients.extend(cc.split(","))
    if bcc: recipients.extend(bcc.split(","))
    
    try:
        with smtplib.SMTP(host, port) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(user, password)
            server.sendmail(user, recipients, msg.as_string())
        
        return {"ok": True, "to": to, "subject": subject}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="Send email alerts")
    parser.add_argument("--to", required=True, help="Recipient email")
    parser.add_argument("--subject", "-s", required=True, help="Email subject")
    parser.add_argument("--body", "-b", default="", help="Plain text body")
    parser.add_argument("--html", help="HTML body")
    parser.add_argument("--file", action="append", help="Attachment (repeatable)")
    parser.add_argument("--cc", help="CC recipients")
    parser.add_argument("--bcc", help="BCC recipients")
    parser.add_argument("--preset", choices=PRESETS.keys(), help="SMTP preset")
    parser.add_argument("--stdin", action="store_true", help="Read body from stdin")
    args = parser.parse_args()
    
    body = args.body
    if args.stdin or (not body and not args.html and not sys.stdin.isatty()):
        body = sys.stdin.read()
    
    smtp_kwargs = {}
    if args.preset:
        smtp_kwargs = PRESETS[args.preset]
    
    result = send_email(
        to=args.to, subject=args.subject, body=body, html=args.html,
        attachments=args.file, cc=args.cc, bcc=args.bcc, **smtp_kwargs,
    )
    
    if result["ok"]:
        print(f"✅ Email sent to {args.to}")
    else:
        print(f"❌ Failed: {result['error']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
