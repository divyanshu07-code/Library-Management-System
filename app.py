"""
Library Management System - Flask Application
Features:
- Book Management (CRUD, ISBN barcode scanning, OpenLibrary API auto-fill)
- Member Management with borrowing histories
- Issue / Return workflows with automatic overdue calculation and fine tracking
- One-click loan renewal (+7 or +14 days)
- Live Analytics Dashboard with Chart.js visualization
- CSV Data Export for Books, Members, and Loan Records
- Standalone and on-demand reminder dispatch
- Dark / Light responsive interface
"""

import os
import sqlite3
import csv
import io
from datetime import datetime, timedelta
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    Response,
    jsonify,
)
import requests as pyrequests

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-library-secret-key-2026")
DB_PATH = os.path.join(os.path.dirname(__file__), "library.db")

DAILY_FINE_RATE = float(os.environ.get("DAILY_FINE_RATE", 0.50))  # Currency units per day


# ==============================================================================
# Database Helpers & Migration
# ==============================================================================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def calculate_fine(due_date_str, return_date_str=None):
    """Calculates overdue fine based on due date and return date (or today)."""
    try:
        due_date = datetime.fromisoformat(due_date_str).date()
        end_date = datetime.fromisoformat(return_date_str).date() if return_date_str else datetime.today().date()
        if end_date > due_date:
            days_overdue = (end_date - due_date).days
            return round(days_overdue * DAILY_FINE_RATE, 2), days_overdue
    except Exception:
        pass
    return 0.0, 0


def init_db():
    """Initializes tables and safely applies migrations if columns are missing."""
    conn = get_db()
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            isbn TEXT UNIQUE,
            category TEXT NOT NULL DEFAULT 'General',
            quantity INTEGER NOT NULL DEFAULT 1,
            available INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            member_id INTEGER NOT NULL,
            issue_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            return_date TEXT,
            fine_amount REAL DEFAULT 0.0,
            fine_paid INTEGER DEFAULT 0,
            renewal_count INTEGER DEFAULT 0,
            FOREIGN KEY (book_id) REFERENCES books (id) ON DELETE CASCADE,
            FOREIGN KEY (member_id) REFERENCES members (id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()

    # Safe Schema Migrations for existing databases
    existing_book_cols = [c["name"] for c in conn.execute("PRAGMA table_info(books)").fetchall()]
    if "category" not in existing_book_cols:
        conn.execute("ALTER TABLE books ADD COLUMN category TEXT NOT NULL DEFAULT 'General'")

    existing_issue_cols = [c["name"] for c in conn.execute("PRAGMA table_info(issues)").fetchall()]
    if "fine_amount" not in existing_issue_cols:
        conn.execute("ALTER TABLE issues ADD COLUMN fine_amount REAL DEFAULT 0.0")
    if "fine_paid" not in existing_issue_cols:
        conn.execute("ALTER TABLE issues ADD COLUMN fine_paid INTEGER DEFAULT 0")
    if "renewal_count" not in existing_issue_cols:
        conn.execute("ALTER TABLE issues ADD COLUMN renewal_count INTEGER DEFAULT 0")

    conn.commit()
    conn.close()


def seed_books():
    """Populates initial book collection and sample activity if empty."""
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) c FROM books").fetchone()["c"]
    if count == 0:
        famous_books = [
            ("To Kill a Mockingbird", "Harper Lee", "9780061120084", "Fiction", 4),
            ("1984", "George Orwell", "9780451524935", "Dystopian", 5),
            ("Pride and Prejudice", "Jane Austen", "9780141439518", "Classic", 3),
            ("The Great Gatsby", "F. Scott Fitzgerald", "9780743273565", "Classic", 4),
            ("The Hobbit", "J.R.R. Tolkien", "9780547928227", "Fantasy", 3),
            ("Harry Potter and the Sorcerer's Stone", "J.K. Rowling", "9780590353427", "Fantasy", 6),
            ("The Catcher in the Rye", "J.D. Salinger", "9780316769488", "Fiction", 3),
            ("Sapiens: A Brief History of Humankind", "Yuval Noah Harari", "9780062316097", "Non-Fiction", 4),
            ("The Alchemist", "Paulo Coelho", "9780061122415", "Philosophy", 4),
            ("A Brief History of Time", "Stephen Hawking", "9780553380163", "Science", 3),
            ("Clean Code", "Robert C. Martin", "9780132350884", "Technology", 5),
            ("Atomic Habits", "James Clear", "9780735211292", "Self-Help", 5),
        ]
        conn.executemany(
            "INSERT OR IGNORE INTO books (title, author, isbn, category, quantity, available) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [(t, a, i, c, q, q) for t, a, i, c, q in famous_books],
        )
        conn.commit()

        # Seed sample members and initial loan demo
        sample_members = [
            ("Alice Smith", "alice.smith@example.com", "555-0101"),
            ("Bob Jones", "bob.jones@example.com", "555-0102"),
            ("Charlie Brown", "charlie.b@example.com", "555-0103"),
            ("Diana Prince", "diana.p@example.com", "555-0104"),
        ]
        conn.executemany(
            "INSERT OR IGNORE INTO members (name, email, phone) VALUES (?, ?, ?)",
            sample_members,
        )
        conn.commit()

        # Seed realistic loan records
        today = datetime.today().date()
        book1 = conn.execute("SELECT id FROM books WHERE title LIKE '1984%'").fetchone()
        book2 = conn.execute("SELECT id FROM books WHERE title LIKE 'To Kill a%'").fetchone()
        book3 = conn.execute("SELECT id FROM books WHERE title LIKE 'Atomic Habits%'").fetchone()
        member1 = conn.execute("SELECT id FROM members WHERE email='alice.smith@example.com'").fetchone()
        member2 = conn.execute("SELECT id FROM members WHERE email='bob.jones@example.com'").fetchone()

        if book1 and member1:
            # Active normal issue
            issue_d = (today - timedelta(days=4)).isoformat()
            due_d = (today + timedelta(days=10)).isoformat()
            conn.execute(
                "INSERT INTO issues (book_id, member_id, issue_date, due_date) VALUES (?, ?, ?, ?)",
                (book1["id"], member1["id"], issue_d, due_d),
            )
            conn.execute("UPDATE books SET available = available - 1 WHERE id=?", (book1["id"],))

        if book2 and member2:
            # Overdue issue for demo
            issue_d = (today - timedelta(days=20)).isoformat()
            due_d = (today - timedelta(days=3)).isoformat()
            conn.execute(
                "INSERT INTO issues (book_id, member_id, issue_date, due_date) VALUES (?, ?, ?, ?)",
                (book2["id"], member2["id"], issue_d, due_d),
            )
            conn.execute("UPDATE books SET available = available - 1 WHERE id=?", (book2["id"],))

        if book3 and member1:
            # Returned issue with fine demo
            issue_d = (today - timedelta(days=30)).isoformat()
            due_d = (today - timedelta(days=16)).isoformat()
            ret_d = (today - timedelta(days=14)).isoformat()
            conn.execute(
                "INSERT INTO issues (book_id, member_id, issue_date, due_date, return_date, fine_amount, fine_paid) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (book3["id"], member1["id"], issue_d, due_d, ret_d, 1.0, 1),
            )

        conn.commit()
    conn.close()


# ==============================================================================
# Dashboard Route
# ==============================================================================

@app.route("/")
def index():
    conn = get_db()
    total_books = conn.execute("SELECT COALESCE(SUM(quantity), 0) c FROM books").fetchone()["c"]
    available_books = conn.execute("SELECT COALESCE(SUM(available), 0) c FROM books").fetchone()["c"]
    total_members = conn.execute("SELECT COUNT(*) c FROM members").fetchone()["c"]
    active_issues = conn.execute("SELECT COUNT(*) c FROM issues WHERE return_date IS NULL").fetchone()["c"]

    # Fines metrics
    total_fines_collected = conn.execute(
        "SELECT COALESCE(SUM(fine_amount), 0.0) c FROM issues WHERE fine_paid = 1"
    ).fetchone()["c"]

    # --- Chart: Most borrowed books ---
    top_books_rows = conn.execute(
        """
        SELECT books.title, COUNT(issues.id) AS times_borrowed
        FROM issues
        JOIN books ON books.id = issues.book_id
        GROUP BY issues.book_id
        ORDER BY times_borrowed DESC
        LIMIT 5
        """
    ).fetchall()
    top_books_labels = [r["title"] for r in top_books_rows]
    top_books_counts = [r["times_borrowed"] for r in top_books_rows]

    # --- Chart: Monthly borrowing trends ---
    monthly_rows = conn.execute(
        """
        SELECT strftime('%Y-%m', issue_date) AS month, COUNT(*) AS c
        FROM issues
        GROUP BY month
        ORDER BY month
        LIMIT 6
        """
    ).fetchall()
    monthly_labels = [r["month"] for r in monthly_rows]
    monthly_counts = [r["c"] for r in monthly_rows]

    # --- Overdue vs On-time Breakdown ---
    today_str = datetime.today().date().isoformat()
    overdue_count = conn.execute(
        "SELECT COUNT(*) c FROM issues WHERE return_date IS NULL AND due_date < ?", (today_str,)
    ).fetchone()["c"]
    on_time_count = max(active_issues - overdue_count, 0)

    # --- Recent Activity Feed (Latest 6 transactions) ---
    recent_activity = conn.execute(
        """
        SELECT issues.id, books.title AS book_title, members.name AS member_name,
               issues.issue_date, issues.due_date, issues.return_date, issues.fine_amount
        FROM issues
        JOIN books ON books.id = issues.book_id
        JOIN members ON members.id = issues.member_id
        ORDER BY issues.id DESC
        LIMIT 6
        """
    ).fetchall()

    conn.close()
    return render_template(
        "index.html",
        total_books=total_books,
        available_books=available_books,
        total_members=total_members,
        active_issues=active_issues,
        total_fines_collected=f"{total_fines_collected:.2f}",
        top_books_labels=top_books_labels,
        top_books_counts=top_books_counts,
        monthly_labels=monthly_labels,
        monthly_counts=monthly_counts,
        overdue_count=overdue_count,
        on_time_count=on_time_count,
        recent_activity=recent_activity,
        today=datetime.today().date(),
    )


# ==============================================================================
# ISBN Barcode Scanner & OpenLibrary Lookup API
# ==============================================================================

@app.route("/api/lookup-isbn/<isbn>")
def lookup_isbn(isbn):
    clean_isbn = "".join(ch for ch in isbn if ch.isalnum())
    if not clean_isbn:
        return jsonify({"found": False, "error": "Invalid ISBN"}), 400

    try:
        resp = pyrequests.get(
            f"https://openlibrary.org/api/books?bibkeys=ISBN:{clean_isbn}&format=json&jscmd=data",
            timeout=5,
        )
        if resp.status_code == 200:
            data = resp.json()
            book_data = data.get(f"ISBN:{clean_isbn}")
            if book_data:
                authors = ", ".join(a.get("name", "") for a in book_data.get("authors", []))
                cover_url = book_data.get("cover", {}).get("medium", "")
                return jsonify({
                    "found": True,
                    "title": book_data.get("title", ""),
                    "author": authors or "Unknown",
                    "cover_url": cover_url,
                })
        return jsonify({"found": False})
    except Exception as e:
        return jsonify({"found": False, "error": str(e)}), 500


# ==============================================================================
# Books Management (CRUD + Search + Category + CSV Export)
# ==============================================================================

@app.route("/books")
def books():
    conn = get_db()
    search = request.args.get("q", "").strip()
    status_filter = request.args.get("status", "all").strip().lower()
    category_filter = request.args.get("category", "all").strip()

    query = "SELECT * FROM books WHERE 1=1"
    params = []

    if search:
        query += " AND (title LIKE ? OR author LIKE ? OR isbn LIKE ? OR category LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%"])

    if status_filter == "available":
        query += " AND available > 0"
    elif status_filter == "borrowed":
        query += " AND available < quantity"
    elif status_filter == "outofstock":
        query += " AND available = 0"

    if category_filter and category_filter != "all":
        query += " AND category = ?"
        params.append(category_filter)

    query += " ORDER BY title ASC"
    rows = conn.execute(query, params).fetchall()

    categories = [r["category"] for r in conn.execute("SELECT DISTINCT category FROM books ORDER BY category").fetchall()]
    conn.close()

    return render_template(
        "books.html",
        books=rows,
        search=search,
        status_filter=status_filter,
        category_filter=category_filter,
        categories=categories,
    )


@app.route("/books/add", methods=["GET", "POST"])
def add_book():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        isbn = request.form.get("isbn", "").strip()
        category = request.form.get("category", "General").strip() or "General"
        quantity = max(int(request.form.get("quantity", 1)), 1)

        if not title or not author:
            flash("Book title and author are required.", "error")
            return redirect(url_for("add_book"))

        conn = get_db()
        try:
            conn.execute(
                """
                INSERT INTO books (title, author, isbn, category, quantity, available)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (title, author, isbn or None, category, quantity, quantity),
            )
            conn.commit()
            flash(f'"{title}" added to library catalog successfully!', "success")
        except sqlite3.IntegrityError:
            flash(f"A book with ISBN {isbn} already exists in the catalog.", "error")
        finally:
            conn.close()
        return redirect(url_for("books"))

    return render_template("book_form.html", book=None)


@app.route("/books/edit/<int:book_id>", methods=["GET", "POST"])
def edit_book(book_id):
    conn = get_db()
    book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    if not book:
        conn.close()
        flash("Requested book not found.", "error")
        return redirect(url_for("books"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        isbn = request.form.get("isbn", "").strip()
        category = request.form.get("category", "General").strip() or "General"
        quantity = max(int(request.form.get("quantity", 1)), 1)

        issued_count = book["quantity"] - book["available"]
        if quantity < issued_count:
            flash(f"Cannot reduce quantity below {issued_count} (copies currently issued).", "error")
            conn.close()
            return redirect(url_for("edit_book", book_id=book_id))

        new_available = quantity - issued_count

        try:
            conn.execute(
                """
                UPDATE books
                SET title = ?, author = ?, isbn = ?, category = ?, quantity = ?, available = ?
                WHERE id = ?
                """,
                (title, author, isbn or None, category, quantity, new_available, book_id),
            )
            conn.commit()
            flash("Book details updated successfully.", "success")
        except sqlite3.IntegrityError:
            flash("Another book with this ISBN already exists.", "error")
        finally:
            conn.close()
        return redirect(url_for("books"))

    conn.close()
    return render_template("book_form.html", book=book)


@app.route("/books/delete/<int:book_id>", methods=["POST"])
def delete_book(book_id):
    conn = get_db()
    active = conn.execute(
        "SELECT COUNT(*) c FROM issues WHERE book_id = ? AND return_date IS NULL", (book_id,)
    ).fetchone()["c"]

    if active > 0:
        flash(f"Cannot delete book: {active} copy is currently issued to members.", "error")
    else:
        conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()
        flash("Book removed from catalog.", "success")

    conn.close()
    return redirect(url_for("books"))


@app.route("/books/export")
def export_books_csv():
    conn = get_db()
    books = conn.execute("SELECT id, title, author, isbn, category, quantity, available FROM books ORDER BY title").fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Title", "Author", "ISBN", "Category", "Total Copies", "Available Copies", "Issued Copies"])
    for b in books:
        issued = b["quantity"] - b["available"]
        writer.writerow([b["id"], b["title"], b["author"], b["isbn"] or "N/A", b["category"], b["quantity"], b["available"], issued])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=library_books_export.csv"},
    )


# ==============================================================================
# Members Management (CRUD + Stats + History + CSV Export)
# ==============================================================================

@app.route("/members")
def members():
    conn = get_db()
    search = request.args.get("q", "").strip()

    query = """
        SELECT members.*,
               COUNT(CASE WHEN issues.return_date IS NULL THEN 1 END) AS active_loans,
               COUNT(issues.id) AS total_borrowed
        FROM members
        LEFT JOIN issues ON issues.member_id = members.id
    """
    params = []
    if search:
        query += " WHERE members.name LIKE ? OR members.email LIKE ? OR members.phone LIKE ?"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    query += " GROUP BY members.id ORDER BY members.name ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()

    return render_template("members.html", members=rows, search=search)


@app.route("/members/add", methods=["GET", "POST"])
def add_member():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()

        if not name or not email:
            flash("Member name and email are required.", "error")
            return redirect(url_for("add_member"))

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO members (name, email, phone) VALUES (?, ?, ?)",
                (name, email, phone or None),
            )
            conn.commit()
            flash(f"Member {name} registered successfully!", "success")
        except sqlite3.IntegrityError:
            flash(f"A member with email {email} is already registered.", "error")
        finally:
            conn.close()
        return redirect(url_for("members"))

    return render_template("member_form.html")


@app.route("/members/delete/<int:member_id>", methods=["POST"])
def delete_member(member_id):
    conn = get_db()
    active = conn.execute(
        "SELECT COUNT(*) c FROM issues WHERE member_id = ? AND return_date IS NULL", (member_id,)
    ).fetchone()["c"]

    if active > 0:
        flash(f"Cannot delete member: they have {active} books currently issued.", "error")
    else:
        conn.execute("DELETE FROM members WHERE id = ?", (member_id,))
        conn.commit()
        flash("Member deleted successfully.", "success")

    conn.close()
    return redirect(url_for("members"))


@app.route("/members/export")
def export_members_csv():
    conn = get_db()
    members = conn.execute(
        """
        SELECT members.id, members.name, members.email, members.phone, members.created_at,
               COUNT(CASE WHEN issues.return_date IS NULL THEN 1 END) AS active_loans,
               COUNT(issues.id) AS total_borrowed
        FROM members
        LEFT JOIN issues ON issues.member_id = members.id
        GROUP BY members.id
        ORDER BY members.name
        """
    ).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "Email", "Phone", "Registration Date", "Active Loans", "Total Loans"])
    for m in members:
        writer.writerow([m["id"], m["name"], m["email"], m["phone"] or "N/A", m["created_at"], m["active_loans"], m["total_borrowed"]])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=library_members_export.csv"},
    )


# ==============================================================================
# Issue / Return / Renewal / Fine System
# ==============================================================================

@app.route("/issues")
def issues():
    conn = get_db()
    status_filter = request.args.get("status", "all").strip().lower()
    search = request.args.get("q", "").strip()

    query = """
        SELECT issues.*, books.title AS book_title, books.isbn AS book_isbn,
               members.name AS member_name, members.email AS member_email
        FROM issues
        JOIN books ON books.id = issues.book_id
        JOIN members ON members.id = issues.member_id
        WHERE 1=1
    """
    params = []
    today = datetime.today().date()
    today_str = today.isoformat()

    if search:
        query += " AND (books.title LIKE ? OR members.name LIKE ? OR members.email LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    if status_filter == "active":
        query += " AND issues.return_date IS NULL"
    elif status_filter == "overdue":
        query += " AND issues.return_date IS NULL AND issues.due_date < ?"
        params.append(today_str)
    elif status_filter == "returned":
        query += " AND issues.return_date IS NULL"

    query += " ORDER BY issues.return_date IS NOT NULL, issues.due_date ASC"
    raw_rows = conn.execute(query, params).fetchall()

    processed_issues = []
    for row in raw_rows:
        row_dict = dict(row)
        is_returned = row_dict["return_date"] is not None
        calculated_fine, overdue_days = calculate_fine(
            row_dict["due_date"],
            row_dict["return_date"] if is_returned else None,
        )
        row_dict["current_fine"] = row_dict["fine_amount"] if is_returned else calculated_fine
        row_dict["is_overdue"] = not is_returned and row_dict["due_date"] < today_str
        row_dict["overdue_days"] = overdue_days
        processed_issues.append(row_dict)

    conn.close()
    return render_template(
        "issues.html",
        issues=processed_issues,
        status_filter=status_filter,
        search=search,
        today=today,
    )


@app.route("/issues/new", methods=["GET", "POST"])
def issue_book():
    conn = get_db()
    if request.method == "POST":
        book_id = int(request.form.get("book_id", 0))
        member_id = int(request.form.get("member_id", 0))
        days = max(int(request.form.get("days", 14)), 1)

        book = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if not book or book["available"] < 1:
            flash("Selected book is currently out of stock.", "error")
            conn.close()
            return redirect(url_for("issue_book"))

        member = conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
        if not member:
            flash("Invalid member selected.", "error")
            conn.close()
            return redirect(url_for("issue_book"))

        issue_date = datetime.today().date()
        due_date = issue_date + timedelta(days=days)

        conn.execute(
            """
            INSERT INTO issues (book_id, member_id, issue_date, due_date)
            VALUES (?, ?, ?, ?)
            """,
            (book_id, member_id, issue_date.isoformat(), due_date.isoformat()),
        )
        conn.execute("UPDATE books SET available = available - 1 WHERE id = ?", (book_id,))
        conn.commit()
        conn.close()

        flash(f'"{book["title"]}" successfully issued to {member["name"]}. Due: {due_date.isoformat()}', "success")
        return redirect(url_for("issues"))

    available_books = conn.execute("SELECT * FROM books WHERE available > 0 ORDER BY title").fetchall()
    all_members = conn.execute("SELECT * FROM members ORDER BY name").fetchall()
    conn.close()
    return render_template("issue_form.html", books=available_books, members=all_members)


@app.route("/issues/return/<int:issue_id>", methods=["POST"])
def return_book(issue_id):
    conn = get_db()
    record = conn.execute("SELECT * FROM issues WHERE id = ?", (issue_id,)).fetchone()
    if not record or record["return_date"] is not None:
        flash("Invalid or already returned loan record.", "error")
        conn.close()
        return redirect(url_for("issues"))

    today = datetime.today().date().isoformat()
    fine, days_overdue = calculate_fine(record["due_date"])
    fine_collected = 1 if fine > 0 else 0

    conn.execute(
        """
        UPDATE issues
        SET return_date = ?, fine_amount = ?, fine_paid = ?
        WHERE id = ?
        """,
        (today, fine, fine_collected, issue_id),
    )
    conn.execute("UPDATE books SET available = available + 1 WHERE id = ?", (record["book_id"],))
    conn.commit()
    conn.close()

    if fine > 0:
        flash(f"Book returned. Overdue by {days_overdue} days. Fine of ${fine:.2f} marked as collected.", "warning")
    else:
        flash("Book successfully returned on time!", "success")

    return redirect(url_for("issues"))


@app.route("/issues/renew/<int:issue_id>", methods=["POST"])
def renew_book(issue_id):
    days_to_add = int(request.form.get("extend_days", 7))
    conn = get_db()
    record = conn.execute("SELECT * FROM issues WHERE id = ?", (issue_id,)).fetchone()

    if not record or record["return_date"] is not None:
        flash("Cannot renew: Record is invalid or already returned.", "error")
        conn.close()
        return redirect(url_for("issues"))

    # Calculate new due date from previous due date or today
    curr_due = datetime.fromisoformat(record["due_date"]).date()
    new_due = max(curr_due, datetime.today().date()) + timedelta(days=days_to_add)

    conn.execute(
        """
        UPDATE issues
        SET due_date = ?, renewal_count = renewal_count + 1
        WHERE id = ?
        """,
        (new_due.isoformat(), issue_id),
    )
    conn.commit()
    conn.close()

    flash(f"Loan successfully renewed! New due date is {new_due.isoformat()}.", "success")
    return redirect(url_for("issues"))


@app.route("/issues/export")
def export_issues_csv():
    conn = get_db()
    records = conn.execute(
        """
        SELECT issues.id, books.title AS book_title, books.isbn,
               members.name AS member_name, members.email AS member_email,
               issues.issue_date, issues.due_date, issues.return_date,
               issues.fine_amount, issues.fine_paid, issues.renewal_count
        FROM issues
        JOIN books ON books.id = issues.book_id
        JOIN members ON members.id = issues.member_id
        ORDER BY issues.id DESC
        """
    ).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Issue ID", "Book Title", "ISBN", "Member Name", "Member Email",
        "Issue Date", "Due Date", "Return Date", "Status", "Fine Amount", "Fine Paid", "Renewals"
    ])

    today_str = datetime.today().date().isoformat()
    for r in records:
        if r["return_date"]:
            status = "Returned"
        elif r["due_date"] < today_str:
            status = "Overdue"
        else:
            status = "Active"

        writer.writerow([
            r["id"], r["book_title"], r["isbn"] or "N/A", r["member_name"], r["member_email"],
            r["issue_date"], r["due_date"], r["return_date"] or "Pending",
            status, f"${r['fine_amount']:.2f}", "Yes" if r["fine_paid"] else "No", r["renewal_count"]
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=library_issues_export.csv"},
    )


# ==============================================================================
# Email Reminders Trigger via Web UI
# ==============================================================================

@app.route("/reminders/send-now", methods=["POST"])
def trigger_reminders_now():
    """Triggers the reminder engine directly from the Web UI."""
    try:
        from send_reminders import run_reminder_check
        results = run_reminder_check()
        if results["total"] == 0:
            flash("Reminder check finished: No loans are due within the reminder window.", "info")
        else:
            flash(
                f"Reminders processed! {results['success']} sent successfully, {results['failed']} failed out of {results['total']}.",
                "success" if results["failed"] == 0 else "warning",
            )
    except Exception as e:
        flash(f"Error running reminders: {str(e)}", "error")

    return redirect(url_for("issues"))


# ==============================================================================
# Initialization & Entry Point
# ==============================================================================

init_db()
seed_books()

if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
