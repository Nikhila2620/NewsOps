@echo off
title NewsOps - One-Click Launcher
echo Starting NewsOps Backend and Frontend...

start "NewsOps Backend" cmd /k "python run_backend.py"
timeout /t 2 /nobreak >nul
start "NewsOps Web" cmd /k "cd web && npm run dev"
timeout /t 3 /nobreak >nul
start http://localhost:3000

echo NewsOps launched!
echo UI: http://localhost:3000
echo API Docs: http://localhost:8000/docs
