"""
send_reminders.py
------------------
Sends an email reminder to members whose borrowed books are due soon.

Run manually:
    python send_reminders.py

Run automatically:
    Set this up as a scheduled/cron job (e.g. once a day) on your host,
    or as a Render "Cron Job", GitHub Actions scheduled workflow, or
    a simple OS cron entry:
        0 8 * * * cd /path/to/project && venv/bin/python send_reminders.py

Requires environment variables:
    SENDGRID_API_KEY   - your free SendGrid API key (sendgrid.com)
    SENDER_EMAIL       - the "from" address (must be a verified sender in SendGrid)
    REMINDER_DAYS_BEFORE (optional) - how many days before the due date to remind. Default: 2
"""

import os
import sqlite3
from datetime import datetime, timedelta

import requests

DB_PATH = os.path.join(os.path.dirname(__file__), "library.db")
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL")
REMINDER_DAYS_BEFORE = int(os.environ.get("REMINDER_DAYS_BEFORE", 2))


def get_upcoming_due_issues():
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


def send_email(to_email, subject, body):
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


def main():
    if not SENDGRID_API_KEY or not SENDER_EMAIL:
        print("SENDGRID_API_KEY and SENDER_EMAIL must be set as environment variables.")
        return

    due_soon = get_upcoming_due_issues()
    if not due_soon:
        print("No reminders to send today.")
        return

    for row in due_soon:
        subject = f'Reminder: "{row["title"]}" is due soon'
        body = (
            f'Hi {row["name"]},\n\n'
            f'This is a friendly reminder that your borrowed book "{row["title"]}" '
            f'is due on {row["due_date"]}.\n\n'
            f"Please return it on time to avoid overdue fees.\n\n"
            f"Thank you,\nYour Library"
        )
        ok = send_email(row["email"], subject, body)
        status = "sent" if ok else "FAILED"
        print(f'Reminder {status} -> {row["email"]} ("{row["title"]}", due {row["due_date"]})')


if __name__ == "__main__":
    main()
