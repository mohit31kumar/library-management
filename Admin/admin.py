from flask import Flask, render_template, jsonify, send_file, Response, make_response
import mysql.connector
from datetime import date, datetime
import csv
import io
import pandas as pd
from flask import send_file, Response


app = Flask(__name__)

# Database config
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "lib_main"
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

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

@app.route("/api/active_users")
def active_users():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT full_reg_no, name, branch, year, role, entry_date, entry_time FROM logs WHERE exit_time IS NULL")
    users = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify(users)

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

@app.route("/api/daily_entries")
def daily_entries():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT entry_date, COUNT(*) 
        FROM logs 
        WHERE entry_date IS NOT NULL
        GROUP BY entry_date 
        ORDER BY entry_date DESC LIMIT 7
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{"date": str(r[0]), "entries": r[1]} for r in rows][::-1])

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


@app.route('/api/user_history/<reg_no>', methods=['GET'])
def user_history(reg_no):
    reg_no = reg_no.strip()

    # Validate 5-digit registration number
    if not reg_no.isdigit() or len(reg_no) != 5:
        return jsonify({"error": "Invalid 5-digit registration number"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT full_reg_no, name, branch, year, role, 
                   entry_date, entry_time, exit_time
            FROM logs
            WHERE full_reg_no LIKE %s
            ORDER BY entry_date DESC, entry_time DESC
        """
        cursor.execute(query, ('%/' + reg_no,))
        results = cursor.fetchall()

        # Convert datetime / timedelta to string
        for row in results:
            for key in ['entry_date', 'entry_time', 'exit_time']:
                if row[key] is not None:
                    row[key] = str(row[key])

        print(f"User {reg_no} history fetched:", results)

    except Exception as e:
        print("Error fetching user history:", e)
        return jsonify({"error": "Server error. Please try again later."}), 500

    finally:
        cursor.close()
        conn.close()

    return jsonify(results if results else [])



@app.route('/export/csv', methods=['GET'])
def export_csv():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM logs")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        return "No data to export", 400

    # Convert entry_time and exit_time to string
    for row in rows:
        if row.get('entry_time'):
            row['entry_time'] = str(row['entry_time'])
        if row.get('exit_time'):
            row['exit_time'] = str(row['exit_time'])

    df = pd.DataFrame(rows)
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=logs.csv"}
    )

@app.route('/export/excel', methods=['GET'])
def export_excel():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM logs")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    if not rows:
        return "No data to export", 400

    # Convert entry_time and exit_time to string
    for row in rows:
        if row.get('entry_time'):
            row['entry_time'] = str(row['entry_time'])
        if row.get('exit_time'):
            row['exit_time'] = str(row['exit_time'])

    df = pd.DataFrame(rows)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Logs')
    output.seek(0)

    return send_file(
        output,
        download_name="logs.xlsx",
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )





if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5001)
