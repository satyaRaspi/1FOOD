@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

title Truflux FoodFlow v1.1.15 - Windows Launcher - Port 8000 Only

echo ======================================================
echo  Truflux FoodFlow v1.1.15 - Windows Launcher
echo  Python/FastAPI single-server build - NO VITE / NO 5173
echo ======================================================
echo.
echo This launcher will:
echo  1. Stop any old Vite/Node demo server on port 5173
echo  2. Start FoodFlow only on http://localhost:8000/
echo  3. Open the Landing Page in your browser
echo.

where py >nul 2>&1
if %errorlevel%==0 (
    set "PYTHON_CMD=py -3"
) else (
    set "PYTHON_CMD=python"
)

%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python was not found.
    echo Please install Python 3.10 or higher and tick "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

echo Checking for old frontend server on port 5173...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173"') do (
    echo Stopping old process on 5173, PID %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo Checking for old FoodFlow server on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000"') do (
    echo Stopping old process on 8000, PID %%a
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo Installing Python dependencies...
%PYTHON_CMD% -m pip install --upgrade pip --trusted-host pypi.org --trusted-host files.pythonhosted.org
%PYTHON_CMD% -m pip install -r requirements.txt --trusted-host pypi.org --trusted-host files.pythonhosted.org
if errorlevel 1 (
    echo.
    echo ERROR: Dependency installation failed.
    echo Try running this file again as Administrator, or use a different network/mobile hotspot.
    echo.
    pause
    exit /b 1
)

echo.
echo Starting Truflux FoodFlow on port 8000 only...
echo.
echo Landing:  http://localhost:8000/
echo Mobile:   http://localhost:8000/app
echo Cashier:  http://localhost:8000/cashier
echo Kiosk:    http://localhost:8000/kiosk
echo Admin:    http://localhost:8000/admin
echo Health:   http://localhost:8000/api/health
echo.

start "Truflux FoodFlow Server v1.1.15" cmd /k "%PYTHON_CMD% -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

echo Waiting for server to start...
timeout /t 5 /nobreak >nul

start "" "http://localhost:8000/?v=1.1.15"

echo.
echo Browser opened at http://localhost:8000/
echo This build does NOT use http://localhost:5173.
echo If Chrome still shows 5173, close that tab and open http://localhost:8000/ in a new tab or Incognito window.
echo.
pause
