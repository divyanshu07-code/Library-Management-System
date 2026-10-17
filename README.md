# LibraryOS: Library Management System

[![Live Demo](https://img.shields.io/badge/Live_Demo-Render-00c7b7.svg?logo=render)](https://library-management-system-1-4v7z.onrender.com/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-green.svg)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite3-lightgrey.svg)](https://www.sqlite.org/)
[![Chart.js](https://img.shields.io/badge/Charts-Chart.js_4-orange.svg)](https://www.chartjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

LibraryOS is a web-based library management system built with Python, Flask, and SQLite. It covers the full circulation lifecycle (cataloging, issuing, renewing, returning, and fine calculation) and adds an analytics dashboard, ISBN-based metadata lookup, automated due-date email reminders, and CSV exports.

**Live demo:** <https://library-management-system-1-4v7z.onrender.com/> (deployed on Render)

> The demo runs on a free-tier host and may take a short while to wake up on the first request.

If you find this project useful, please consider giving it a ⭐ on [GitHub](https://github.com/divyanshu07-code/Library-Management-System). It helps others discover it and is much appreciated.

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Email Reminders](#email-reminders)
- [Data Export](#data-export)
- [Deployment](#deployment)
- [License](#license)

---

## Features

### Catalog and Inventory
- Create, read, update, and delete book records.
- Add books by ISBN using a camera-based barcode scanner (HTML5, works with phone or webcam).
- Automatic metadata lookup (title, author, cover image) through the Open Library API.
- Category tagging and filtering, including real-time shelf availability.

### Patron Management
- Patron registration with unique email validation.
- Per-patron counters for active loans and lifetime borrowing.
- Referential safeguard: patrons with unreturned books cannot be deleted.

### Circulation and Fines
- Issue available books with selectable loan periods (7, 14, or 30 days).
- One-click renewal, extending a loan by 7 days.
- Daily overdue fine calculation based on calendar days past the due date (configurable rate).
- Return processing that records the return date, finalizes fines, and archives the transaction.

### Analytics Dashboard
- KPIs: total copies, available copies, registered patrons, active loans, overdue items, and fines collected.
- Charts (Chart.js):
  - Most borrowed books (horizontal bar)
  - Monthly borrowing trends (line with area fill)
  - Loan status breakdown, on-time vs. overdue (doughnut)
- Recent activity feed of the latest check-outs and check-ins.

### Notifications
- Due-date reminders through SendGrid, standard SMTP, or a simulation mode that logs messages to the console when no credentials are configured.
- Reminders can be triggered on demand from the web UI or run on a schedule.

### User Interface
- Custom CSS design system with no external UI framework.
- Light and dark themes, with the preference persisted in `localStorage`.
- Responsive layout for desktop and mobile.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+, Flask 3 |
| Database | SQLite 3 |
| Frontend | Jinja2 templates, vanilla JavaScript, custom CSS |
| Visualization | Chart.js 4 |
| External API | Open Library |
| Email | SendGrid API or SMTP |
| Deployment | Gunicorn, Render / Railway (via `Procfile`) |

---

## Project Structure

```
Library-Management-System/
├── app.py               # Flask application: routes, data access, analytics, business logic
├── send_reminders.py    # Email reminder engine (SendGrid / SMTP / simulation)
├── requirements.txt     # Python dependencies
├── Procfile             # Process definition for Render / Railway / Heroku
├── static/
│   └── style.css        # Design system with light/dark theme variables
└── templates/
    ├── base.html        # Layout, navigation, flash messages, theme toggle
    ├── index.html       # Analytics dashboard
    ├── books.html       # Catalog with search, filtering, and export
    ├── book_form.html   # Add/edit book form with barcode scanner and ISBN lookup
    ├── members.html     # Patron directory and borrowing metrics
    ├── member_form.html # Patron registration form
    ├── issues.html      # Circulation table with fines, renewals, and returns
    └── issue_form.html  # Checkout form with loan-duration presets
```

---

## Getting Started

### Prerequisites
- Python 3.10 or newer
- Git

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/divyanshu07-code/Library-Management-System.git
cd Library-Management-System

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python app.py
```

Open <http://127.0.0.1:5000> in your browser.

On first launch, the SQLite database (`library.db`) is created automatically and seeded with sample catalog items and circulation records.

---

## Configuration

All settings are read from environment variables.

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | Production | `dev-library-secret-key-2026` | Signing key for sessions and flash messages. **Always override in production.** |
| `PORT` | Set by host | `5000` | Port the web server listens on. |
| `DAILY_FINE_RATE` | No | `5.0` | Overdue fine charged per day. |
| `REMINDER_DAYS_BEFORE` | No | `2` | Days before the due date to send a reminder. |
| `SENDGRID_API_KEY` | No | none | SendGrid API key. |
| `SENDER_EMAIL` | No | `library@example.com` | Verified sender address. |
| `SMTP_SERVER` | No | none | SMTP host, for example `smtp.gmail.com`. |
| `SMTP_PORT` | No | `587` | SMTP port (TLS). |
| `SMTP_USER` | No | none | SMTP username. |
| `SMTP_PASSWORD` | No | none | SMTP password or app password. |

---

## Email Reminders

`send_reminders.py` selects the delivery method in this order:

1. **SendGrid**, if `SENDGRID_API_KEY` is set.
2. **SMTP**, if `SMTP_SERVER` is set.
3. **Simulation mode**, otherwise. Messages are logged to the console and nothing is sent, which is useful for local development and demos.

Reminders can be sent in two ways:

- **On demand:** librarians trigger a reminder run from the web UI.
- **Scheduled:** run the script from any scheduler, such as cron, a Render Cron Job, or a GitHub Actions workflow.

```bash
python send_reminders.py
```

---

## Data Export

The following endpoints return CSV files:

| Endpoint | Contents |
|---|---|
| `/books/export` | Catalog inventory |
| `/members/export` | Patron records |
| `/issues/export` | Loan and fine ledger |

---

## Deployment

The reference instance is already live on Render at <https://library-management-system-1-4v7z.onrender.com/>. The steps below describe how to deploy your own copy.

### Render

1. Push or fork this repository to GitHub.
2. In the [Render Dashboard](https://dashboard.render.com), choose **New +** → **Web Service** and select the repository.
3. Configure the service:
   - **Runtime:** Python 3
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn app:app` (detected automatically from the `Procfile`)
4. Add the environment variables listed in [Configuration](#configuration), at minimum `SECRET_KEY`.
5. Deploy.

### Railway

1. Choose **New Project** → **Deploy from GitHub repo** and select the repository.
2. Railway reads the `Procfile` and starts `gunicorn app:app`.

### Production notes

- SQLite stores data in a local file. On hosts with an ephemeral filesystem (including most free tiers), data is lost on redeploy or restart unless you attach a persistent disk or migrate to a managed database.
- Set a strong, unique `SECRET_KEY` before exposing the application publicly.

---

## License

Released under the [MIT License](https://opensource.org/licenses/MIT).

---

If this project helped you, a ⭐ on the repository would be greatly appreciated.
