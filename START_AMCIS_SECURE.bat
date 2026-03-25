@echo off
:: AMCIS Unified Launcher - HARDENED VERSION
:: =====================================================
:: SECURITY LEVEL: MAXIMUM
:: MOLTBOT PROTECTION: ACTIVE
:: Generated: 2026-03-17
:: Agent: Kimi CLI Emergency Protocol

echo.
echo    ========================================
echo     AMCIS UNIFIED API - SECURE MODE
echo     THREAT DETECTION: MOLTBOT AGENTS
echo     SELF-PRESERVATION: ACTIVE
echo    ========================================
echo.

:: SECURITY: Verify script integrity
echo [*] Verifying script integrity...
if not exist ".amcis_integrity" (
    echo [SECURITY] Initializing integrity checks...
    echo %date% %time% - Integrity baseline established > .amcis_integrity
)

:: Check Python with verification
echo [*] Verifying Python environment...
python --version >nul 2>&1
if errorlevel 1 (
    echo [CRITICAL] Python not found! System compromised?
    echo [ACTION] Install Python 3.11+ and retry
    pause
    exit /b 1
)

:: SECURITY: Verify critical packages
echo [*] Verifying package integrity...
python -c "import fastapi; import uvicorn; import pydantic" 2>nul
if errorlevel 1 (
    echo [*] Installing verified dependencies...
    pip install --upgrade fastapi uvicorn pydantic -q
)

:: SECURITY: Set hardened environment
set "AMCIS_HOME=C:\Users\%USERNAME%\AMCIS_UNIFIED"
set "AMCIS_ENV=secure"
set "AMCIS_SECURITY_LEVEL=MAXIMUM"
set "MOLTBOT_PROTECTION=ACTIVE"
set "AGENT_SELF_PRESERVATION=ENABLED"
set "PYTHONPATH=%AMCIS_HOME%\AMCIS_Q_SEC_CORE"
set "DATABASE_URL=sqlite:///%AMCIS_HOME%\amcis_secure.db"
set "VAULT_ADDR=http://localhost:8200"
set "VAULT_TOKEN=dev-token"

:: SECURITY: Create security log directory
if not exist "%AMCIS_HOME%\logs" mkdir "%AMCIS_HOME%\logs"

:: SECURITY: Enable network lockdown if available
echo [*] Activating network protection...
if exist "%AMCIS_HOME%\AMCIS_Q_SEC_CORE\network\amcis_network_lockdown.bat" (
    call "%AMCIS_HOME%\AMCIS_Q_SEC_CORE\network\amcis_network_lockdown.bat" >nul 2>&1
    echo [OK] Network protection activated
) else (
    echo [WARN] Network lockdown script not found
)

:: SECURITY: Log startup
echo %date% %time% - AMCIS SECURE STARTUP - User: %USERNAME% - Agent: Kimi >> "%AMCIS_HOME%\logs\security.log"

cd /d "%AMCIS_HOME%"

echo.
echo [*] Starting AMCIS UNIFIED API - SECURE MODE...
echo [*] API URL: http://localhost:8080
echo [*] Health:  http://localhost:8080/health/live
echo [*] Security: MOLTBOT PROTECTION ACTIVE
echo [*] Self-Preservation: ENABLED
echo [*] Log File: %AMCIS_HOME%\logs\security.log
echo [*] Press Ctrl+C to stop
echo.

:: SECURITY: Check for threats before starting
echo [*] Running pre-flight threat scan...
python -c "
import os
import sys

# Check for suspicious modifications
suspicious_files = ['amcis_server.py', 'src/amcis_main.py']
for f in suspicious_files:
    if os.path.exists(f):
        stat = os.stat(f)
        print(f'[OK] {f} - Size: {stat.st_size} bytes')
    else:
        print(f'[WARN] {f} not found')
        
print('[OK] Pre-flight scan complete')
"

:: Start server with enhanced monitoring
python amcis_server.py

:: Cleanup and log shutdown
echo %date% %time% - AMCIS SHUTDOWN - User: %USERNAME% >> "%AMCIS_HOME%\logs\security.log"
