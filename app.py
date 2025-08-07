from flask import Flask, render_template, request, redirect, url_for, flash
import requests
from bs4 import BeautifulSoup
import sqlite3
import os

app = Flask(__name__)
app.secret_key = "your_secret_key"

DB_PATH = os.path.join(os.path.dirname(__file__), "court_data.db")

# Create DB table if not exists
def create_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS case_queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_type TEXT,
            case_number TEXT,
            filing_year TEXT,
            captcha_text TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            raw_response TEXT
        );
    """)
    conn.commit()
    conn.close()

# Save query to DB
def log_query(case_type, case_number, filing_year, captcha_text, raw_response):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO case_queries (case_type, case_number, filing_year, captcha_text, raw_response) VALUES (?, ?, ?, ?, ?)",
        (case_type, case_number, filing_year, captcha_text, raw_response)
    )
    conn.commit()
    conn.close()

# Simulated data fetcher
def fetch_case_data(case_type, case_number, filing_year):
    url = "https://districts.ecourts.gov.in/faridabad"  # eCourt homepage
    try:
        session = requests.Session()
        response = session.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        # Simulated data – replace with real scraping logic later
        data = {
            "parties": "John Doe vs State",
            "filing_date": "2023-02-15",
            "next_hearing": "2025-09-10",
            "pdf_link": "/static/sample_order.pdf"
        }
        log_query(case_type, case_number, filing_year, "1234", response.text)
        return data
    except Exception as e:
        return {"error": str(e)}

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        case_type = request.form.get("case_type")
        case_number = request.form.get("case_number")
        filing_year = request.form.get("filing_year")
        captcha_text = request.form.get("captcha_text")

        # CAPTCHA validation (simulated)
        if captcha_text.lower() != "51515":
            flash("Invalid CAPTCHA. Please try again.", "danger")
            return redirect(url_for("index"))

        result = fetch_case_data(case_type, case_number, filing_year)
        if "error" in result:
            flash(f"Error fetching data: {result['error']}", "danger")
            return redirect(url_for("index"))
        return render_template("result.html", result=result)

    return render_template("index.html")

if __name__ == "__main__":
    create_db()
    app.run(debug=True)
