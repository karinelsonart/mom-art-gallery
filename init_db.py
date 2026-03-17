"""
init_db.py — Run once to create gallery.db and import existing CSV data.

Usage:
    python init_db.py
"""

import sqlite3
import csv
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE  = os.path.join(BASE_DIR, "gallery.db")
CSV_FILE = os.path.join(BASE_DIR, "assets", "gallery.csv")


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS artworks (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            filename         TEXT    NOT NULL UNIQUE,
            title            TEXT    NOT NULL,
            date             TEXT,
            description      TEXT,
            category         TEXT,
            artist_statement TEXT
        )
    """)
    conn.commit()
    print(f"Database created at {DB_FILE}")

    # Import CSV if it exists
    if not os.path.exists(CSV_FILE):
        print("No CSV found — empty database created.")
        conn.close()
        return

    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        imported = 0
        skipped  = 0
        for row in reader:
            try:
                c.execute("""
                    INSERT OR IGNORE INTO artworks
                        (filename, title, date, description, category, artist_statement)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    row.get("filename", "").strip(),
                    row.get("title", "").strip(),
                    row.get("date", "").strip(),
                    row.get("description", "").strip(),
                    row.get("category", "").strip(),
                    row.get("artist_statement", "").strip(),
                ))
                if c.rowcount:
                    imported += 1
                else:
                    skipped += 1
            except Exception as e:
                print(f"  Error importing row {row}: {e}")

    conn.commit()
    conn.close()
    print(f"Import complete: {imported} rows imported, {skipped} skipped (duplicates).")


if __name__ == "__main__":
    init_db()
