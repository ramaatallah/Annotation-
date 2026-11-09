@echo off
echo =========================================================
echo    Starting Wahaj Arabic Academic NLP & Annotation Server
echo =========================================================

cd /d "%~dp0api"

if exist "..\.venv\Scripts\activate.bat" (
    call "..\.venv\Scripts\activate.bat"
) else if exist "..\backend\.venv\Scripts\activate.bat" (
    call "..\backend\.venv\Scripts\activate.bat"
)

python main.py
pause
