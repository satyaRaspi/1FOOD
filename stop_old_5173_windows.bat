@echo off
title Stop old Vite / 5173 server
echo Stopping any old server using port 5173...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173"') do (
    echo Stopping PID %%a
    taskkill /F /PID %%a
)
echo Done. Now run start_app_windows.bat and open http://localhost:8000/
pause
