@echo off
REM MarketMind Frontend Startup Script for Windows
REM This script sets up the environment and starts the Vue3 frontend development server

setlocal enabledelayedexpansion

echo ========================================
echo   MarketMind Frontend Startup Script
echo ========================================
echo.

REM Get the directory where this script is located and enter frontend directory
set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%.."
cd /d "%ROOT_DIR%\frontend"

REM Check Node.js version
echo [1/5] Checking Node.js version...
node --version >nul 2>&1
if errorlevel 1 (
    echo Error: Node.js is not installed
    echo Please install Node.js 18 or higher: https://nodejs.org/
    pause
    exit /b 1
)

for /f "tokens=1 delims=." %%i in ('node --version') do set NODE_MAJOR=%%i
set NODE_MAJOR=%NODE_MAJOR:v=%
if %NODE_MAJOR% LSS 18 (
    echo Error: Node.js 18 or higher is required. Found: v%NODE_MAJOR%
    pause
    exit /b 1
)
echo + Node.js version compatible
echo.

REM Check if npm is installed
echo [2/5] Checking npm...
npm --version >nul 2>&1
if errorlevel 1 (
    echo Error: npm is not installed
    pause
    exit /b 1
)
for /f %%i in ('npm --version') do set NPM_VERSION=%%i
echo + npm version %NPM_VERSION% is installed
echo.

REM Check if node_modules exists, if not install dependencies
echo [3/5] Checking dependencies...
if not exist "node_modules" (
    echo node_modules not found. Installing dependencies...
    npm install
    if errorlevel 1 (
        echo Error: Failed to install dependencies
        pause
        exit /b 1
    )

    REM Create environment files
    echo Creating environment files...

    REM Create .env.development
    (
        echo # Development Environment Configuration
        echo VITE_API_BASE_URL=http://localhost:8000/api
        echo VITE_API_TIMEOUT=30000
    ) > .env.development

    REM Create .env.production
    (
        echo # Production Environment Configuration
        echo VITE_API_BASE_URL=/api
        echo VITE_API_TIMEOUT=30000
    ) > .env.production

    echo + Environment files created
) else (
    echo + Dependencies already installed
)
echo.

REM Verify environment files exist
echo [4/5] Checking environment configuration...
if not exist ".env.development" (
    echo Creating .env.development...
    (
        echo # Development Environment Configuration
        echo VITE_API_BASE_URL=http://localhost:8000/api
        echo VITE_API_TIMEOUT=30000
    ) > .env.development
)

if not exist ".env.production" (
    echo Creating .env.production...
    (
        echo # Production Environment Configuration
        echo VITE_API_BASE_URL=/api
        echo VITE_API_TIMEOUT=30000
    ) > .env.production
)
echo + Environment configuration ready
echo.

REM Start the development server
echo [5/5] Starting Vite development server...
echo ========================================
echo   Frontend Server Starting
echo ========================================
echo Development Server: http://localhost:5173
echo Network Access: http://^<your-ip^>:5173
echo ========================================
echo.
echo Press Ctrl+C to stop the server
echo.

REM Run the development server
npm run dev
