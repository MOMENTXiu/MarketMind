@echo off
REM MarketMind Project Deploy Script for Windows
REM Prepares infrastructure, dependencies, runtime wiring, migrations, and seed data.
REM Does NOT start long-running backend / worker / frontend servers.

setlocal enabledelayedexpansion

echo.
echo ========================================
echo.
echo      MarketMind Project Deploy
echo   Infra / Deps / Checks / Migrations
echo.
echo ========================================
echo.

set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%.."
cd /d "%ROOT_DIR%"

REM Check system requirements
echo [1/6] Checking system requirements...

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python 3 is not installed
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo   Python %PYTHON_VERSION% found

REM Check uv
uv --version >nul 2>&1
if errorlevel 1 (
    echo Error: 'uv' package manager is not installed
    echo Install with: powershell -c "irm https://astral.sh/uv/install.ps1 ^| iex"
    pause
    exit /b 1
)
echo   uv package manager found

REM Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo Error: Node.js is not installed
    pause
    exit /b 1
)
for /f %%i in ('node --version') do set NODE_VERSION=%%i
echo   Node.js %NODE_VERSION% found

REM Check npm
npm --version >nul 2>&1
if errorlevel 1 (
    echo Error: npm is not installed
    pause
    exit /b 1
)
for /f %%i in ('npm --version') do set NPM_VERSION=%%i
echo   npm %NPM_VERSION% found

REM Check Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not installed or not in PATH
    pause
    exit /b 1
)
echo   Docker found

REM Check curl
curl --version >nul 2>&1
if errorlevel 1 (
    echo   Warning: curl is not installed (will skip some readiness probes)
) else (
    echo   curl found
)
echo.

REM Set local runtime defaults
echo [2/6] Setting local runtime defaults...
set "REDIS_ENABLED=true"
set "TASK_QUEUE_BACKEND=redis"
if "%REDIS_URL%"=="" set "REDIS_URL=redis://localhost:6379/0"
if "%DATABASE_URL%"=="" set "DATABASE_URL=postgresql+psycopg://marketmind:marketmind_dev_password@localhost:5432/marketmind"
if "%ANALYSIS_QUEUE_NAME%"=="" set "ANALYSIS_QUEUE_NAME=retail-analysis"
echo   REDIS_ENABLED=true
echo   TASK_QUEUE_BACKEND=redis
echo   REDIS_URL=%REDIS_URL%
echo   DATABASE_URL=%DATABASE_URL%
echo   ANALYSIS_QUEUE_NAME=%ANALYSIS_QUEUE_NAME%
echo.

REM Start Docker infrastructure
echo [3/6] Starting Docker infrastructure...
docker compose -f docker-compose.dev.yml up -d postgres redis minio minio-init
if errorlevel 1 (
    echo Error: Failed to start Docker infrastructure
    pause
    exit /b 1
)

REM Wait for postgres
echo   Waiting for postgres...
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
    echo     Waiting for postgres (%ATTEMPT%/30)...
    timeout /t 2 /nobreak >nul
    goto wait_postgres
)
echo   postgres is running

REM Wait for redis
echo   Waiting for redis...
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
    echo     Waiting for redis (%ATTEMPT%/30)...
    timeout /t 2 /nobreak >nul
    goto wait_redis
)
echo   redis is running

REM Wait for minio
echo   Waiting for minio...
set ATTEMPT=0
:wait_minio
set /a ATTEMPT+=1
if %ATTEMPT% GTR 30 (
    echo Error: minio did not become healthy
    docker compose -f docker-compose.dev.yml ps
    pause
    exit /b 1
)
docker inspect --format="{{.State.Status}}" marketmind-minio-dev 2>nul | findstr "running" >nul 2>&1
if errorlevel 1 (
    echo     Waiting for minio (%ATTEMPT%/30)...
    timeout /t 2 /nobreak >nul
    goto wait_minio
)
echo   minio is running
echo.

REM Backend dependencies
echo [4/6] Installing backend dependencies...
uv sync
if errorlevel 1 (
    echo Error: Failed to install backend dependencies
    pause
    exit /b 1
)
echo   Backend dependencies installed
echo.

REM Frontend dependencies
echo [5/6] Installing frontend dependencies...
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
echo   Frontend dependencies installed
echo.

REM Backend runtime checks and migrations
echo [6/6] Running runtime checks and migrations...

echo   Checking backend runtime wiring...
uv run python -m backend.core.runtime_checks check-retail-runtime --dry-run
if errorlevel 1 (
    echo Error: Backend runtime check failed
    pause
    exit /b 1
)
echo   Backend runtime wiring is PostgreSQL/Redis ready

echo   Checking object storage readiness...
uv run python -m backend.core.runtime_checks check-object-storage --sandbox
if errorlevel 1 (
    echo   Object storage check skipped or incomplete
)
echo   Object storage check completed

echo   Applying database migrations...
uv run python -m alembic upgrade head
if errorlevel 1 (
    echo Error: Database migration failed
    pause
    exit /b 1
)
echo   Database schema is ready

REM Create required local directories
if not exist "logs" mkdir logs
if not exist "outputs\charts" mkdir outputs\charts
if not exist "outputs\reports" mkdir outputs\reports
if not exist "data\projects" mkdir data\projects
echo   Local directories ready
echo.

echo ========================================
echo    MarketMind deploy complete!
echo ========================================
echo.
echo Infrastructure is ready:
echo   Postgres:     localhost:5432
echo   Redis:        localhost:6379
echo   MinIO API:    http://localhost:9000
echo   MinIO Console: http://localhost:9001
echo.
echo Next step:
echo   scripts\start-project.bat
echo.

pause
