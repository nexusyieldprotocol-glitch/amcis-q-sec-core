@echo off
:: AMCIS Simple Start Script (No Docker)
echo ======================================
echo AMCIS Native Windows Launcher
echo ======================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    exit /b 1
)

:: Set environment variables
set AMCIS_ENV=development
set AMCIS_LOG_LEVEL=INFO
set DATABASE_URL=sqlite:///C:/Users/%USERNAME%/AMCIS_UNIFIED/amcis.db
set REDIS_URL=
set VAULT_ADDR=http://localhost:8200
set VAULT_TOKEN=dev-token

cd /d C:\Users\%USERNAME%\AMCIS_UNIFIED\AMCIS_Q_SEC_CORE

echo Starting AMCIS API on http://localhost:8080
echo Press Ctrl+C to stop
echo.

:: Start the API server
python -m uvicorn src.amcis_main:app --host 0.0.0.0 --port 8080 --reload
