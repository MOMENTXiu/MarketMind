@echo off
REM MarketMind Retail Analysis Worker Startup Script for Windows

setlocal enabledelayedexpansion

echo ========================================
echo   MarketMind Retail Analysis Worker
echo ========================================
echo.

set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%.."
cd /d "%ROOT_DIR%"

REM Check uv
uv --version >nul 2>&1
if errorlevel 1 (
    echo Error: 'uv' is not installed
    pause
    exit /b 1
)

REM Install dependencies unless skipped
if not "%MARKETMIND_SKIP_DEP_SYNC%"=="1" (
    echo Installing Python dependencies...
    uv sync
    if errorlevel 1 (
        echo Error: Failed to sync Python dependencies
        pause
        exit /b 1
    )
    echo + Python dependencies installed
    echo.
)

if "%REDIS_ENABLED%"=="" set "REDIS_ENABLED=true"
if "%TASK_QUEUE_BACKEND%"=="" set "TASK_QUEUE_BACKEND=redis"
if "%REDIS_URL%"=="" set "REDIS_URL=redis://localhost:6379/0"
if "%ANALYSIS_QUEUE_NAME%"=="" set "ANALYSIS_QUEUE_NAME=retail-analysis"

echo Starting RQ worker...
echo Queue: %ANALYSIS_QUEUE_NAME%
echo Redis: %REDIS_URL%
echo Press Ctrl+C to stop the worker
echo.

uv run rq worker "%ANALYSIS_QUEUE_NAME%" --url "%REDIS_URL%"
