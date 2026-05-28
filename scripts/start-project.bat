@echo off
REM MarketMind Project Startup Script for Windows
REM Starts backend, worker, and frontend directly.
REM Run scripts\deploy-project.bat first to prepare infrastructure and dependencies.

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

REM Check required runtime tools
echo [1/3] Checking runtime tools...

REM Check uv
uv --version >nul 2>&1
if errorlevel 1 (
    echo Error: 'uv' package manager is not installed
    echo Install with: powershell -c "irm https://astral.sh/uv/install.ps1 ^| iex"
    pause
    exit /b 1
)
echo   uv found

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo Error: Node.js is not installed
    pause
    exit /b 1
)
echo   Node.js found

REM Check npm
npm --version >nul 2>&1
if errorlevel 1 (
    echo Error: npm is not installed
    pause
    exit /b 1
)
echo   npm found

REM Check curl
curl --version >nul 2>&1
if errorlevel 1 (
    echo Error: curl is not installed
    pause
    exit /b 1
)
echo   curl found

echo.

REM Verify Docker infrastructure is ready
echo [2/3] Verifying infrastructure readiness...

docker inspect --format="{{.State.Status}}" marketmind-postgres-dev 2>nul | findstr "running" >nul 2>&1
if errorlevel 1 (
    echo   postgres is not running
    set INFRA_READY=0
) else (
    echo   postgres is running
)

docker inspect --format="{{.State.Status}}" marketmind-redis-dev 2>nul | findstr "running" >nul 2>&1
if errorlevel 1 (
    echo   redis is not running
    set INFRA_READY=0
) else (
    echo   redis is running
)

docker inspect --format="{{.State.Status}}" marketmind-minio-dev 2>nul | findstr "running" >nul 2>&1
if errorlevel 1 (
    echo   minio is not running
    set INFRA_READY=0
) else (
    echo   minio is running
)

if "%INFRA_READY%"=="0" (
    echo.
    echo Error: Docker infrastructure is not ready.
    echo Run the deploy script first:
    echo   scripts\deploy-project.bat
    pause
    exit /b 1
)
echo.

REM Set runtime environment
set "REDIS_ENABLED=true"
set "TASK_QUEUE_BACKEND=redis"
if "%REDIS_URL%"=="" set "REDIS_URL=redis://localhost:6379/0"
if "%DATABASE_URL%"=="" set "DATABASE_URL=postgresql+psycopg://marketmind:marketmind_dev_password@localhost:5432/marketmind"
if "%ANALYSIS_QUEUE_NAME%"=="" set "ANALYSIS_QUEUE_NAME=retail-analysis"

REM Create log directory
if not exist "logs" mkdir logs

REM Start servers
echo [3/3] Starting servers...
echo.

REM Start backend in a new window
echo Starting backend server...
start "MarketMind Backend" cmd /c "cd /d "%ROOT_DIR%" && uv run python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 > logs\backend.log 2>&1"
echo   Backend server started
echo   Backend logs: logs\backend.log

REM Start worker in a new window
echo Starting analysis worker...
start "MarketMind Worker" cmd /c "cd /d "%ROOT_DIR%" && uv run python -m rq.cli worker %ANALYSIS_QUEUE_NAME% --url %REDIS_URL% > logs\worker.log 2>&1"
echo   Analysis worker started
echo   Worker logs: logs\worker.log

REM Wait a bit for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend in a new window
echo Starting frontend server...
start "MarketMind Frontend" cmd /c "cd /d "%ROOT_DIR%\frontend" && npm run dev -- --host 0.0.0.0 > ..\logs\frontend.log 2>&1"
echo   Frontend server started
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
echo   MinIO API:   http://localhost:9000
echo   MinIO Console: http://localhost:9001
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
