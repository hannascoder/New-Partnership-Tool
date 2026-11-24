"""Sends reports/weekly_brief.md (text) and site/brief.html (html) by e-mail. Free: plain SMTP with an account the owner provides.

Needs these GitHub secrets (nothing is stored in the public repository):
  BRIEF_SMTP_HOST, BRIEF_SMTP_PORT (587 = STARTTLS, 465 = SSL), BRIEF_SMTP_USER, BRIEF_SMTP_PASS, BRIEF_FROM, BRIEF_TO (comma separated)
If one is missing nothing is sent and the run still succeeds ("not configured").
"""
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NEED = ["BRIEF_SMTP_HOST", "BRIEF_SMTP_PORT", "BRIEF_SMTP_USER", "BRIEF_SMTP_PASS", "BRIEF_FROM", "BRIEF_TO"]


def main(smtp_factory=None):
    missing = [k for k in NEED if not os.environ.get(k, "").strip()]
    if missing:
        print("e-mail not configured (missing: " + ", ".join(missing) + "): nothing sent")
        return 0
    text = (ROOT / "reports" / "weekly_brief.md").read_text(encoding="utf-8")
    page = (ROOT / "site" / "brief.html").read_text(encoding="utf-8")
    subject = text.splitlines()[0].lstrip("# ").strip()
    msg = EmailMessage()
    msg["Subject"], msg["From"] = subject, os.environ["BRIEF_FROM"]
    to = [x.strip() for x in os.environ["BRIEF_TO"].split(",") if x.strip()]
    msg["To"] = ", ".join(to)
    msg.set_content(text)
    msg.add_alternative(page, subtype="html")
    host, port = os.environ["BRIEF_SMTP_HOST"], int(os.environ["BRIEF_SMTP_PORT"])
    ctx = ssl.create_default_context()
    if smtp_factory:
        s = smtp_factory(host, port)
    elif port == 465:
        s = smtplib.SMTP_SSL(host, port, context=ctx, timeout=60)
    else:
        s = smtplib.SMTP(host, port, timeout=60)
        s.starttls(context=ctx)
    with s:
        s.login(os.environ["BRIEF_SMTP_USER"], os.environ["BRIEF_SMTP_PASS"])
        s.send_message(msg)
    print(f"sent to {len(to)} recipient(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
