@echo off
echo ==========================================
echo    Starting Arabic NER Backend Server...
echo ==========================================
cd api
call ..\.venv\Scripts\activate
uvicorn main:app --port 8000 --reload
pause