# 📚 Library Management System (LibraryOS)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-green.svg)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite3-lightgrey.svg)](https://www.sqlite.org/)
[![Chart.js](https://img.shields.io/badge/Visualizations-Chart.js_4-orange.svg)](https://www.chartjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A modern, full-featured **Library Management System** engineered with **Python, Flask, and SQLite3**. Features dynamic circulation tracking, automatic overdue fine calculations, one-click loan renewals, barcode/ISBN scanning with OpenLibrary metadata synchronization, interactive Chart.js analytics, automated email reminder scheduling, and instant CSV reporting.

---

## 🌟 Key Features

### 📖 Catalog & Inventory Management
- **Full Book CRUD**: Add, edit, catalog, and remove book records with ease.
- **Barcode / Camera ISBN Scanner**: Integrated HTML5 QR/Barcode scanner using phone/webcam.
- **Open Library API Auto-Discovery**: Enter or scan an ISBN to automatically fetch the book title, author, and high-res cover art.
- **Categorization & Multi-Filter**: Categorize books (Fiction, Science, Classic, Technology, etc.) and filter by real-time shelf availability.

### 👥 Patron & Membership Management
- **Patron Registration & Contact Tracking**: Manage student/patron records with unique email validation.
- **Borrowing Analytics**: Real-time counter of active loans and lifetime books borrowed per member.
- **Integrity Safeguards**: Prevents deleting patrons who currently have unreturned books checked out.

### 🔄 Circulation, Overdue Fines & One-Click Renewals
- **Intuitive Issue Workflow**: Assign available books with customizable loan durations (7, 14, 30 days).
- **Automated Overdue Fine Engine**: Daily calculation of overdue penalties based on calendar days elapsed past due date.
- **One-Click Renewal**: Quickly extend loan periods (+7 days) directly from the circulation table.
- **Return & Fine Recording**: Records return dates, computes accrued fines, and archives transaction history.

### 📊 Interactive Analytics Dashboard
- **Real-Time KPIs**: Total copies, available on-shelf count, registered patrons, active loans, overdue items, and total fines collected.
- **Dynamic Chart.js Graphs**:
  - *Most Borrowed Books* (Horizontal Bar Chart)
  - *Monthly Borrowing Trends* (Smooth Line Chart with Area Fill)
  - *Loan Status Breakdown* (Doughnut Chart: On-Time vs Overdue)
- **Recent Activity Log**: Immediate timeline of the latest check-outs and check-ins.

### 📩 Automated Due-Date Reminders
- **Universal Multi-Provider Dispatcher**:
  - **SendGrid API** for cloud transactional email.
  - **Standard SMTP** (Gmail, Outlook, Amazon SES, or custom mail servers).
  - **Simulation Mode** (gracefully logs reminders to console if API keys aren't set—ideal for local tests & recruiter demos).
- **Web UI Trigger**: Librarians can trigger on-demand reminder jobs directly with one click from the UI.
- **Cron / Scheduled Ready**: Can be run as a cron job, Render Cron Service, or GitHub Actions workflow.

### 📥 Enterprise Reporting (CSV Export)
- Download real-time spreadsheet exports for:
  - Catalog inventory (`/books/export`)
  - Member records (`/members/export`)
  - Loan and fine ledgers (`/issues/export`)

### 🎨 Modern UI & Dark Mode
- Built with a custom design system in pure CSS (no bloated frameworks).
- True Light & Dark mode toggle with persistent state saved in `localStorage`.
- Fluid, responsive mobile & desktop experience.

---

## 📂 Project Architecture

```
library-management-system/
├── app.py                 # Core Flask application (routing, models, analytics, business logic)
├── send_reminders.py       # Automated email reminder engine (SendGrid / SMTP / Simulation)
├── requirements.txt        # Production dependencies
├── Procfile                 # Process deployment definition for Render / Railway / Heroku
├── .gitignore              # Ignored files (database, logs, environment variables)
├── static/
│   └── style.css          # Modern CSS design system with light/dark theme variables
└── templates/
    ├── base.html          # Global layout, responsive navigation, flash alerts & theme toggle
    ├── index.html         # Analytics dashboard with Chart.js visualization & activity feed
    ├── books.html         # Book catalog table with search, category filtering & CSV export
    ├── book_form.html     # Book entry & edit form with camera barcode scanner & ISBN lookup
    ├── members.html       # Patron directory with borrowing metrics & CSV export
    ├── member_form.html   # Patron registration form
    ├── issues.html        # Circulation table with fine indicators, renewals & return controls
    └── issue_form.html    # Book checkout form with quick loan duration presets
```

---

## 🚀 Getting Started

### 1. Clone & Enter Repository
```bash
git clone https://github.com/divyanshu07-code/Library-Management-System.git
cd library-management-system
```

### 2. Set Up Virtual Environment (Recommended)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run Locally
```bash
python app.py
```
Open **http://127.0.0.1:5000** in your browser.  
*The SQLite database (`library.db`) is automatically initialized and pre-seeded with catalog items and sample circulation records on initial launch.*

---

## ⚙️ Environment Variables

| Variable | Required? | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | Production | `dev-library-secret-key-2026` | Flask session and flash messaging signing key |
| `PORT` | Auto by Host | `5000` | Port for the web server to listen on |
| `DAILY_FINE_RATE` | Optional | `0.50` | Overdue fee rate per day |
| `SENDGRID_API_KEY`| Optional | — | SendGrid API key for automated reminder dispatch |
| `SENDER_EMAIL` | Optional | `library@example.com` | Verified sender email address |
| `SMTP_SERVER` | Optional | — | SMTP host (e.g. `smtp.gmail.com`) for SMTP email dispatch |
| `SMTP_PORT` | Optional | `587` | Port for TLS SMTP connection |
| `SMTP_USER` | Optional | — | SMTP username / email address |
| `SMTP_PASSWORD` | Optional | — | SMTP app password |
| `REMINDER_DAYS_BEFORE` | Optional | `2` | Days ahead of due date to trigger loan reminders |

---

## 🌐 Deployment Guide

### Deploying to Render (Recommended Free/Low-Cost Host)
1. Fork or push this repository to your GitHub account.
2. In [Render Dashboard](https://dashboard.render.com), click **New +** &rarr; **Web Service**.
3. Select your repository.
4. Configure service settings:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app` (or Render will automatically detect the `Procfile`)
5. Click **Deploy Web Service**!

### Deploying to Railway
1. Click **New Project** &rarr; **Deploy from GitHub repo**.
2. Select your repository. Railway automatically reads the `Procfile` and launches `gunicorn app:app`.

---

## 💼 Resume & Interview Talking Points

- **Architectural Design**: Engineered a modular MVC-style architecture in Flask with robust SQLite foreign keys and automated schema migrations.
- **RESTful Endpoints & Third-Party Integration**: Integrated Open Library REST API to asynchronously populate book metadata and cover art via client-side fetch.
- **Financial & Circulation Logic**: Implemented business rules for inventory decrement/increment, loan tenure enforcement, dynamic penalty algorithms, and loan renewal state management.
- **Observability & Analytics**: Aggregated real-time circulation metrics using SQL window/aggregation queries visualized via responsive Chart.js components.
- **Extensible Notification Pipeline**: Designed a fallback notification pipeline supporting SendGrid API, standard TLS SMTP, and decoupled background cron execution.

---

## 📄 License
This project is licensed under the MIT License - feel free to use and customize for your own projects!
