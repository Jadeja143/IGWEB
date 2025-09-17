@echo off
title Instagram Bot - Dependency Installation
color 0A

echo ============================================
echo Instagram Bot - Dependency Installation
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.10 or higher from https://python.org
    echo Make sure to check "Add to PATH" during installation
    pause
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is not installed or not in PATH
    echo Please install Node.js 18 or higher from https://nodejs.org
    pause
    exit /b 1
)

echo [INFO] Checking prerequisites...
python --version
node --version
npm --version
echo.

REM Create Python virtual environment
echo [INFO] Creating Python virtual environment...
if exist .venv (
    echo [INFO] Virtual environment already exists, skipping creation
) else (
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [INFO] Virtual environment created successfully
)
echo.

REM Activate virtual environment and install Python dependencies
echo [INFO] Installing Python dependencies...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)

pip install --upgrade pip
pip install -r bot/requirements.txt
pip install flask flask-cors requests
if errorlevel 1 (
    echo [ERROR] Failed to install Python dependencies
    pause
    exit /b 1
)
echo [INFO] Python dependencies installed successfully
echo.

REM Install Node.js dependencies
echo [INFO] Installing Node.js dependencies...
npm ci
if errorlevel 1 (
    echo [ERROR] Failed to install Node.js dependencies
    echo Trying with npm install...
    npm install
    if errorlevel 1 (
        echo [ERROR] Failed to install Node.js dependencies with npm install
        pause
        exit /b 1
    )
)
echo [INFO] Node.js dependencies installed successfully
echo.

REM Check if .env file exists
if not exist .env (
    echo [SETUP] Creating .env file from template...
    copy .env.example .env
    echo [IMPORTANT] Please edit .env file and add your Instagram credentials
    echo [IMPORTANT] At minimum, set IG_USERNAME and IG_PASSWORD
    echo.
    echo Opening .env file for editing...
    start notepad.exe .env
    echo.
    echo [WAIT] Please edit and save the .env file, then press any key to continue...
    pause >nul
)

echo ============================================
echo Installation completed successfully!
echo ============================================
echo.
echo Next steps:
echo 1. Make sure you have edited .env with your Instagram credentials
echo 2. Run run.bat to start the Instagram bot
echo.
echo For Telegram control (optional):
echo 1. Message @BotFather on Telegram to create a bot
echo 2. Add TELEGRAM_BOT_TOKEN and ADMIN_USER_ID to .env
echo.
pause