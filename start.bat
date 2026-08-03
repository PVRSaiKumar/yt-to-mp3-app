@echo off
echo ====================================
echo   YT to MP3 - Starting Server...
echo ====================================
echo.

cd /d "%~dp0"

echo Installing dependencies...
pip install -r requirements.txt -q

echo.
echo Starting server on http://localhost:5000
echo Press Ctrl+C to stop
echo.

start http://localhost:5000
python app.py