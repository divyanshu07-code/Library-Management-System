from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-fallback-key")
DB_PATH = os.path.join(os.path.dirname(__file__), "library.db")


# ---------- Database helpers ----------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            isbn TEXT UNIQUE,
            quantity INTEGER NOT NULL DEFAULT 1,
            available INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT
        );

        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            member_id INTEGER NOT NULL,
            issue_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            return_date TEXT,
            FOREIGN KEY (book_id) REFERENCES books (id),
            FOREIGN KEY (member_id) REFERENCES members (id)
        );
        """
    )
    conn.commit()
    conn.close()


def seed_books():
    """Populate a few well-known books on first run, so the app isn't empty."""
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) c FROM books").fetchone()["c"]
    if count == 0:
        famous_books = [
            ("To Kill a Mockingbird", "Harper Lee", "9780061120084", 3),
            ("1984", "George Orwell", "9780451524935", 4),
            ("Pride and Prejudice", "Jane Austen", "9780141439518", 3),
            ("The Great Gatsby", "F. Scott Fitzgerald", "9780743273565", 3),
            ("The Hobbit", "J.R.R. Tolkien", "9780547928227", 2),
            ("Harry Potter and the Sorcerer's Stone", "J.K. Rowling", "9780590353427", 5),
            ("The Catcher in the Rye", "J.D. Salinger", "9780316769488", 2),
            ("Sapiens: A Brief History of Humankind", "Yuval Noah Harari", "9780062316097", 3),
            ("The Alchemist", "Paulo Coelho", "9780061122415", 3),
            ("A Brief History of Time", "Stephen Hawking", "9780553380163", 2),
        ]
        conn.executemany(
            "INSERT OR IGNORE INTO books (title, author, isbn, quantity, available) "
            "VALUES (?, ?, ?, ?, ?)",
            [(t, a, i, q, q) for t, a, i, q in famous_books],
        )
        conn.commit()
    conn.close()


# ---------- Home ----------
@app.route("/")
def index():
    conn = get_db()
    total_books = conn.execute("SELECT COALESCE(SUM(quantity),0) c FROM books").fetchone()["c"]
    available_books = conn.execute("SELECT COALESCE(SUM(available),0) c FROM books").fetchone()["c"]
    total_members = conn.execute("SELECT COUNT(*) c FROM members").fetchone()["c"]
    active_issues = conn.execute("SELECT COUNT(*) c FROM issues WHERE return_date IS NULL").fetchone()["c"]

    # --- Chart: most borrowed books (top 5 by number of times issued) ---
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

    # --- Chart: busiest months (issues grouped by YYYY-MM) ---
    monthly_rows = conn.execute(
        """
        SELECT strftime('%Y-%m', issue_date) AS month, COUNT(*) AS c
        FROM issues
        GROUP BY month
        ORDER BY month
        """
    ).fetchall()
    monthly_labels = [r["month"] for r in monthly_rows]
    monthly_counts = [r["c"] for r in monthly_rows]

    # --- Chart: overdue vs on-time among currently active issues ---
    today_str = datetime.today().date().isoformat()
    overdue_count = conn.execute(
        "SELECT COUNT(*) c FROM issues WHERE return_date IS NULL AND due_date < ?", (today_str,)
    ).fetchone()["c"]
    on_time_count = active_issues - overdue_count

    conn.close()
    return render_template(
        "index.html",
        total_books=total_books,
        available_books=available_books,
        total_members=total_members,
        active_issues=active_issues,
        top_books_labels=top_books_labels,
        top_books_counts=top_books_counts,
        monthly_labels=monthly_labels,
        monthly_counts=monthly_counts,
        overdue_count=overdue_count,
        on_time_count=on_time_count,
    )


# ---------- ISBN lookup (used by the barcode scanner on the Add Book form) ----------
@app.route("/api/lookup-isbn/<isbn>")
def lookup_isbn(isbn):
    import requests as pyrequests

    isbn = "".join(ch for ch in isbn if ch.isalnum())
    try:
        resp = pyrequests.get(
            f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data",
            timeout=5,
        )
        data = resp.json()
        book_data = data.get(f"ISBN:{isbn}")
        if not book_data:
            return {"found": False}
        return {
            "found": True,
            "title": book_data.get("title", ""),
            "author": ", ".join(a["name"] for a in book_data.get("authors", [])),
        }
    except Exception:
        return {"found": False, "error": "lookup_failed"}


# ---------- Books ----------
@app.route("/books")
def books():
    conn = get_db()
    search = request.args.get("q", "").strip()
    if search:
        rows = conn.execute(
            "SELECT * FROM books WHERE title LIKE ? OR author LIKE ? OR isbn LIKE ? ORDER BY title",
            (f"%{search}%", f"%{search}%", f"%{search}%"),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM books ORDER BY title").fetchall()
    conn.close()
    return render_template("books.html", books=rows, search=search)


@app.route("/books/add", methods=["GET", "POST"])
def add_book():
    if request.method == "POST":
        title = request.form["title"].strip()
        author = request.form["author"].strip()
        isbn = request.form["isbn"].strip()
        quantity = int(request.form.get("quantity", 1))

        if not title or not author:
            flash("Title and Author are required.", "error")
            return redirect(url_for("add_book"))

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO books (title, author, isbn, quantity, available) VALUES (?, ?, ?, ?, ?)",
                (title, author, isbn or None, quantity, quantity),
            )
            conn.commit()
            flash("Book added successfully.", "success")
        except sqlite3.IntegrityError:
            flash("A book with this ISBN already exists.", "error")
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
        flash("Book not found.", "error")
        return redirect(url_for("books"))

    if request.method == "POST":
        title = request.form["title"].strip()
        author = request.form["author"].strip()
        isbn = request.form["isbn"].strip()
        quantity = int(request.form.get("quantity", 1))

        issued_count = book["quantity"] - book["available"]
        new_available = max(quantity - issued_count, 0)

        conn.execute(
            "UPDATE books SET title=?, author=?, isbn=?, quantity=?, available=? WHERE id=?",
            (title, author, isbn or None, quantity, new_available, book_id),
        )
        conn.commit()
        conn.close()
        flash("Book updated successfully.", "success")
        return redirect(url_for("books"))

    conn.close()
    return render_template("book_form.html", book=book)


@app.route("/books/delete/<int:book_id>", methods=["POST"])
def delete_book(book_id):
    conn = get_db()
    active = conn.execute(
        "SELECT COUNT(*) c FROM issues WHERE book_id=? AND return_date IS NULL", (book_id,)
    ).fetchone()["c"]
    if active > 0:
        flash("Cannot delete: this book has active issues.", "error")
    else:
        conn.execute("DELETE FROM books WHERE id=?", (book_id,))
        conn.commit()
        flash("Book deleted.", "success")
    conn.close()
    return redirect(url_for("books"))


# ---------- Members ----------
@app.route("/members")
def members():
    conn = get_db()
    rows = conn.execute("SELECT * FROM members ORDER BY name").fetchall()
    conn.close()
    return render_template("members.html", members=rows)


@app.route("/members/add", methods=["GET", "POST"])
def add_member():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        phone = request.form.get("phone", "").strip()

        if not name or not email:
            flash("Name and Email are required.", "error")
            return redirect(url_for("add_member"))

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO members (name, email, phone) VALUES (?, ?, ?)",
                (name, email, phone or None),
            )
            conn.commit()
            flash("Member added successfully.", "success")
        except sqlite3.IntegrityError:
            flash("A member with this email already exists.", "error")
        finally:
            conn.close()
        return redirect(url_for("members"))

    return render_template("member_form.html")


@app.route("/members/delete/<int:member_id>", methods=["POST"])
def delete_member(member_id):
    conn = get_db()
    active = conn.execute(
        "SELECT COUNT(*) c FROM issues WHERE member_id=? AND return_date IS NULL", (member_id,)
    ).fetchone()["c"]
    if active > 0:
        flash("Cannot delete: this member has books currently issued.", "error")
    else:
        conn.execute("DELETE FROM members WHERE id=?", (member_id,))
        conn.commit()
        flash("Member deleted.", "success")
    conn.close()
    return redirect(url_for("members"))


# ---------- Issue / Return ----------
@app.route("/issues")
def issues():
    conn = get_db()
    rows = conn.execute(
        """
        SELECT issues.id, books.title AS book_title, members.name AS member_name,
               issues.issue_date, issues.due_date, issues.return_date
        FROM issues
        JOIN books ON books.id = issues.book_id
        JOIN members ON members.id = issues.member_id
        ORDER BY issues.return_date IS NOT NULL, issues.due_date
        """
    ).fetchall()
    conn.close()
    today = datetime.today().date()
    return render_template("issues.html", issues=rows, today=today)


@app.route("/issues/new", methods=["GET", "POST"])
def issue_book():
    conn = get_db()
    if request.method == "POST":
        book_id = int(request.form["book_id"])
        member_id = int(request.form["member_id"])
        days = int(request.form.get("days", 14))

        book = conn.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        if not book or book["available"] < 1:
            flash("Selected book is not available.", "error")
            conn.close()
            return redirect(url_for("issue_book"))

        issue_date = datetime.today().date()
        due_date = issue_date + timedelta(days=days)

        conn.execute(
            "INSERT INTO issues (book_id, member_id, issue_date, due_date) VALUES (?, ?, ?, ?)",
            (book_id, member_id, issue_date.isoformat(), due_date.isoformat()),
        )
        conn.execute("UPDATE books SET available = available - 1 WHERE id=?", (book_id,))
        conn.commit()
        conn.close()
        flash("Book issued successfully.", "success")
        return redirect(url_for("issues"))

    available_books = conn.execute("SELECT * FROM books WHERE available > 0 ORDER BY title").fetchall()
    all_members = conn.execute("SELECT * FROM members ORDER BY name").fetchall()
    conn.close()
    return render_template("issue_form.html", books=available_books, members=all_members)


@app.route("/issues/return/<int:issue_id>", methods=["POST"])
def return_book(issue_id):
    conn = get_db()
    record = conn.execute("SELECT * FROM issues WHERE id=?", (issue_id,)).fetchone()
    if not record or record["return_date"] is not None:
        flash("Invalid or already-returned issue record.", "error")
    else:
        today = datetime.today().date().isoformat()
        conn.execute("UPDATE issues SET return_date=? WHERE id=?", (today, issue_id))
        conn.execute("UPDATE books SET available = available + 1 WHERE id=?", (record["book_id"],))
        conn.commit()
        flash("Book marked as returned.", "success")
    conn.close()
    return redirect(url_for("issues"))


# Ensure the database/tables exist whether this module is run directly
# (python app.py) or imported by a WSGI server (gunicorn app:app).
init_db()
seed_books()

if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
