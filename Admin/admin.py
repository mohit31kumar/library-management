import os
import io
import pandas as pd
import mysql.connector 
from flask import Response
from datetime import date, datetime
from flask import Flask, render_template, jsonify, send_file, request
from werkzeug.utils import secure_filename


# Flask app setup
app = Flask(__name__)

# Load DB config from environment variables for security
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASS", ""),
    "database": os.getenv("DB_NAME", "lib_main")
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

# Folder to save uploaded files temporarily
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"xlsx"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return render_template("ind.html")

# ---------------------- APIs ----------------------

@app.route("/api/live_stats")
def live_stats():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    
    # Users currently inside
    cur.execute("SELECT COUNT(*) AS inside FROM logs WHERE exit_time IS NULL")
    inside = cur.fetchone()["inside"]

    # Today's entries
    cur.execute("SELECT COUNT(*) AS today_entries FROM logs WHERE entry_date = CURDATE()")
    today_entries = cur.fetchone()["today_entries"]

    cur.close()
    conn.close()
    return jsonify({"inside": inside, "today_entries": today_entries})

# ------------------- Active Users -------------------
@app.route('/api/active_users', methods=['GET'])
def active_users():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
            SELECT l.full_reg_no, l.name, l.branch, l.year, l.role, l.entry_time, f.email
            FROM logs l
            LEFT JOIN faculty f ON RIGHT(l.full_reg_no, 4) = f.full_reg_no
            WHERE l.exit_time IS NULL
            ORDER BY l.entry_time DESC
        """
        cursor.execute(query)
        results = cursor.fetchall()

        # Convert datetime to string
        for row in results:
            if row.get("entry_time"):
                row["entry_time"] = str(row["entry_time"])
            if row.get("exit_time"):
                row["exit_time"] = str(row["exit_time"])

        return jsonify(results)
    except Exception as e:
        print("Error fetching active users:", e)
        return jsonify({"error": "Server error"}), 500
    finally:
        cursor.close()
        conn.close()



@app.route("/api/peak_hours_week")
def peak_hours_week():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Last 7 days (weekly)
    query = """
        SELECT HOUR(entry_time) AS hour, COUNT(*) AS entries
        FROM logs
        WHERE entry_date >= CURDATE() - INTERVAL 7 DAY
        GROUP BY HOUR(entry_time)
        ORDER BY hour;
    """
    cursor.execute(query)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    # Format for Chart.js
    data = []
    for row in rows:
        data.append({
            "hour": f"{row['hour']:02d}:00",   # format 2-digit hour
            "entries": row["entries"]
        })

    return jsonify(data)

# Daily, Weekly, Monthly entries APIs
@app.route("/api/daily_entries")
def daily_entries():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT entry_date, COUNT(*) AS entries
        FROM logs 
        WHERE entry_date IS NOT NULL
        GROUP BY entry_date 
        ORDER BY entry_date DESC LIMIT 7
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    # rows are dicts with 'entry_date' and 'entries'. Reverse for chronological
    out = [{"date": r["entry_date"].strftime("%Y-%m-%d") if isinstance(r["entry_date"], (datetime,)) else str(r["entry_date"]),
            "entries": r["entries"]} for r in rows][::-1]
    return jsonify(out)


@app.route("/api/weekly_entries")
def weekly_entries():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT WEEK(entry_date) AS week, COUNT(*) 
        FROM logs 
        WHERE entry_date IS NOT NULL
        GROUP BY week 
        ORDER BY week DESC LIMIT 4
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{"week": str(r[0]), "entries": r[1]} for r in rows][::-1])

@app.route("/api/monthly_entries")
def monthly_entries():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT DATE_FORMAT(entry_date, '%Y-%m') AS month, COUNT(*) 
        FROM logs 
        WHERE entry_date IS NOT NULL
        GROUP BY month 
        ORDER BY month DESC LIMIT 12
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{"month": r[0], "entries": r[1]} for r in rows][::-1])

# User history by reg_no 
@app.route('/api/user_history/<reg_no>', methods=['GET'])
def user_history(reg_no):
    reg_no = reg_no.strip()

    if not reg_no.isdigit():
        return jsonify({"error": "Invalid registration number"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT *
        FROM logs
        WHERE (role='Student' AND RIGHT(full_reg_no, 5) = %s)
           OR (role='Faculty' AND RIGHT(full_reg_no, 4) = %s)
        ORDER BY entry_date DESC, entry_time DESC
    """
    cursor.execute(query, (reg_no, reg_no))
    results = cursor.fetchall()

    # Convert dates/times to strings
    for row in results:
        for key in ['entry_date', 'exit_date', 'entry_time', 'exit_time']:
            if row[key]:
                row[key] = str(row[key])

    cursor.close()
    conn.close()
    return jsonify(results)




@app.route('/export/daily', methods=['GET'])
def export_daily_logs():
    date_str = request.args.get('date') or date.today().strftime("%Y-%m-%d")

    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT full_reg_no, name, branch, year, email, entry_date, entry_time, exit_date, exit_time, role
        FROM logs
        WHERE entry_date = %s
        ORDER BY entry_time DESC
    """
    cursor.execute(query, (date_str,))
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    if not rows:
        return jsonify({"error": f"No logs found for {date_str}"}), 404

    # Convert datetime/time to string
    for r in rows:
        for key in ['entry_date', 'entry_time', 'exit_date', 'exit_time']:
            if r.get(key):
                r[key] = str(r[key])

    df = pd.DataFrame(rows)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Daily Logs')
    output.seek(0)

    filename = f"daily_logs_{date_str}.xlsx"
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@app.route('/export/range', methods=['GET'])
def export_range_logs():
    start_date = request.args.get("start")
    end_date = request.args.get("end")

    if not start_date or not end_date:
        return jsonify({"error": "Both start and end dates are required (YYYY-MM-DD)."}), 400

    try:
        s = datetime.strptime(start_date, "%Y-%m-%d").date()
        e = datetime.strptime(end_date, "%Y-%m-%d").date()
    except Exception:
        return jsonify({"error": "Dates must be in YYYY-MM-DD format."}), 400

    if s > e:
        return jsonify({"error": "start date must be <= end date"}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT full_reg_no, name, branch, year, email, entry_date, entry_time, exit_date, exit_time, role
        FROM logs
        WHERE entry_date BETWEEN %s AND %s
        ORDER BY entry_date DESC, entry_time DESC
    """
    cursor.execute(query, (start_date, end_date))
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    if not rows:
        return jsonify({"error": f"No logs found between {start_date} and {end_date}"}), 404

    for r in rows:
        for key in ['entry_date', 'entry_time', 'exit_date', 'exit_time']:
            if r.get(key):
                r[key] = str(r[key])

    df = pd.DataFrame(rows)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Logs')
    output.seek(0)

    filename = f"logs_{start_date}_to_{end_date}.xlsx"
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


# ------------------- Import Students -------------------
@app.route("/import/students", methods=["POST"])
def import_students():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files['file']
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    try:
        df = pd.read_excel(file)
        required_cols = ['full_reg_no', 'name', 'branch', 'year']
        if not all(col in df.columns for col in required_cols):
            return jsonify({"error": f"Required columns: {required_cols}"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        inserted = 0
        for _, row in df.iterrows():
            try:
                cursor.execute("""
                    INSERT INTO students (full_reg_no, name, branch, year)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE name=%s, branch=%s, year=%s
                """, (row['full_reg_no'], row['name'], row['branch'], row['year'],
                      row['name'], row['branch'], row['year']))
                inserted += 1
            except Exception as e:
                print(f"Skipping row due to error: {e}")
        conn.commit()
        return jsonify({"success": f"{inserted} students added/updated successfully"})
    except Exception as e:
        print("Error importing students:", e)
        return jsonify({"error": "Failed to import students"}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

# ------------------- Import Faculties -------------------
@app.route("/import/faculties", methods=["POST"])
def import_faculties():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files['file']
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    try:
        df = pd.read_excel(file)
        required_cols = ['full_reg_no', 'name', 'email']
        if not all(col in df.columns for col in required_cols):
            return jsonify({"error": f"Required columns: {required_cols}"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        inserted = 0
        for _, row in df.iterrows():
            try:
                cursor.execute("""
                    INSERT INTO faculty (full_reg_no, name, email)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE name=%s, email=%s
                """, (row['full_reg_no'], row['name'], row['email'],
                      row['name'], row['email']))
                inserted += 1
            except Exception as e:
                print(f"Skipping row due to error: {e}")
        conn.commit()
        return jsonify({"success": f"{inserted} faculties added/updated successfully"})
    except Exception as e:
        print("Error importing faculties:", e)
        return jsonify({"error": "Failed to import faculties"}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5001)
