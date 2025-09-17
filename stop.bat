@echo off
title Instagram Bot - Stop Services
color 0C

echo ============================================
echo Instagram Bot - Stopping All Services
echo ============================================
echo.

echo [INFO] Stopping Python Bot API (port 8001)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /C:":8001 "') do (
    echo Killing process %%a on port 8001
    taskkill /f /pid %%a >nul 2>&1
)

echo [INFO] Stopping Node.js Server (port 3000)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /C:":3000 "') do (
    echo Killing process %%a on port 3000
    taskkill /f /pid %%a >nul 2>&1
)

echo.
echo [SUCCESS] All Instagram Bot services have been stopped
echo.
pause