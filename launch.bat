@echo off
setlocal enabledelayedexpansion
title NewsOps Launcher

echo ===================================================
echo             NewsOps Intelligence Engine
echo ===================================================
echo.
echo Choose launch mode:
echo   [1] Docker Compose (Runs Mongo + Backend + Web in Docker)
echo   [2] Local Dev Mode (Python Backend + Next.js Web locally)
echo   [3] Run Tests (pytest backend tests)
echo   [4] Exit
echo.
set /p choice="Enter choice [1-4] (default is 2): "

if "%choice%"=="" set choice=2

if "%choice%"=="1" (
    echo.
    echo [*] Starting Docker Compose...
    docker compose up --build
    goto end
)

if "%choice%"=="2" (
    echo.
    echo [*] Starting NewsOps Backend on http://localhost:8000...
    start "NewsOps Backend" cmd /k "python run_backend.py"
    
    timeout /t 2 /nobreak >nul
    
    echo [*] Starting NewsOps Web Frontend on http://localhost:3000...
    start "NewsOps Web" cmd /k "cd web && npm run dev"
    
    timeout /t 3 /nobreak >nul
    
    echo [*] Opening browser to http://localhost:3000...
    start http://localhost:3000
    
    echo.
    echo NewsOps is running!
    echo   - Web UI: http://localhost:3000
    echo   - Backend API Docs: http://localhost:8000/docs
    echo.
    echo Keep the opened command windows running. Close them to stop NewsOps.
    goto end
)

if "%choice%"=="3" (
    echo.
    echo [*] Running Pytest suite...
    python -m pytest tests -v
    echo.
    pause
    goto end
)

:end
