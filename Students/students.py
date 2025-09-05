import apscheduler
from flask import Flask, render_template, request, redirect, url_for, flash, get_flashed_messages, send_from_directory, jsonify
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import mysql.connector
import pytz
import atexit
import traceback

app = Flask(__name__, static_folder='.', template_folder='.')
app.secret_key = 'your_secret_key'
app.config['DEBUG'] = True  # Enable debug mode

IST = pytz.timezone('Asia/Kolkata')

# --- DATABASE CONNECTION ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',  # Add your MySQL password here
    'database': 'lib_main'
}

def get_db_connection():
    """Get database connection with error handling"""
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return None

def execute_query(query, params=None, fetch=False, fetch_one=False):
    """Execute query with proper error handling"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(query, params or ())
        
        if fetch_one:
            result = cursor.fetchone()
        elif fetch:
            result = cursor.fetchall()
        else:
            conn.commit()
            result = cursor.rowcount
            
        cursor.close()
        conn.close()
        return result
    except mysql.connector.Error as err:
        print(f"Query execution error: {err}")
        if conn:
            conn.close()
        return None

# --- USER FINDER FUNCTIONS ---
def find_student(registry_code):
    """Find student by last digits of registration number"""
    query = "SELECT * FROM students WHERE full_reg_no LIKE %s"
    return execute_query(query, (f'%{registry_code}',), fetch_one=True)

def find_faculty(registry_code):
    """Find faculty by exact registration number"""
    try:
        query = "SELECT * FROM faculty WHERE full_reg_no = %s"
        return execute_query(query, (int(registry_code),), fetch_one=True)
    except ValueError:
        return None

def find_user_and_validate(registry_code, role):
    """Find user and validate input"""
    if not registry_code or not role:
        return None, "Please enter registration code and select role."
    
    registry_code = registry_code.strip()
    
    if role == 'Student':
        if not registry_code.isdigit() or len(registry_code) != 5:
            return None, "Enter a valid 5-digit code for Student."
        user = find_student(registry_code)
    elif role == 'Faculty':
        if not registry_code.isdigit() or len(registry_code) != 4:
            return None, "Enter a valid 4-digit code for Faculty."
        user = find_faculty(registry_code)
    else:
        return None, "Invalid role selected."
    
    if not user:
        return None, f"No {role} found with that code."
    
    return user, None

# --- LOG FUNCTIONS ---
def get_open_log(full_reg_no):
    """Check if user has an open log (currently inside)"""
    query = """SELECT * FROM logs 
               WHERE full_reg_no = %s AND (exit_date IS NULL OR exit_date = '')"""
    return execute_query(query, (str(full_reg_no),), fetch_one=True)

def get_users_inside():
    """Get all users currently inside the library"""
    query = """SELECT full_reg_no, name FROM logs 
               WHERE exit_date IS NULL OR exit_date = ''"""
    result = execute_query(query, fetch=True)
    return result or []

def create_entry_log(user, role, reason):
    """Create new entry log"""
    now = datetime.now(IST)
    query = """INSERT INTO logs 
               (full_reg_no, name, branch, year,  entry_date, entry_time, role, reason) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
    
    values = (
        str(user['full_reg_no']),
        user['name'],
        user.get('branch', 'N/A'),
        str(user.get('year', 'N/A')),
        now.date(),
        now.time(),
        role,
        reason
    )
    
    return execute_query(query, values)

def update_exit_log(full_reg_no):
    """Update log with exit time"""
    now = datetime.now(IST)
    query = """UPDATE logs 
               SET exit_date = %s, exit_time = %s 
               WHERE full_reg_no = %s AND (exit_date IS NULL OR exit_date = '')"""
    
    return execute_query(query, (now.date(), now.time(), str(full_reg_no)))

def check_password(user_id, password):
    """Check login credentials"""
    query = "SELECT * FROM password WHERE id = %s AND pass = %s"
    result = execute_query(query, (user_id, password), fetch_one=True)
    return bool(result)

def get_live_stats():
    today = datetime.now(IST).date()

    total_entries_query = "SELECT COUNT(*) as count FROM logs WHERE entry_date = %s"
    total_entries_result = execute_query(total_entries_query, (today,), fetch_one=True)
    total_entries_today = total_entries_result['count'] if total_entries_result else 0
    print("total_entries_result:", total_entries_result)

    unique_visitors_query = "SELECT COUNT(DISTINCT full_reg_no) as count FROM logs WHERE entry_date = %s"
    unique_visitors_result = execute_query(unique_visitors_query, (today,), fetch_one=True)
    unique_visitors_today = unique_visitors_result['count'] if unique_visitors_result else 0
    print("unique_visitors_result:", unique_visitors_result)

    inside_query = "SELECT COUNT(*) as count FROM logs WHERE exit_date IS NULL OR exit_date = ''"
    inside_result = execute_query(inside_query, fetch_one=True)
    currently_inside = inside_result['count'] if inside_result else 0
    print("inside_result:", inside_result)

    peak_hour_query = """SELECT HOUR(entry_time) as hour, COUNT(log_id) as count
                         FROM logs WHERE entry_date = %s
                         GROUP BY HOUR(entry_time) ORDER BY count DESC, hour DESC LIMIT 1"""
    peak_hour_result = execute_query(peak_hour_query, (today,), fetch_one=True)
    print("peak_hour_result:", peak_hour_result)
    peak_hour_str = "N/A"
    if peak_hour_result and peak_hour_result['hour'] is not None:
        hour = int(peak_hour_result['hour'])
        if hour == 0:
            peak_hour_str = "12 AM"
        elif hour < 12:
            peak_hour_str = f"{hour} AM"
        elif hour == 12:
            peak_hour_str = "12 PM"
        else:
            peak_hour_str = f"{hour - 12} PM"

    return {
        "total_entries_today": total_entries_today,
        "unique_visitors_today": unique_visitors_today,
        "currently_inside": currently_inside,
        "peak_hour_today": peak_hour_str
    }

# --- AUTO EXIT SCHEDULER ---
def auto_exit_users():
    """Automatically log out users still inside at 16:30 IST"""
    try:
        now = datetime.now(IST)
        query = """UPDATE logs 
                   SET exit_date = %s, exit_time = %s 
                   WHERE exit_date IS NULL OR exit_date = ''"""
        
        count = execute_query(query, (now.date(), now.time()))
        if count and count > 0:
            print(f"[AUTO-EXIT] {count} users exited automatically at 16:30 IST.")
        else:
            print("[AUTO-EXIT] No open logs found at 16:30 IST.")
    except Exception as e:
        print(f"[AUTO-EXIT ERROR] {e}")

# Run startup cleanup    
def run_startup_cleanup():
    """Cleanup leftover logs from previous days or after auto-exit cutoff."""
    try:
        now = datetime.now(IST)
        today = now.date()
        
        # Check if there are any open logs from before today
        query = """SELECT COUNT(*) as count FROM logs 
                   WHERE (exit_date IS NULL OR exit_date = '') 
                   AND entry_date < %s"""
        old_open_logs = execute_query(query, (today,), fetch_one=True)

        if old_open_logs and old_open_logs['count'] > 0:
            print("[STARTUP CLEANUP] Found old open logs from previous days. Running auto-exit...")
            auto_exit_users()
        else:
            print("[STARTUP CLEANUP] No old logs found. Skipping cleanup.")
    except Exception as e:
        print(f"[STARTUP CLEANUP ERROR] {e}")

# Initialize scheduler
try:
    scheduler = BackgroundScheduler(timezone=IST)
    scheduler.add_job(auto_exit_users, trigger='cron', hour=16, minute=30, id='auto_exit_job')
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())
except Exception as e:
    print(f"Scheduler initialization error: {e}")

# --- ROUTES ---
@app.route('/')
def index():
    """Main page showing current users and entry form"""
    try:
        users_inside = get_users_inside()
        messages = get_flashed_messages(with_categories=True)
        toast_message, toast_type = ('', 'info')
        if messages:
            toast_type, toast_message = messages[0]
        
        return render_template('index.html', 
                             toast_message=toast_message, 
                             toast_type=toast_type, 
                             users_inside=users_inside)
    except Exception as e:
        print(f"Index route error: {e}")
        return f"<h1>Error loading page</h1><p>{str(e)}</p><p>Check terminal for details.</p>"


@app.route('/check', methods=['POST'])
def check_user():
    try:
        registry_code = request.form.get('registry_last_digits', '').strip()
        role = request.form.get('role', '').strip()
        # Reason is optional on exit, get if present
        reason = request.form.get('reason', 'Self Study').strip()

        if not role:
            flash("Please select a role.", "error")
            return redirect(url_for('index'))

        # Validate user exists
        user, error = find_user_and_validate(registry_code, role)
        if error:
            flash(error, "error")
            return redirect(url_for('index'))

        now = datetime.now(IST)

        # Check if user currently inside (open log)
        open_log = get_open_log(user['full_reg_no'])

        if open_log:
            # User inside → handle exit
            if open_log['role'] != role:
                flash(f"Exit denied. You entered as {open_log['role']} and must exit with the same role.", "error")
                return redirect(url_for('index'))

            update_exit_log(user['full_reg_no'])
            flash(f"Goodbye! {user['name']} exited the library.", "success")
            return redirect(url_for('index'))
        else:
            # User not inside → handle entry

            # Check library timing
            # if now.hour < 7 or now.hour >= 20:
            #     flash("Library closed. Hours: 7 AM - 8 PM", "error")
            #     return redirect(url_for('index'))

            create_entry_log(user, role, reason)
            flash(f"Welcome! {user['name']} entered the library.", "success")
            return redirect(url_for('index'))

    except Exception as e:
        print(f"Error in /check route: {e}")
        traceback.print_exc()
        flash("An unexpected error occurred. Please try again.", "error")
        return redirect(url_for('index'))


@app.route('/check-status', methods=['POST'])
def check_status():
    registry_code = request.form.get('registry_last_digits', '').strip()
    role = request.form.get('role', '').strip()

    if not role:
        return jsonify({"success": False, "error": "Please select a role."})

    user, error = find_user_and_validate(registry_code, role)
    if error:
        return jsonify({"success": False, "error": error})

    open_log = get_open_log(user['full_reg_no'])
    return jsonify({
        "success": True,
        "user_name": user['name'],
        "user_inside": bool(open_log)
    })


@app.route('/entry', methods=['POST'])
def handle_entry():
    """Handle library entry (when user is outside)"""
    try:
        registry_code = request.form.get('registry_last_digits', '').strip()
        role = request.form.get('role', '').strip()
        reason = request.form.get('reason', 'Self Study').strip()

        if not role:
            flash("Please select a role.", "error")
            return redirect(url_for('index'))

        # Find and validate user
        user, error = find_user_and_validate(registry_code, role)
        if error:
            flash(error, "error")
            return redirect(url_for('index'))

        # Check library hours
        now = datetime.now(IST)
        if now.hour < 7 or now.hour >= 20:
            flash("Library closed. Hours: 7 AM - 8 PM", "error")
            return redirect(url_for('index'))

        # Check if user is already inside
        open_log = get_open_log(user['full_reg_no'])
        if open_log:
            flash(f"Error: {user['name']} is already inside the library.", "error")
            return redirect(url_for('index'))

        # Create entry log
        result = create_entry_log(user, role, reason)
        if result:
            flash(f"Welcome! {user['name']} entered the library.", "success")
        else:
            flash("Error logging entry. Please try again.", "error")

        return redirect(url_for('index'))
        
    except Exception as e:
        print(f"Entry error: {e}")
        print(traceback.format_exc())
        flash("System error during entry. Please try again.", "error")
        return redirect(url_for('index'))

@app.route('/exit', methods=['POST'])
def handle_exit():
    """Handle library exit (when user is inside)"""
    try:
        registry_code = request.form.get('registry_last_digits', '').strip()
        role = request.form.get('role', '').strip()

        if not role:
            flash("Please select a role.", "error")
            return redirect(url_for('index'))

        # Find and validate user
        user, error = find_user_and_validate(registry_code, role)
        if error:
            flash(error, "error")
            return redirect(url_for('index'))

        # Find open log
        open_log = get_open_log(user['full_reg_no'])
        if not open_log:
            flash(f"Error: {user['name']} is not currently inside the library.", "error")
            return redirect(url_for('index'))

        # Check role consistency
        if open_log['role'] != role:
            flash(f"Exit denied. Entered as {open_log['role']}, must exit with same role.", "error")
            return redirect(url_for('index'))

        # Update exit log
        result = update_exit_log(user['full_reg_no'])
        if result:
            flash(f"Goodbye! {user['name']} exited the library.", "success")
        else:
            flash("Error logging exit. Please try again.", "error")

        return redirect(url_for('index'))
        
    except Exception as e:
        print(f"Exit error: {e}")
        print(traceback.format_exc())
        flash("System error during exit. Please try again.", "error")
        return redirect(url_for('index'))



@app.route("/login", methods=["POST"])
def login():
    """Login API for overlay"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False})
            
        student_id = str(data.get("id", "")).strip().lower()
        password = str(data.get("pass", "")).strip()

        if check_password(student_id, password):
            return jsonify({"success": True})
        return jsonify({"success": False})
        
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({"success": False})
    



@app.route('/api/stats', methods=['GET'])
def api_stats():
    """Return live stats for dashboard AJAX"""
    try:
        stats = get_live_stats()
        return jsonify(stats)
    except Exception as e:
        print(f"/api/stats error: {e}")
        return jsonify({
            "total_entries_today": 0,
            "unique_visitors_today": 0,
            "currently_inside": 0,
            "peak_hour_today": "N/A",
            "error": str(e)
        }), 500

@app.route('/startup-cleanup')
def startup_cleanup_route():
    """Route to trigger startup cleanup manually."""
    try:
        run_startup_cleanup()
        return "<h1>Startup cleanup completed.</h1>"
    except Exception as e:
        return f"<h1>Error during cleanup:</h1><p>{str(e)}</p>", 500


# --- STATIC FILES ---


@app.route('/logo.png')
def serve_logo(): 
    return send_from_directory('.', 'logo.png')

@app.route('/background.png')
def serve_background(): 
    return send_from_directory('.', 'background.png')

@app.route('/script.js')
def serve_js(): 
    return send_from_directory('.', 'script.js')

@app.route('/style.css')
def serve_css(): 
    return send_from_directory('.', 'style.css')


# --- ERROR HANDLERS ---
@app.errorhandler(500)
def internal_error(error):
    return f"""
    <h1>Internal Server Error</h1>
    <p>Something went wrong. Check the terminal for error details.</p>
    <p>Error: {str(error)}</p>
    <a href="/">Go back to homepage</a>
    """, 500

@app.errorhandler(404)
def not_found(error):
    return f"""
    <h1>Page Not Found</h1>
    <p>The requested page could not be found.</p>
    <a href="/">Go back to homepage</a>
    """, 404

# --- TEST ROUTE ---

@app.route('/test')
def test():
    return "<h1>✅ Test route is working!</h1>"

if __name__ == '__main__':
    print("Starting Library Management System...")
    print("Visit: http://localhost:5000")
    print("Test DB: http://localhost:5000/test")
    app.run(debug=True, host='0.0.0.0', port=5000)
