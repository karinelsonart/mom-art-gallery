from flask import Flask, render_template, request, redirect, url_for, flash
import os
import csv
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
SITE_DIR = "/root/mom-art-gallery"
GALLERY_DIR = os.path.join(SITE_DIR, "static/gallery")
CSV_FILE = os.path.join(SITE_DIR, "assets/gallery.csv")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif"}
 
# Gmail credentials — set these as environment variables on the server, never hardcode them.
# Run once on the VM:
#   export GMAIL_USER="yourgmail@gmail.com"
#   export GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"   # 16-char Google App Password
#   export CONTACT_RECIPIENT="karinelson@gmail.com"   # where contact emails land
GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
CONTACT_RECIPIENT = os.environ.get("CONTACT_RECIPIENT", GMAIL_USER)
 
CSV_FIELDS = ["filename", "title", "date", "description", "category", "artist_statement"]
 
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "change-me-in-production")
 
 
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
 
 
def load_artworks():
    if not os.path.exists(CSV_FILE):
        return []
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        artworks = []
        for row in reader:
            # Back-fill artist_statement for rows that predate the column
            if "artist_statement" not in row:
                row["artist_statement"] = ""
            artworks.append(row)
    return artworks
 
 
def save_artworks(artworks):
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(artworks)
 
 
def rebuild_site():
    try:
        subprocess.run(
            ["hugo", "-s", SITE_DIR, "-d", os.path.join(SITE_DIR, "public")],
            check=True,
        )
        print("Hugo site rebuilt successfully.")
    except subprocess.CalledProcessError as e:
        print("Error rebuilding Hugo site:", e)
 
 
def send_contact_email(sender_name, sender_email, message_body):
    """Send a contact form submission to CONTACT_RECIPIENT via Gmail SMTP."""
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        raise RuntimeError(
            "Gmail credentials not set. Export GMAIL_USER and GMAIL_APP_PASSWORD."
        )
 
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"New message from {sender_name} — Kari Nelson Art"
    msg["From"] = GMAIL_USER
    msg["To"] = CONTACT_RECIPIENT
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
    """Pull artwork fields out of a POST request, merging onto an existing dict."""
    base = existing or {}
    base["title"] = request.form.get("title", "").strip()
    base["date"] = request.form.get("date", "").strip() or datetime.now().strftime("%Y-%m-%d")
    base["description"] = request.form.get("description", "").strip()
    base["category"] = request.form.get("category", "").strip()
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
 
        ext = file.filename.rsplit(".", 1)[1].lower()
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.{ext}"
        file.save(os.path.join(GALLERY_DIR, filename))
 
        artwork = artwork_from_form()
        artwork["filename"] = filename
 
        artworks = load_artworks()
        artworks.append(artwork)
        save_artworks(artworks)
 
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
    artworks = load_artworks()
    row = next((r for r in artworks if r["filename"] == filename), None)
    if not row:
        flash("Artwork not found.")
        return redirect(url_for("gallery"))
 
    if request.method == "POST":
        artwork_from_form(existing=row)  # mutates row in-place
 
        # Optional image replacement
        file = request.files.get("image")
        if file and allowed_file(file.filename):
            old_path = os.path.join(GALLERY_DIR, row["filename"])
            if os.path.exists(old_path):
                os.remove(old_path)
            ext = file.filename.rsplit(".", 1)[1].lower()
            new_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.{ext}"
            file.save(os.path.join(GALLERY_DIR, new_filename))
            row["filename"] = new_filename
 
        save_artworks(artworks)
        rebuild_site()
        flash("Artwork updated!")
        return redirect(url_for("gallery"))
 
    return render_template("edit.html", artwork=row)
 
 
@app.route("/delete/<filename>", methods=["POST"])
def delete(filename):
    artworks = load_artworks()
    row = next((r for r in artworks if r["filename"] == filename), None)
    if not row:
        flash("Artwork not found.")
        return redirect(url_for("gallery"))
 
    img_path = os.path.join(GALLERY_DIR, filename)
    if os.path.exists(img_path):
        os.remove(img_path)
 
    artworks = [r for r in artworks if r["filename"] != filename]
    save_artworks(artworks)
    rebuild_site()
    flash("Artwork deleted.")
    return redirect(url_for("gallery"))
 
 
# ---------------------------------------------------------------------------
# Public contact form endpoint
# ---------------------------------------------------------------------------
@app.route("/contact-submit", methods=["POST"])
def contact_submit():
    """
    The Hugo contact form POSTs here.
    Make sure Caddy proxies /contact-submit → http://localhost:5000/contact-submit
    """
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    message = request.form.get("message", "").strip()
 
    if not name or not email or not message:
        # Redirect back to contact page with a query param the page can read
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
 
