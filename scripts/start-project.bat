@echo off
REM MarketMind Project Startup Script for Windows
REM This script starts backend, frontend, and worker concurrently

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
set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%.."
cd /d "%ROOT_DIR%"

REM Check if startup scripts exist
echo [1/5] Checking startup scripts...
if not exist "%SCRIPT_DIR%start-backend.bat" (
    echo Error: start-backend.bat not found
    pause
    exit /b 1
)

if not exist "%SCRIPT_DIR%start-frontend.bat" (
    echo Error: start-frontend.bat not found
    pause
    exit /b 1
)

if not exist "%SCRIPT_DIR%start-worker.bat" (
    echo Error: start-worker.bat not found
    pause
    exit /b 1
)
echo + Startup scripts ready
echo.

REM Check system requirements
echo [2/5] Checking system requirements...

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

REM Check Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not installed or not in PATH
    pause
    exit /b 1
)
echo + Docker found
echo.

REM Start Docker infrastructure
echo [3/5] Starting Docker infrastructure...
docker compose -f docker-compose.dev.yml up -d postgres redis
if errorlevel 1 (
    echo Error: Failed to start Docker infrastructure
    pause
    exit /b 1
)

REM Wait for postgres
echo Waiting for postgres...
set ATTEMPT=0
:wait_postgres
set /a ATTEMPT+=1
if %ATTEMPT% GTR 30 (
    echo Error: postgres did not become healthy
    docker compose -f docker-compose.dev.yml ps
    pause
    exit /b 1
)
docker inspect --format="{{.State.Status}}" marketmind-postgres-dev 2>nul | findstr "running" >nul 2>&1
if errorlevel 1 (
    echo   Waiting for postgres (%ATTEMPT%/30)...
    timeout /t 2 /nobreak >nul
    goto wait_postgres
)
echo + postgres is running

REM Wait for redis
echo Waiting for redis...
set ATTEMPT=0
:wait_redis
set /a ATTEMPT+=1
if %ATTEMPT% GTR 30 (
    echo Error: redis did not become healthy
    docker compose -f docker-compose.dev.yml ps
    pause
    exit /b 1
)
docker inspect --format="{{.State.Status}}" marketmind-redis-dev 2>nul | findstr "running" >nul 2>&1
if errorlevel 1 (
    echo   Waiting for redis (%ATTEMPT%/30)...
    timeout /t 2 /nobreak >nul
    goto wait_redis
)
echo + redis is running
echo.

REM Install dependencies
echo [4/5] Installing dependencies...

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
cd /d "%ROOT_DIR%\frontend"
if not exist "node_modules" (
    npm install
    if errorlevel 1 (
        echo Error: Failed to install frontend dependencies
        pause
        exit /b 1
    )
)
cd /d "%ROOT_DIR%"
echo + Frontend dependencies installed
echo.

REM Apply database migrations
echo Applying database migrations...
uv run alembic upgrade head
if errorlevel 1 (
    echo Error: Database migration failed
    pause
    exit /b 1
)
echo + Database schema is ready
echo.

REM Create log directory and set env vars
if not exist "logs" mkdir logs
set "REDIS_ENABLED=true"
set "TASK_QUEUE_BACKEND=redis"

REM Start servers
echo [5/5] Starting servers...
echo.

REM Start backend in new window
echo Starting backend server...
set "MARKETMIND_SKIP_INFRA=1"
start "MarketMind Backend" cmd /c "set MARKETMIND_SKIP_INFRA=1 && \"%SCRIPT_DIR%start-backend.bat\" > logs\backend.log 2>&1"
echo + Backend server started
echo   Backend logs: logs\backend.log

REM Start worker in new window
echo Starting analysis worker...
start "MarketMind Worker" cmd /c "set MARKETMIND_SKIP_DEP_SYNC=1 && \"%SCRIPT_DIR%start-worker.bat\" > logs\worker.log 2>&1"
echo + Analysis worker started
echo   Worker logs: logs\worker.log

REM Wait a bit for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend in new window
echo Starting frontend server...
start "MarketMind Frontend" cmd /c "\"%SCRIPT_DIR%start-frontend.bat\" > logs\frontend.log 2>&1"
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
echo   Postgres:    localhost:5432
echo   Redis:       localhost:6379
echo.
echo Log Files:
echo   Backend:  logs\backend.log
echo   Worker:   logs\worker.log
echo   Frontend: logs\frontend.log
echo.
echo Useful commands:
echo   View backend logs:  type logs\backend.log
echo   View worker logs:   type logs\worker.log
echo   View frontend logs: type logs\frontend.log
echo   Stop all servers:   Close the server windows
echo.
echo ========================================
echo Three new windows have been opened for:
echo   1. Backend Server
echo   2. Analysis Worker
echo   3. Frontend Server
echo.
echo Close those windows to stop the servers
echo ========================================
echo.
echo Press any key to close this window...
pause >nul
