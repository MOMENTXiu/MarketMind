@echo off
REM MarketMind Project Startup Script for Windows
REM This script starts both frontend and backend servers concurrently

setlocal enabledelayedexpansion

echo.
echo ========================================
echo.
echo         MarketMind Project
echo      Full Stack Startup Script
echo.
echo ========================================
echo.

REM Get the directory where this script is located
cd /d %~dp0

REM Check if startup scripts exist
echo [1/4] Checking startup scripts...
if not exist "start-backend.bat" (
    echo Error: start-backend.bat not found
    pause
    exit /b 1
)

if not exist "start-frontend.bat" (
    echo Error: start-frontend.bat not found
    pause
    exit /b 1
)
echo + Startup scripts ready
echo.

REM Check system requirements
echo [2/4] Checking system requirements...

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python 3 is not installed
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo + Python %PYTHON_VERSION% found

REM Check uv
uv --version >nul 2>&1
if errorlevel 1 (
    echo Error: 'uv' package manager is not installed
    echo Install with: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    pause
    exit /b 1
)
echo + uv package manager found

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo Error: Node.js is not installed
    pause
    exit /b 1
)
for /f %%i in ('node --version') do set NODE_VERSION=%%i
echo + Node.js %NODE_VERSION% found

REM Check npm
npm --version >nul 2>&1
if errorlevel 1 (
    echo Error: npm is not installed
    pause
    exit /b 1
)
for /f %%i in ('npm --version') do set NPM_VERSION=%%i
echo + npm %NPM_VERSION% found
echo.

REM Pre-install dependencies
echo [3/4] Installing dependencies...

REM Backend dependencies
echo Installing backend dependencies...
uv sync
if errorlevel 1 (
    echo Error: Failed to install backend dependencies
    pause
    exit /b 1
)
echo + Backend dependencies installed

REM Frontend dependencies
echo Installing frontend dependencies...
cd frontend
if not exist "node_modules" (
    npm install
    if errorlevel 1 (
        echo Error: Failed to install frontend dependencies
        pause
        exit /b 1
    )
)
cd ..
echo + Frontend dependencies installed
echo.

REM Create log directory
if not exist "logs" mkdir logs

REM Start servers
echo [4/4] Starting servers...
echo.

REM Start backend in new window
echo Starting backend server...
start "MarketMind Backend" cmd /c "start-backend.bat > logs\backend.log 2>&1"
echo + Backend server started
echo   Backend logs: logs\backend.log

REM Wait a bit for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend in new window
echo Starting frontend server...
start "MarketMind Frontend" cmd /c "start-frontend.bat > logs\frontend.log 2>&1"
echo + Frontend server started
echo   Frontend logs: logs\frontend.log

echo.
echo ========================================
echo     MarketMind is now running!
echo ========================================
echo.
echo Access Points:
echo   Frontend:    http://localhost:5173
echo   Backend API: http://localhost:8000/api
echo   API Docs:    http://localhost:8000/api/docs
echo.
echo Log Files:
echo   Backend:  logs\backend.log
echo   Frontend: logs\frontend.log
echo.
echo Useful commands:
echo   View backend logs:  type logs\backend.log
echo   View frontend logs: type logs\frontend.log
echo   Stop all servers:   Close the backend and frontend windows
echo.
echo ========================================
echo Two new windows have been opened for:
echo   1. Backend Server
echo   2. Frontend Server
echo.
echo Close those windows to stop the servers
echo ========================================
echo.
echo Press any key to close this window...
pause >nul
