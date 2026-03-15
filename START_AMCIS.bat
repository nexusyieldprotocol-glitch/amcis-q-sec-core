@echo off
:: AMCIS Unified Launcher - No Docker Required
:: =====================================================

echo.
echo    ========================================
echo     AMCIS UNIFIED API - Native Windows
echo    ========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Install Python 3.11+
    pause
    exit /b 1
)

:: Check pip packages
echo [*] Checking dependencies...
python -c "import fastapi" 2>nul
if errorlevel 1 (
    echo [*] Installing FastAPI and dependencies...
    pip install fastapi uvicorn pydantic -q
)

:: Set environment
set "AMCIS_HOME=C:\Users\%USERNAME%\AMCIS_UNIFIED"
set "AMCIS_ENV=development"
set "PYTHONPATH=%AMCIS_HOME%\AMCIS_Q_SEC_CORE;%AMCIS_HOME%\..\CTVP"
set "DATABASE_URL=sqlite:///%AMCIS_HOME%\amcis.db"

cd /d "%AMCIS_HOME%"

echo.
echo [*] Starting AMCIS Unified API...
echo [*] API URL: http://localhost:8080
echo [*] Health:  http://localhost:8080/health/live
echo [*] Press Ctrl+C to stop
echo.

:: Start server
python amcis_server.py
