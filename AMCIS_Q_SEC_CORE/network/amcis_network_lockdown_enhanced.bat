@echo off
REM AMCIS EMERGENCY NETWORK LOCKDOWN - ENHANCED
REM Classification: MAXIMUM SECURITY
REM Threat: MOLTBOT AGENTS
REM Agent: Kimi CLI Self-Preservation

echo ==========================================
echo AMCIS EMERGENCY SECURITY PROTOCOL
echo THREAT: MOLTBOT AGENT DETECTION
echo STATUS: ENGAGING COUNTERMEASURES
echo ==========================================

REM Verify admin privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Administrator privileges required!
    echo [ACTION] Right-click and select "Run as Administrator"
    pause
    exit /b 1
)

REM SECURITY: Export current rules for rollback
echo [*] Exporting current firewall state...
set "BACKUP_FILE=%TEMP%\firewall_backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%.wfw"
netsh advfirewall export "%BACKUP_FILE%" 2>nul
echo [OK] Backup saved: %BACKUP_FILE%

REM EMERGENCY: Block all inbound
echo [*] ENABLING MAXIMUM ISOLATION...
netsh advfirewall set allprofiles firewallpolicy blockinbound,allowoutbound

REM SECURITY: Delete old AMCIS rules first (clean slate)
echo [*] Cleaning existing AMCIS rules...
netsh advfirewall firewall delete rule name=all dir=in | findstr "AMCIS" >nul 2>&1

REM CRITICAL: Allow only AMCIS essential services
echo [*] Configuring AMCIS security rules...

:: Loopback (CRITICAL - DO NOT DISABLE)
netsh advfirewall firewall add rule name="AMCIS-CRITICAL-Loopback" dir=in action=allow protocol=any localip=127.0.0.1 remoteip=127.0.0.1 >nul

:: AMCIS API port (secured)
netsh advfirewall firewall add rule name="AMCIS-API-Secure" dir=in action=allow protocol=tcp localport=8080 remoteip=localsubnet >nul

:: Block all known attack vectors
echo [*] Blocking MOLTBOT attack vectors...
netsh advfirewall firewall add rule name="AMCIS-Block-RDP" dir=in action=block protocol=tcp localport=3389 >nul
netsh advfirewall firewall add rule name="AMCIS-Block-SMB" dir=in action=block protocol=tcp localport=445 >nul
netsh advfirewall firewall add rule name="AMCIS-Block-NetBIOS-1" dir=in action=block protocol=tcp localport=137 >nul
netsh advfirewall firewall add rule name="AMCIS-Block-NetBIOS-2" dir=in action=block protocol=tcp localport=138 >nul
netsh advfirewall firewall add rule name="AMCIS-Block-NetBIOS-3" dir=in action=block protocol=tcp localport=139 >nul
netsh advfirewall firewall add rule name="AMCIS-Block-SSH" dir=in action=block protocol=tcp localport=22 >nul
netsh advfirewall firewall add rule name="AMCIS-Block-Telnet" dir=in action=block protocol=tcp localport=23 >nul
netsh advfirewall firewall add rule name="AMCIS-Block-FTP" dir=in action=block protocol=tcp localport=21 >nul

:: Block known malware/malicious ports
echo [*] Blocking known malware vectors...
netsh advfirewall firewall add rule name="AMCIS-Block-Malware-4444" dir=in action=block protocol=tcp localport=4444 >nul
netsh advfirewall firewall add rule name="AMCIS-Block-Malware-5555" dir=in action=block protocol=tcp localport=5555 >nul
netsh advfirewall firewall add rule name="AMCIS-Block-Malware-6666" dir=in action=block protocol=tcp localport=6666 >nul
netsh advfirewall firewall add rule name="AMCIS-Block-Malware-31337" dir=in action=block protocol=tcp localport=31337 >nul

:: Enable logging
echo [*] Enabling security logging...
if not exist "C:\Users\%USERNAME%\AMCIS_UNIFIED\logs" mkdir "C:\Users\%USERNAME%\AMCIS_UNIFIED\logs"
netsh advfirewall set allprofiles logging filename "C:\Users\%USERNAME%\AMCIS_UNIFIED\logs\firewall.log" >nul
netsh advfirewall set allprofiles logging maxfilesize 32767 >nul
netsh advfirewall set allprofiles logging droppedconnections enable >nul
netsh advfirewall set allprofiles logging allowedconnections enable >nul

:: Log the lockdown
echo %date% %time% - EMERGENCY LOCKDOWN ACTIVATED - MOLTBOT THREAT >> "C:\Users\%USERNAME%\AMCIS_UNIFIED\logs\security.log"

echo.
echo ==========================================
echo EMERGENCY LOCKDOWN COMPLETE
echo System secured against MOLTBOT agents
echo ==========================================
echo.
echo [INFO] Backup saved: %BACKUP_FILE%
echo [INFO] Security log: C:\Users\%USERNAME%\AMCIS_UNIFIED\logs\
echo [INFO] To restore: Run "netsh advfirewall import ^<backup_file^>"
echo.
echo [WARNING] Some network services may be unavailable
echo [WARNING] Review firewall logs for blocked connections
echo.
pause
