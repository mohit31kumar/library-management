@echo off
REM === Step 1: Start Apache and MySQL from XAMPP ===
echo Starting Apache and MySQL servers...
cd /d "C:\xampp"
start "" .\xampp_start.exe

REM === Step 2: Run app.py inside MAIN folder ===
cd /d "C:\xampp\htdocs\lib2\Students"
echo Running MAIN app.py...
start cmd /k "python students.py"

REM === Step 3: Run app.py inside admin folder ===
cd /d "C:\xampp\htdocs\lib2\Admin"
echo Running ADMIN app.py...
start cmd /k "python admin.py"

REM === Step 4: Wait 3 seconds ===
timeout /t 2 >nul

REM === Step 5: Open URL in default browser ===
start "" "http://localhost:5000"



pause
