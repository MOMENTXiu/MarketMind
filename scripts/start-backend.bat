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

REM Start Docker infrastructure when running the backend directly
if not "%MARKETMIND_SKIP_INFRA%"=="1" (
    echo [infra] Ensuring Docker infrastructure is running...
    docker --version >nul 2>&1
    if errorlevel 1 (
        echo Error: Docker is not installed or not in PATH
        pause
        exit /b 1
    )

    docker compose -f docker-compose.dev.yml up -d postgres redis
    if errorlevel 1 (
        echo Error: Failed to start Docker infrastructure
        pause
        exit /b 1
    )

    REM Wait for postgres
    echo Waiting for postgres...
    set ATTEMPT=0
    :wait_postgres_be
    set /a ATTEMPT+=1
    if !ATTEMPT! GTR 30 (
        echo Error: postgres did not become healthy
        pause
        exit /b 1
    )
    docker inspect --format="{{.State.Status}}" marketmind-postgres-dev 2>nul | findstr "running" >nul 2>&1
    if errorlevel 1 (
        echo   Waiting for postgres (!ATTEMPT!/30)...
        timeout /t 2 /nobreak >nul
        goto wait_postgres_be
    )
    echo + postgres is running

    REM Wait for redis
    echo Waiting for redis...
    set ATTEMPT=0
    :wait_redis_be
    set /a ATTEMPT+=1
    if !ATTEMPT! GTR 30 (
        echo Error: redis did not become healthy
        pause
        exit /b 1
    )
    docker inspect --format="{{.State.Status}}" marketmind-redis-dev 2>nul | findstr "running" >nul 2>&1
    if errorlevel 1 (
        echo   Waiting for redis (!ATTEMPT!/30)...
        timeout /t 2 /nobreak >nul
        goto wait_redis_be
    )
    echo + redis is running
    echo.
)

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
if not exist "data\projects" mkdir data\projects
echo + Directories created:
echo   - outputs\charts
echo   - outputs\reports
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
if "%REDIS_ENABLED%"=="" set "REDIS_ENABLED=true"
if "%TASK_QUEUE_BACKEND%"=="" set "TASK_QUEUE_BACKEND=redis"
echo.

REM Apply database migrations
echo [db] Applying database migrations...
uv run alembic upgrade head
if errorlevel 1 (
    echo Error: Database migration failed
    pause
    exit /b 1
)
echo + Database schema is ready
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
