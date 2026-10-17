"""
send_reminders.py
------------------
Sends automated email reminders to members whose borrowed books are due soon.

Supports 3 modes:
1. SendGrid API (when SENDGRID_API_KEY and SENDER_EMAIL are configured)
2. Standard SMTP (when SMTP_SERVER, SMTP_USER, SMTP_PASSWORD are configured)
3. Simulated / Dry-Run (when no credentials are provided - logs to console, perfect for local demo & portfolio review!)

Usage:
    - Run standalone: python send_reminders.py
    - Run as a scheduled cron job (Render Cron, Railway, or Linux/Mac crontab)
    - Called on-demand via the Web UI route /reminders/send-now
"""

import os
import smtplib
import sqlite3
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests

DB_PATH = os.path.join(os.path.dirname(__file__), "library.db")

# Configuration via environment variables
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "library@example.com")
REMINDER_DAYS_BEFORE = int(os.environ.get("REMINDER_DAYS_BEFORE", 2))

# SMTP Fallback Configuration
SMTP_SERVER = os.environ.get("SMTP_SERVER")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")


def get_upcoming_due_issues():
    """Fetches active loans where due_date matches today + REMINDER_DAYS_BEFORE."""
    if not os.path.exists(DB_PATH):
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    target_date = (datetime.today().date() + timedelta(days=REMINDER_DAYS_BEFORE)).isoformat()

    rows = conn.execute(
        """
        SELECT members.name, members.email, books.title, issues.due_date
        FROM issues
        JOIN members ON members.id = issues.member_id
        JOIN books ON books.id = issues.book_id
        WHERE issues.return_date IS NULL AND issues.due_date = ?
        """,
        (target_date,),
    ).fetchall()
    conn.close()
    return rows


def send_via_sendgrid(to_email, subject, body):
    """Sends email via SendGrid V3 REST API."""
    try:
        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {SENDGRID_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "personalizations": [{"to": [{"email": to_email}]}],
                "from": {"email": SENDER_EMAIL},
                "subject": subject,
                "content": [{"type": "text/plain", "value": body}],
            },
            timeout=10,
        )
        return response.status_code in (200, 201, 202)
    except Exception as e:
        print(f"SendGrid Error: {e}")
        return False


def send_via_smtp(to_email, subject, body):
    """Sends email via standard SMTP server (e.g. Gmail / Outlook / Custom)."""
    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.starttls()
            if SMTP_USER and SMTP_PASSWORD:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"SMTP Error: {e}")
        return False


def send_email(to_email, subject, body):
    """Dispatches email using available provider, or runs simulation."""
    if SENDGRID_API_KEY:
        return send_via_sendgrid(to_email, subject, body)
    elif SMTP_SERVER:
        return send_via_smtp(to_email, subject, body)
    else:
        # Simulation Mode: Log output cleanly for interview/local demonstration
        print(f"[SIMULATED EMAIL DISPATCH] To: {to_email} | Subject: {subject}")
        print(f"Content: {body.replace(chr(10), ' ')}")
        return True


def run_reminder_check():
    """Runs reminder check and returns detailed summary dict."""
    due_soon = get_upcoming_due_issues()
    results = {"total": len(due_soon), "success": 0, "failed": 0, "logs": []}

    for row in due_soon:
        subject = f'Library Reminder: "{row["title"]}" is due soon'
        body = (
            f'Hi {row["name"]},\n\n'
            f'This is a friendly reminder that your borrowed book "{row["title"]}" '
            f'is due on {row["due_date"]}.\n\n'
            f"Please return or renew it on time to avoid overdue charges.\n\n"
            f"Best regards,\nYour Library Team"
        )
        ok = send_email(row["email"], subject, body)
        status = "SENT" if ok else "FAILED"
        if ok:
            results["success"] += 1
        else:
            results["failed"] += 1
        results["logs"].append(f"{status}: {row['email']} - {row['title']} (Due {row['due_date']})")

    return results


def main():
    print("=" * 60)
    print("Library Management System - Automated Reminder Dispatcher")
    print("=" * 60)

    if not SENDGRID_API_KEY and not SMTP_SERVER:
        print("Note: Running in SIMULATION MODE (No email credentials provided).")
        print("Set SENDGRID_API_KEY or SMTP_SERVER to dispatch real emails.\n")

    summary = run_reminder_check()
    if summary["total"] == 0:
        print(f"No loans due in {REMINDER_DAYS_BEFORE} days. Everything is up to date!")
    else:
        for log in summary["logs"]:
            print(log)
        print(f"\nCompleted: {summary['success']} sent, {summary['failed']} failed out of {summary['total']}.")


if __name__ == "__main__":
    main()
