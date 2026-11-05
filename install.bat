@echo off
setlocal
title NewsOps - One-Click Install and Launch
echo ================================================================
echo             NewsOps - One-Click Setup and Launch
echo ================================================================
echo.

echo [1/4] Checking and installing Python dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [!] Warning installing Python packages, continuing with installed system packages...
)

echo.
echo [2/4] Checking and installing Web dependencies...
cd web
call npm ci --legacy-peer-deps
cd ..

echo.
echo [3/4] Starting NewsOps Backend API (http://localhost:8000) ...
start "NewsOps Backend API" cmd /k "python run_backend.py"

echo.
echo [4/4] Starting NewsOps Web Frontend (http://localhost:3000) ...
start "NewsOps Web UI" cmd /k "cd web && npm run dev"

echo.
echo Waiting for servers to initialize...
timeout /t 5 /nobreak >nul

echo Opening NewsOps in your browser...
start http://localhost:3000

echo.
echo ================================================================
echo   NewsOps is successfully installed and running!
echo   - Web UI: http://localhost:3000
echo   - Backend Docs: http://localhost:8000/docs
echo.
echo   Keep the two opened command windows running.
echo   To stop NewsOps, simply close those terminal windows.
echo ================================================================
pause
