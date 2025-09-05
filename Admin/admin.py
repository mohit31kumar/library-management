# --- 1. Import Necessary Libraries ---
import pandas as pd
import mysql.connector
from flask import (
    Flask,
    request,
    send_file,
    jsonify,
    render_template,
    send_from_directory,
)
from flask_cors import CORS
from datetime import datetime
import io

# --- 2. Database Configuration ---
# IMPORTANT: Update these values with your actual database credentials.
db_config = {
    'host': 'localhost',      # Or your database server IP
    'user': 'root',           # Your database username
    'password': '',           # Your database password
    'database': 'lib_main'
}

# --- 3. Initialize the Flask Application ---
app = Flask(__name__, template_folder='.', static_folder='.')
CORS(app)  # Enable CORS to allow requests from the browser

# --- 4. Helper Function to Fetch Data from MySQL ---
def get_log_data():
    """
    Connects to the MySQL database and fetches the library logs.
    Returns a pandas DataFrame.
    """
    try:
        # Establish a connection to the database
        conn = mysql.connector.connect(**db_config)
        # SQL query to select all data from the logs table
        query = "SELECT full_reg_no, name, branch, year, entry_date, entry_time, exit_date, exit_time FROM logs"
        # Execute the query and load the result into a pandas DataFrame
        df = pd.read_sql(query, conn)
        # Convert the 'entry_date' column to datetime objects for filtering
        df['entry_date'] = pd.to_datetime(df['entry_date'])
        return df
    except mysql.connector.Error as e:
        print(f"Error connecting to MySQL or fetching data: {e}")
        # Return an empty DataFrame if the connection fails
        return pd.DataFrame()
    finally:
        # Ensure the connection is always closed
        if 'conn' in locals() and conn.is_connected():
            conn.close()

# --- 5. Helper Function to Create and Send Excel Files ---
def create_excel_response(df, filename="report.xlsx"):
    """
    Converts a pandas DataFrame to an in-memory Excel file and prepares it for download.
    """
    output = io.BytesIO()
    # The 'xlsxwriter' engine is used for creating Excel files.
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Report')
    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

# --- 6. API Endpoints for Reports and Static Files ---
@app.route('/sty.css')
def serve_css():
    return send_from_directory('.', 'sty.css')

@app.route('/scr.js')
def serve_js():
    return send_from_directory('.', 'scr.js')

@app.route('/report/custom_date_range', methods=['GET'])
def custom_date_range():
    """
    Generates a report with unique student entries for a custom date range.
    This corresponds to the 'Custom Date Report' feature in the admin panel.
    """
    log_df = get_log_data()
    if log_df.empty:
        return jsonify({"error": "Could not connect to the database or the log is empty."}), 500

    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    if not start_date_str or not end_date_str:
        return jsonify({"error": "Both 'start_date' and 'end_date' are required. Format: YYYY-MM-DD"}), 400

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    if start_date > end_date:
        return jsonify({"error": "'start_date' cannot be after 'end_date'."}), 400

    # Filter logs for the specified date range
    mask = (log_df['entry_date'].dt.date >= start_date) & (log_df['entry_date'].dt.date <= end_date)
    date_range_logs = log_df[mask]

    if date_range_logs.empty:
        return jsonify({"error": f"No entries found between {start_date_str} and {end_date_str}."}), 404
    
    # Create a summary DataFrame
    report_df = date_range_logs.copy()
    report_df['entry_date'] = report_df['entry_date'].dt.strftime('%d-%m-%Y')

    filename = f"report_{start_date_str}_to_{end_date_str}.xlsx"
    return create_excel_response(report_df, filename)


@app.route('/report/daily_summary', methods=['GET'])
def daily_summary():
    """
    Generates a complete log for a single specified day.
    Corresponds to the 'Daily Summary' feature in the admin panel.
    """
    log_df = get_log_data()
    if log_df.empty:
        return jsonify({"error": "Could not connect to the database or the log is empty."}), 500

    date_str = request.args.get('date')
    if not date_str:
        return jsonify({"error": "A 'date' parameter is required. Format: YYYY-MM-DD"}), 400

    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    # Filter logs for the target date
    daily_summary_df = log_df[log_df['entry_date'].dt.date == target_date].copy()
    if daily_summary_df.empty:
        return jsonify({"error": f"No library entries found for {date_str}."}), 404

    # Format date for the report
    daily_summary_df['entry_date'] = daily_summary_df['entry_date'].dt.strftime('%d-%m-%Y')
    filename = f"daily_summary_{date_str}.xlsx"
    return create_excel_response(daily_summary_df, filename)


@app.route('/report/full_log_dump', methods=['GET'])
def full_log_dump():
    """
    Generates a full dump of all library logs.
    Corresponds to the 'Download Excel' feature in the admin panel.
    """
    log_df = get_log_data()
    if log_df.empty:
        return jsonify({"error": "Could not connect to the database or the log is empty."}), 500

    # Sort data for readability
    full_df = log_df.sort_values(by=['entry_date', 'entry_time'], ascending=[False, False]).copy()
    full_df['entry_date'] = full_df['entry_date'].dt.strftime('%d-%m-%Y')
    
    filename = "full_library_log_dump.xlsx"
    return create_excel_response(full_df, filename)


@app.route('/')
def home():
    """
    Serves the main admin panel page.
    """
    return render_template('ind.html')

# --- 7. Run the Application ---
if __name__ == '__main__':
    # Run the Flask app, making it accessible on your local network
    app.run(debug=True, host='0.0.0.0', port=5001)

