import os
import sys
import pandas as pd
import mysql.connector as mysql
from flask import Flask, request, render_template, flash, redirect, url_for

# --- Database and Helper Functions (No changes needed here) ---

MYSQL_HOST = "localhost"
MYSQL_PORT = 3306
MYSQL_USER = "root"
MYSQL_PASSWORD = ""  # <-- Fill with your MySQL root password if set
MYSQL_DB = "lib_main"

EMAIL_DOMAIN = "@poornima.edu.in"

def is_valid_email(email: str) -> bool:
    if not isinstance(email, str) or not email:
        return False
    return email.lower().endswith(EMAIL_DOMAIN)

def safe_int(val):
    try:
        if pd.isna(val):
            return None
        return int(str(val).strip().split('.')[0])
    except Exception:
        return None

def safe_str(val):
    if pd.isna(val):
        return ""
    return str(val).strip()

def get_connection():
    try:
        conn = mysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB
        )
        conn.autocommit = True
        return conn
    except mysql.Error as e:
        print(f"[FATAL] MySQL connection failed: {e}")
        return None

def ensure_students_table(cursor):
    students_table = """
    CREATE TABLE IF NOT EXISTS Students (
        full_reg_no VARCHAR(20) PRIMARY KEY, 
        name VARCHAR(100),
        branch VARCHAR(50),
        year INT CHECK (year BETWEEN 1 AND 5),
        email VARCHAR(255) CHECK(email LIKE '%@poornima.edu.in')
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
    try:
        cursor.execute(students_table)
    except mysql.Error as e:
        print(f"[ERROR] Creating Students table: {e}")

def import_students(cursor, df):
    inserted = updated = skipped = 0
    errors = []
    insert_sql = """
    INSERT INTO Students (full_reg_no, name, branch, year, email)
    VALUES (%s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        name = VALUES(name),
        branch = VALUES(branch),
        year = VALUES(year),
        email = VALUES(email);
    """
    for idx, row in df.iterrows():
        full_reg_no = safe_str(row.get("full_reg_no"))
        name = safe_str(row.get("name"))
        branch = safe_str(row.get("branch"))
        year = safe_int(row.get("year"))
        email = safe_str(row.get("email"))

        if not full_reg_no:
            skipped += 1
            errors.append(f"Row {idx+2}: 'full_reg_no' is missing.")
            continue
        
        if year is None or not (1 <= year <= 5):
            skipped += 1
            errors.append(f"Row {idx+2}: 'year' must be between 1 and 5.")
            continue
        
        if not is_valid_email(email):
            skipped += 1
            errors.append(f"Row {idx+2}: Email must end with {EMAIL_DOMAIN}.")
            continue
        
        try:
            cursor.execute(insert_sql, (full_reg_no, name, branch, year, email))
            if cursor.rowcount == 1:
                inserted += 1
            else:
                updated += 1
        except mysql.Error as e:
            skipped += 1
            errors.append(f"Row {idx+2}: Database error -> {e}")
    
    return {"inserted": inserted, "updated": updated, "skipped": skipped, "errors": errors}

# --- Flask Application ---

# Tell Flask to look for HTML files in the current directory '.'
app = Flask(__name__, template_folder='.')
app.secret_key = "supersecretkey"
app.config['UPLOAD_FOLDER'] = 'uploads'

# Route for your home page
@app.route('/')
def home():
    return render_template('home.html')

# Route to display the import form and handle the POST request
@app.route('/import', methods=['GET', 'POST'])
def import_page():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        if file and file.filename.endswith('.xlsx'):
            # Ensure the uploads directory exists
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            
            conn = get_connection()
            if not conn:
                flash('Database connection failed.', 'danger')
                return render_template('import.html')
            
            cursor = conn.cursor()
            ensure_students_table(cursor)
            
            try:
                xl = pd.ExcelFile(filepath)
                if "students" in xl.sheet_names:
                    students_df = xl.parse("students")
                    result = import_students(cursor, students_df)
                    flash(f"Import complete! Inserted: {result['inserted']}, Updated: {result['updated']}, Skipped: {result['skipped']}", 'success')
                    if result['errors']:
                        for error in result['errors']:
                            flash(error, 'warning')
                else:
                    flash("'students' sheet not found in the Excel file.", 'danger')
            except Exception as e:
                flash(f"An error occurred: {e}", 'danger')
            finally:
                cursor.close()
                conn.close()
                os.remove(filepath) # Clean up the uploaded file
        else:
            flash('Invalid file type. Please upload a .xlsx file.', 'danger')

        return redirect(url_for('import_page'))

    # For a GET request, just display the page
    return render_template('import.html')

if __name__ == '__main__':
    app.run(debug=True)
