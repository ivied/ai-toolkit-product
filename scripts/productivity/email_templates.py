#!/usr/bin/env python3
"""
Email Template Engine — Generate professional emails from templates.

Provides a library of common email templates (follow-ups, cold outreach,
meeting requests, etc.) with variable substitution and tone adjustment.

Usage:
    python email_templates.py --list                          # Show all templates
    python email_templates.py --template followup --name "John" --company "Acme"
    python email_templates.py --template cold_outreach --tone formal --name "Sarah"
    python email_templates.py --template meeting_request --date "Monday 2pm"

No external dependencies required.
"""

import argparse
import json
import re
import sys
from datetime import datetime

TEMPLATES = {
    "followup": {
        "subject": "Following up on our conversation",
        "body": """Hi {name},

I hope this message finds you well. I wanted to follow up on our recent conversation about {topic}.

{custom_content}

Would you be available to discuss this further? I'm flexible with timing and happy to work around your schedule.

Looking forward to hearing from you.

Best regards,
{sender}""",
        "vars": ["name", "topic", "custom_content", "sender"],
    },
    "cold_outreach": {
        "subject": "Quick question about {company}",
        "body": """Hi {name},

I came across {company} and was impressed by {impressive_thing}. I think there might be an interesting opportunity for us to work together.

{value_proposition}

Would you have 15 minutes this week for a quick chat? No pressure at all — I'd genuinely love to learn more about what you're building.

Best,
{sender}""",
        "vars": ["name", "company", "impressive_thing", "value_proposition", "sender"],
    },
    "meeting_request": {
        "subject": "Meeting request: {topic}",
        "body": """Hi {name},

I'd like to schedule a meeting to discuss {topic}.

**Proposed time:** {date}
**Duration:** {duration}
**Location/Link:** {location}

**Agenda:**
{agenda}

Please let me know if this works for you, or suggest an alternative time.

Thanks,
{sender}""",
        "vars": ["name", "topic", "date", "duration", "location", "agenda", "sender"],
    },
    "thank_you": {
        "subject": "Thank you for {reason}",
        "body": """Hi {name},

I wanted to take a moment to thank you for {reason}. It really made a difference, and I genuinely appreciate your {quality}.

{additional}

Thanks again, and I look forward to {next_step}.

Warm regards,
{sender}""",
        "vars": ["name", "reason", "quality", "additional", "next_step", "sender"],
    },
    "introduction": {
        "subject": "Introduction: {person1} meet {person2}",
        "body": """Hi {person1} and {person2},

I'd like to introduce you to each other. I think you'd have a lot to talk about.

**{person1}** — {person1_desc}
**{person2}** — {person2_desc}

{reason_for_intro}

I'll leave it to you two to connect. Enjoy the conversation!

Best,
{sender}""",
        "vars": ["person1", "person2", "person1_desc", "person2_desc", "reason_for_intro", "sender"],
    },
    "apology": {
        "subject": "Apology regarding {issue}",
        "body": """Hi {name},

I owe you an apology regarding {issue}. This was not up to the standard you deserve, and I take full responsibility.

**What happened:** {explanation}
**What we're doing about it:** {resolution}

{additional}

Thank you for your patience and understanding. Please don't hesitate to reach out if you have any questions.

Sincerely,
{sender}""",
        "vars": ["name", "issue", "explanation", "resolution", "additional", "sender"],
    },
    "project_update": {
        "subject": "Project Update: {project}",
        "body": """Hi {name},

Here's the latest update on {project}:

**Status:** {status}
**Completed this period:**
{completed}

**Next steps:**
{next_steps}

**Blockers/Risks:**
{blockers}

Let me know if you have any questions or concerns.

Best,
{sender}""",
        "vars": ["name", "project", "status", "completed", "next_steps", "blockers", "sender"],
    },
    "invoice_reminder": {
        "subject": "Friendly reminder: Invoice #{invoice_id}",
        "body": """Hi {name},

I hope you're doing well. This is a friendly reminder that invoice #{invoice_id} for {amount} is {status}.

**Invoice details:**
- Invoice #: {invoice_id}
- Amount: {amount}
- Due date: {due_date}
- Description: {description}

If you've already processed this payment, please disregard this message. Otherwise, I'd appreciate if you could look into it at your convenience.

Thank you,
{sender}""",
        "vars": ["name", "invoice_id", "amount", "status", "due_date", "description", "sender"],
    },
}

TONE_ADJUSTMENTS = {
    "formal": {"Hi": "Dear", "Thanks": "Thank you", "Best": "Best regards", "Warm regards": "Kind regards"},
    "casual": {"Dear": "Hey", "I hope this message finds you well.": "Hope you're doing great!", 
               "Best regards": "Cheers", "Sincerely": "Thanks!"},
    "friendly": {"Dear": "Hi", "I hope this message finds you well.": "Hope all is well with you! 😊"},
}


def apply_tone(text: str, tone: str) -> str:
    """Adjust email tone."""
    if tone not in TONE_ADJUSTMENTS:
        return text
    
    for original, replacement in TONE_ADJUSTMENTS[tone].items():
        text = text.replace(original, replacement)
    return text


def generate_email(template_name: str, variables: dict, tone: str = "default") -> dict:
    """Generate an email from a template."""
    if template_name not in TEMPLATES:
        raise ValueError(f"Unknown template: {template_name}. Available: {', '.join(TEMPLATES.keys())}")
    
    template = TEMPLATES[template_name]
    
    # Fill in defaults for missing variables
    defaults = {v: f"[{v}]" for v in template["vars"]}
    defaults["sender"] = variables.get("sender", "Your Name")
    defaults["custom_content"] = ""
    defaults["additional"] = ""
    defaults.update(variables)
    
    subject = template["subject"]
    body = template["body"]
    
    for var, value in defaults.items():
        subject = subject.replace(f"{{{var}}}", value)
        body = body.replace(f"{{{var}}}", value)
    
    if tone != "default":
        body = apply_tone(body, tone)
    
    return {
        "subject": subject,
        "body": body,
        "template": template_name,
        "tone": tone,
    }


def main():
    parser = argparse.ArgumentParser(description="Generate professional emails from templates")
    parser.add_argument("--list", action="store_true", help="List available templates")
    parser.add_argument("--template", "-t", help="Template name")
    parser.add_argument("--tone", choices=["default", "formal", "casual", "friendly"], default="default")
    parser.add_argument("--output", choices=["text", "json"], default="text")
    
    # Common variables
    parser.add_argument("--name", help="Recipient name")
    parser.add_argument("--sender", default="Your Name", help="Sender name")
    parser.add_argument("--company", help="Company name")
    parser.add_argument("--topic", help="Topic/subject")
    parser.add_argument("--date", help="Date/time")
    parser.add_argument("--vars", help="JSON string of additional variables")
    args = parser.parse_args()
    
    if args.list:
        print("📧 Available Email Templates:\n")
        for name, tmpl in TEMPLATES.items():
            print(f"  • {name}")
            print(f"    Variables: {', '.join(tmpl['vars'])}")
            print(f"    Subject: {tmpl['subject']}")
            print()
        return
    
    if not args.template:
        parser.error("Specify --template or use --list to see options")
    
    variables = {"sender": args.sender}
    if args.name: variables["name"] = args.name
    if args.company: variables["company"] = args.company
    if args.topic: variables["topic"] = args.topic
    if args.date: variables["date"] = args.date
    if args.vars:
        variables.update(json.loads(args.vars))
    
    email = generate_email(args.template, variables, args.tone)
    
    if args.output == "json":
        print(json.dumps(email, indent=2))
    else:
        print(f"Subject: {email['subject']}\n")
        print(email['body'])


if __name__ == "__main__":
    main()
