@echo off
title NewsOps - One-Click Launcher
echo ===================================================
echo             Starting NewsOps Engine
echo ===================================================
echo.
echo [*] Starting NewsOps Backend API on http://localhost:8000 ...
start "NewsOps Backend" cmd /k "python run_backend.py"

echo [*] Starting NewsOps Web Frontend on http://localhost:3000 ...
start "NewsOps Web" cmd /k "cd web && npm run dev"

timeout /t 4 /nobreak >nul

echo [*] Opening browser to http://localhost:3000 ...
start http://localhost:3000

echo.
echo ===================================================
echo NewsOps is up and running!
echo   - Web UI: http://localhost:3000
echo   - Backend API Docs: http://localhost:8000/docs
echo   - Health check: http://localhost:8000/healthz
echo.
echo Keep the opened command windows running.
echo To stop NewsOps, simply close those terminal windows.
echo ===================================================
pause
