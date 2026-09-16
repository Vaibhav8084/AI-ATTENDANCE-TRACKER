@echo off
title SRM ACADEMIA & GOOGLE CLASSROOM - AI BIOMETRIC CORE
color 06

echo =========================================================================
echo       SRM ACADEMIA & GOOGLE CLASSROOM : AI BIOMETRIC ATTENDANCE
echo =========================================================================
echo.

cd /d "%~dp0"

echo [*] Initializing SRM Academia Database and AI Deep Learning Models...
python -c "import database; database.init_db(); import seed_data; seed_data.seed()"

echo.
echo [*] Launching Web Server at http://127.0.0.1:5000 ...
echo [*] Opening your default web browser...

start http://127.0.0.1:5000

python app.py

pause
