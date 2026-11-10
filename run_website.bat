@echo off
echo =========================================================
echo    Starting Wahaj Frontend Website (Next.js Dev Server)
echo =========================================================

cd /d "%~dp0website"
call npm run dev
pause
