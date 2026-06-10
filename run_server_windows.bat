@echo off
setlocal
cd /d "%~dp0"
title Truflux FoodFlow Server
where py >nul 2>&1
if %errorlevel%==0 (
    set "PYTHON_CMD=py -3"
) else (
    set "PYTHON_CMD=python"
)
echo Starting server at http://localhost:8000/
%PYTHON_CMD% -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pause
