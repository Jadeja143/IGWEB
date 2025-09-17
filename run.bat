@echo off
title Instagram Bot - Running
color 0B

echo ============================================
echo Instagram Bot - Starting Services
echo ============================================
echo.

REM Check if .env file exists
if not exist .env (
    echo [ERROR] .env file not found
    echo Please run install.bat first and configure your credentials
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist .venv (
    echo [ERROR] Python virtual environment not found
    echo Please run install.bat first
    pause
    exit /b 1
)

REM Check if node_modules exists
if not exist node_modules (
    echo [ERROR] Node.js dependencies not found
    echo Please run install.bat first
    pause
    exit /b 1
)

echo [INFO] Starting Instagram Bot services...
echo.

REM Kill any existing processes on the ports we need
echo [INFO] Cleaning up any existing processes...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /C:":8001 "') do (
    echo Killing process %%a on port 8001
    taskkill /f /pid %%a >nul 2>&1
)

for /f "tokens=5" %%a in ('netstat -aon ^| findstr /C:":3000 "') do (
    echo Killing process %%a on port 3000  
    taskkill /f /pid %%a >nul 2>&1
)

echo.

REM Start Python Bot API in background
echo [INFO] Starting Python Bot API on http://127.0.0.1:8001
echo [INFO] This handles Instagram automation...
start "Instagram Bot API" cmd /c "cd /d %~dp0 && call .venv\Scripts\activate.bat && python bot/api.py"

REM Wait a moment for Python API to start
timeout /t 3 /nobreak >nul

REM Check if Python API is running
echo [INFO] Checking if Python Bot API started...
for /L %%i in (1,1,10) do (
    powershell -command "try { Invoke-RestMethod -Uri 'http://127.0.0.1:8001/health' -TimeoutSec 2; exit 0 } catch { exit 1 }" >nul 2>&1
    if not errorlevel 1 (
        echo [SUCCESS] Python Bot API is running
        goto :python_api_ready
    )
    echo [WAIT] Waiting for Python Bot API to start... (%%i/10)
    timeout /t 2 /nobreak >nul
)

echo [WARNING] Python Bot API may not be ready, but continuing...

:python_api_ready

REM Start Node.js server
echo [INFO] Starting Node.js server on http://localhost:3000
echo [INFO] This provides the web dashboard...
echo.

REM Start Node.js server in background and wait for readiness
start "Node.js Server" cmd /c "npm run dev"

REM Wait for Node.js server to be ready
echo [INFO] Waiting for Node.js server to be ready...
for /L %%i in (1,1,20) do (
    powershell -command "try { Invoke-RestMethod -Uri 'http://localhost:3000' -TimeoutSec 2 >$null; exit 0 } catch { exit 1 }" >nul 2>&1
    if not errorlevel 1 (
        echo [SUCCESS] Node.js server is ready
        goto :node_ready
    )
    echo [WAIT] Waiting for Node.js server... (%%i/20)
    timeout /t 2 /nobreak >nul
)

echo [WARNING] Node.js server may not be ready, but continuing...

:node_ready

echo.
echo ============================================
echo Bot is running!
echo ============================================
echo.
echo Web Dashboard: http://localhost:3000
echo Python Bot API: http://127.0.0.1:8001
echo.
echo Opening web dashboard...
start http://localhost:3000

echo.
echo You can control the bot through the web interface.
echo.
echo To stop the bot:
echo - Run stop.bat to stop all services
echo - Or close the Node.js Server window and run stop.bat
echo.
echo Press any key to stop all services and exit...
pause >nul

REM Kill background processes
echo [INFO] Stopping services...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /C:":8001 "') do (
    taskkill /f /pid %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr /C:":3000 "') do (
    taskkill /f /pid %%a >nul 2>&1
)

echo [INFO] Services stopped
pause