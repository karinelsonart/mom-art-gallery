from flask import Flask, render_template, request, redirect, url_for, flash
import os
import csv
import sqlite3
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import uuid
import subprocess

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
GALLERY_DIR = os.path.join(BASE_DIR, "static", "gallery")
DB_FILE     = os.path.join(BASE_DIR, "gallery.db")

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif"}

# Gmail credentials — set as environment variables on the server, never hardcode.
#   export GMAIL_USER="yourgmail@gmail.com"
#   export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
#   export CONTACT_RECIPIENT="karinelson@gmail.com"
GMAIL_USER        = os.environ.get("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
CONTACT_RECIPIENT  = os.environ.get("CONTACT_RECIPIENT", GMAIL_USER)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "change-me-in-production")


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------
def export_csv():
    """Re-export the database to gallery.csv so Hugo can rebuild."""
    csv_file = os.path.join(BASE_DIR, "assets", "gallery.csv")
    artworks = load_artworks()
    fields = ["filename", "title", "date", "description", "category", "artist_statement"]
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(artworks)



def get_db():
    """Open a database connection with row_factory so rows act like dicts."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def load_artworks():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM artworks ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


def get_artwork(filename):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM artworks WHERE filename = ?", (filename,)
        ).fetchone()
    return dict(row) if row else None


def insert_artwork(artwork):
    with get_db() as conn:
        conn.execute("""
            INSERT INTO artworks (filename, title, date, description, category, artist_statement)
            VALUES (:filename, :title, :date, :description, :category, :artist_statement)
        """, artwork)
        conn.commit()


def update_artwork(artwork):
    with get_db() as conn:
        conn.execute("""
            UPDATE artworks
               SET filename         = :filename,
                   title            = :title,
                   date             = :date,
                   description      = :description,
                   category         = :category,
                   artist_statement = :artist_statement
             WHERE filename = :original_filename
        """, artwork)
        conn.commit()


def delete_artwork(filename):
    with get_db() as conn:
        conn.execute("DELETE FROM artworks WHERE filename = ?", (filename,))
        conn.commit()


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def rebuild_site():
    try:
        subprocess.run(
            ["/usr/bin/hugo", "-s", BASE_DIR, "-d", "/var/www/html", "--cleanDestinationDir"],
            check=True,
        )
        print("Hugo site rebuilt successfully.")
    except subprocess.CalledProcessError as e:
        print("Error rebuilding Hugo site:", e)


def send_contact_email(sender_name, sender_email, message_body):
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        raise RuntimeError(
            "Gmail credentials not set. Export GMAIL_USER and GMAIL_APP_PASSWORD."
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"]  = f"New message from {sender_name} — Kari Nelson Art"
    msg["From"]     = GMAIL_USER
    msg["To"]       = CONTACT_RECIPIENT
    msg["Reply-To"] = sender_email

    plain = (
        f"Name:    {sender_name}\n"
        f"Email:   {sender_email}\n\n"
        f"Message:\n{message_body}"
    )
    html = f"""
    <html><body>
      <h2>New contact form submission</h2>
      <p><strong>Name:</strong> {sender_name}</p>
      <p><strong>Email:</strong> <a href="mailto:{sender_email}">{sender_email}</a></p>
      <hr>
      <p>{message_body.replace(chr(10), '<br>')}</p>
    </body></html>
    """
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    context = ssl.create_default_context()
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.ehlo()
        server.starttls(context=context)
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, CONTACT_RECIPIENT, msg.as_string())


def artwork_from_form(existing=None):
    """Pull artwork fields out of a POST request."""
    base = existing or {}
    base["title"]            = request.form.get("title", "").strip()
    base["date"]             = request.form.get("date", "").strip() or datetime.now().strftime("%Y")
    base["description"]      = request.form.get("description", "").strip()
    base["category"]         = request.form.get("category", "").strip()
    base["artist_statement"] = request.form.get("artist_statement", "").strip()
    return base


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        file = request.files.get("image")
        if not file or not allowed_file(file.filename):
            flash("Please upload a valid image file (jpg, jpeg, png, gif).")
            return redirect(request.url)

        title = request.form.get("title", "").strip()
        if not title:
            flash("Title is required.")
            return redirect(request.url)

        ext      = file.filename.rsplit(".", 1)[1].lower()
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.{ext}"
        file.save(os.path.join(GALLERY_DIR, filename))

        artwork = artwork_from_form()
        artwork["filename"] = filename
        insert_artwork(artwork)

        export_csv()
        rebuild_site()
        flash("Artwork uploaded successfully!")
        return redirect(request.url)

    return render_template("upload.html")


@app.route("/gallery")
def gallery():
    artworks = load_artworks()
    return render_template("gallery.html", artworks=artworks)


@app.route("/edit/<filename>", methods=["GET", "POST"])
def edit(filename):
    artwork = get_artwork(filename)
    if not artwork:
        flash("Artwork not found.")
        return redirect(url_for("gallery"))

    if request.method == "POST":
        original_filename = artwork["filename"]
        artwork_from_form(existing=artwork)  # mutates artwork in-place

        # Optional image replacement
        file = request.files.get("image")
        if file and allowed_file(file.filename):
            old_path = os.path.join(GALLERY_DIR, original_filename)
            if os.path.exists(old_path):
                os.remove(old_path)
            ext          = file.filename.rsplit(".", 1)[1].lower()
            new_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.{ext}"
            file.save(os.path.join(GALLERY_DIR, new_filename))
            artwork["filename"] = new_filename

        artwork["original_filename"] = original_filename
        update_artwork(artwork)

        export_csv()
        rebuild_site()
        flash("Artwork updated!")
        return redirect(url_for("gallery"))

    return render_template("edit.html", artwork=artwork)


@app.route("/delete/<filename>", methods=["POST"])
def delete(filename):
    artwork = get_artwork(filename)
    if not artwork:
        flash("Artwork not found.")
        return redirect(url_for("gallery"))

    img_path = os.path.join(GALLERY_DIR, filename)
    if os.path.exists(img_path):
        os.remove(img_path)

    delete_artwork(filename)
    export_csv()
    rebuild_site()
    flash("Artwork deleted.")
    return redirect(url_for("gallery"))


# ---------------------------------------------------------------------------
# Public contact form endpoint
# ---------------------------------------------------------------------------
@app.route("/contact-submit", methods=["POST"])
def contact_submit():
    name    = request.form.get("name", "").strip()
    email   = request.form.get("email", "").strip()
    message = request.form.get("message", "").strip()

    if not name or not email or not message:
        return redirect("/contact/?error=missing-fields")

    try:
        send_contact_email(name, email, message)
        return redirect("/thank-you/")
    except Exception as e:
        print("Contact email error:", e)
        return redirect("/contact/?error=send-failed")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
