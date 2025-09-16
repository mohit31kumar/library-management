

import os
import shutil
import subprocess
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, flash, Response
import mysql.connector

# MySQL Database Credentials
DB_HOST = 'localhost'
DB_USER = 'root'  # Replace with your MySQL username
DB_PASSWORD = ''  # Replace with your MySQL password
DB_NAME = 'lib_main'

# Define the secure root directory
LIB2_PATH = Path('C:\\xampp\\htdocs\\lib2').resolve()
if not LIB2_PATH.is_dir():
    LIB2_PATH.mkdir()

app = Flask(__name__)
app.secret_key = 'super_secret_key'

# Simple path validation helper
def validate_path(requested_path):
    path = Path(LIB2_PATH, requested_path).resolve()
    return path if str(path).startswith(str(LIB2_PATH)) else None

def is_password_correct(password):
    conn = None
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = conn.cursor()
        
        # Query the database for the provided password
        cursor.execute("SELECT pass FROM password WHERE pass = %s", (password,))
        result = cursor.fetchone()
        
        return result is not None
    except mysql.connector.Error as e:
        print(f"Database error: {e}")
        return False
    finally:
        if conn and conn.is_connected():
            conn.close()

@app.before_request
def check_auth():
    if request.path.startswith('/static') or request.path == url_for('login'):
        return

    if request.cookies.get('auth_token') != 'authenticated':
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if is_password_correct(password):
            response = redirect(url_for('dashboard'))
            response.set_cookie('auth_token', 'authenticated', max_age=3600, httponly=True)
            return response
        else:
            flash('Incorrect password')
    return render_template('login.html')


@app.route('/')
@app.route('/dashboard')
def dashboard():
    requested_path = request.args.get('path', '')
    current_path = validate_path(requested_path)
    if not current_path or not current_path.is_dir():
        flash("Invalid path or folder not found.")
        # If the path is invalid, redirect to the root dashboard
        return redirect(url_for('dashboard'))

    try:
        items = []
        for item in current_path.iterdir():
            items.append({
                'name': item.name,
                'is_dir': item.is_dir(),
                'size': item.stat().st_size if not item.is_dir() else None
            })

        breadcrumbs = []
        # Create breadcrumbs for navigation
        relative_path = current_path.relative_to(LIB2_PATH)
        path_parts = list(relative_path.parts)
        for i, part in enumerate(path_parts):
            path_crumb = Path(*path_parts[:i+1])
            breadcrumbs.append({'name': part, 'path': str(path_crumb)})
        
        return render_template('dev.html', items=items, current_path=requested_path, breadcrumbs=breadcrumbs)

    except Exception as e:
        flash(f"Error accessing directory: {e}")
        return redirect(url_for('dashboard'))

@app.route('/upload', methods=['POST'])
def upload_file():
    target_path_str = request.form.get('path', '')
    target_path = validate_path(target_path_str)
    if not target_path or not target_path.is_dir():
        return jsonify({'success': False, 'message': 'Invalid target directory.'}), 400

    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file part.'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file.'}), 400

    filename = Path(file.filename).name
    save_path = target_path / filename
    
    if save_path.exists():
        return jsonify({'success': False, 'message': 'File already exists. Rename the file and try again.'}), 409
    
    try:
        file.save(str(save_path))
        return jsonify({'success': True, 'message': 'File uploaded successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error saving file: {e}'}), 500

@app.route('/delete', methods=['POST'])
def delete_item():
    item_path_str = request.form.get('path', '')
    item_path = validate_path(item_path_str)
    if not item_path or not item_path.exists():
        return jsonify({'success': False, 'message': 'Invalid path or item not found.'}), 404

    try:
        if item_path.is_dir():
            shutil.rmtree(str(item_path))
        else:
            os.remove(str(item_path))
        return jsonify({'success': True, 'message': 'Item deleted successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error deleting item: {e}'}), 500

@app.route('/download')
def download_item():
    item_path_str = request.args.get('path', '')
    item_path = validate_path(item_path_str)
    if not item_path or not item_path.is_file():
        flash("File not found or invalid path.")
        return redirect(url_for('dashboard'))
    
    return send_from_directory(item_path.parent, item_path.name, as_attachment=True)

@app.route('/terminal', methods=['POST'])
def run_command():
    command = request.json.get('command', '')
    if not command.strip():
        return jsonify({'success': True, 'output': '', 'error': ''})
    
    # Optional: Restrict commands (e.g., prevent 'rm -rf /')
    # This is a very basic example; for a production app, a robust whitelist is better.
    if '..' in command or 'sudo' in command or 'rm -rf' in command:
         return jsonify({'success': False, 'output': '', 'error': 'Command denied for security reasons.'}), 403

    try:
        result = subprocess.run(
            command,
            shell=True,
            check=False, # Changed to False to prevent exceptions from non-zero return codes
            text=True,
            capture_output=True,
            cwd=LIB2_PATH
        )
        return jsonify({
            'success': True,
            'output': result.stdout,
            'error': result.stderr,
            'return_code': result.returncode
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'output': '',
            'error': str(e),
            'return_code': 1
        })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5002)
