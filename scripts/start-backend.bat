@echo off
REM MarketMind Backend Startup Script for Windows
REM This script sets up the environment and starts the FastAPI backend server

setlocal enabledelayedexpansion

echo ========================================
echo   MarketMind Backend Startup Script
echo ========================================
echo.

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%.."
cd /d "%ROOT_DIR%"

REM Check Python version
echo [1/6] Checking Python version...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.13 or higher
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo + Python version %PYTHON_VERSION% found
echo.

REM Check if uv is installed
echo [2/6] Checking uv package manager...
uv --version >nul 2>&1
if errorlevel 1 (
    echo Error: 'uv' is not installed
    echo Please install uv: https://github.com/astral-sh/uv
    echo Quick install: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
    pause
    exit /b 1
)
echo + uv is installed
echo.

REM Install/sync Python dependencies
echo [3/6] Installing Python dependencies...
uv sync
if errorlevel 1 (
    echo Error: Failed to sync Python dependencies
    pause
    exit /b 1
)
echo + Python dependencies installed
echo.

REM Create necessary directories
echo [4/6] Creating required directories...
if not exist "outputs\charts" mkdir outputs\charts
if not exist "outputs\reports" mkdir outputs\reports
if not exist "outputs\audio" mkdir outputs\audio
if not exist "data\projects" mkdir data\projects
echo + Directories created:
echo   - outputs\charts
echo   - outputs\reports
echo   - outputs\audio
echo   - data\projects
echo.

REM Check if .env file exists (optional)
echo [5/6] Checking environment configuration...
if not exist ".env" (
    echo Notice: No .env file found. Using default configuration.
    echo You can create a .env file to override default settings.
) else (
    echo + .env file found
)
echo.

REM Start the backend server
echo [6/6] Starting FastAPI backend server...
echo ========================================
echo   Backend Server Starting
echo ========================================
echo API Base URL: http://localhost:8000/api
echo API Docs: http://localhost:8000/api/docs
echo Health Check: http://localhost:8000/api/health
echo ========================================
echo.
echo Press Ctrl+C to stop the server
echo.

REM Run the server
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
