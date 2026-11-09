@echo off
echo =========================================================
echo    Starting Wahaj Fullstack Platform (Backend + Frontend)
echo =========================================================

start "Wahaj FastAPI Backend" cmd /k "call run_server.bat"
timeout /t 3 /nobreak >nul
start "Wahaj Frontend Website" cmd /k "call run_website.bat"

echo.
echo Backend is starting at: http://127.0.0.1:8000
echo Frontend will open at:  http://localhost:5173
echo.
pause
