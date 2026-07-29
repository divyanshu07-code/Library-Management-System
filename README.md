# Library Management System

A simple, complete Library Management System built with **Flask** and **SQLite**.

## Features
- Dashboard with live stats (total books, available copies, members, active issues)
- Dashboard charts: most borrowed books, busiest months, overdue vs on-time loans
- Add / edit / delete / search books
- Barcode/ISBN scanning on the Add Book form (uses your phone/webcam camera) with
  auto-lookup of title & author via the free Open Library API
- Add / delete members
- Issue books to members with a due date
- Mark books as returned, with overdue detection
- Email due-date reminders via SendGrid (run as a script or scheduled job)
- Dark mode toggle (saved per-browser)
- Pre-seeded with 10 well-known books on first run
- Clean, responsive UI (no external CSS/JS frameworks needed)

## Project Structure
```
library-management-system/
├── app.py                 # Flask app (routes + database logic)
├── send_reminders.py       # Standalone script: emails members whose books are due soon
├── requirements.txt        # Python dependencies
├── Procfile                 # Start command for Render/Railway-style hosts
├── .gitignore
├── static/
│   └── style.css
└── templates/
    ├── base.html
    ├── index.html
    ├── books.html
    ├── book_form.html
    ├── members.html
    ├── member_form.html
    ├── issues.html
    └── issue_form.html
```

The SQLite database file (`library.db`) is created automatically the first time you run the app — no manual DB setup needed.

## Environment variables

| Variable | Required? | Purpose |
|---|---|---|
| `SECRET_KEY` | Recommended in production | Flask session/flash-message signing key. Falls back to a dev-only value locally. |
| `SENDGRID_API_KEY` | Only if using email reminders | Your free SendGrid API key (sendgrid.com) |
| `SENDER_EMAIL` | Only if using email reminders | The "from" address — must be a verified sender in your SendGrid account |
| `REMINDER_DAYS_BEFORE` | Optional | How many days before the due date to send a reminder. Default: `2` |
| `PORT` | Set automatically by most hosts | Port the app listens on. Defaults to `5000` locally. |

Set them locally before running a command, e.g.:
```bash
export SENDGRID_API_KEY="your-key-here"
export SENDER_EMAIL="you@example.com"
python send_reminders.py
```
On Windows (cmd): `set SENDGRID_API_KEY=your-key-here`

## Email reminders

`send_reminders.py` checks for any active loan due in `REMINDER_DAYS_BEFORE` days and
emails the member via SendGrid. Run it manually, or schedule it:
- **Render**: use a "Cron Job" service pointed at `python send_reminders.py`
- **Linux/Mac cron**: `0 8 * * * cd /path/to/project && venv/bin/python send_reminders.py`
- **GitHub Actions**: a scheduled workflow that checks out the repo and runs the script

## Barcode scanning notes

The camera-based ISBN scanner needs either **HTTPS** or **localhost** to access the
device camera (browsers block camera access on plain HTTP for any other host) — this
works automatically once deployed on Render/PythonAnywhere/etc., which serve over HTTPS.

## Run it locally

1. **Unzip the project**, then move into the folder:
   ```bash
   cd library-management-system
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app**:
   ```bash
   python app.py
   ```

5. Open your browser at **http://127.0.0.1:5000**

## Push this project to GitHub

From inside the `library-management-system` folder:

```bash
git init
git add .
git commit -m "Initial commit: Library Management System"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo-name>.git
git push -u origin main
```

Replace `<your-username>/<your-repo-name>` with your GitHub username and a repository you create on github.com (click **New repository**, and don't initialize it with a README so there's no merge conflict).

## Notes
- `app.secret_key` in `app.py` is a placeholder — change it before deploying anywhere public.
- `library.db` is git-ignored so your database won't be committed; each fresh clone starts empty.
- To reset the database at any time, just delete `library.db` and restart the app.

If you like this project, consider giving it a ⭐ and sharing your feedback.
