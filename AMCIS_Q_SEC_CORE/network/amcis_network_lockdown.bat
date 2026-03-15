@echo off
REM AMCIS Q-SEC CORE - Network Isolation Script
REM Run as Administrator to enable maximum security

echo ==========================================
echo AMCIS Network Security Hardening
echo ==========================================

REM Block all inbound connections except explicit allows
netsh advfirewall set allprofiles firewallpolicy blockinbound,allowoutbound

REM Allow loopback (essential for AMCIS internal services)
netsh advfirewall firewall add rule name="AMCIS-Allow-Loopback" dir=in action=allow protocol=any localip=127.0.0.1 remoteip=127.0.0.1

REM Allow local subnet (adjust as needed)
netsh advfirewall firewall add rule name="AMCIS-Allow-LAN" dir=in action=allow remoteip=192.168.1.0/24

REM Block dangerous ports
netsh advfirewall firewall add rule name="AMCIS-Block-RDP" dir=in action=block protocol=tcp localport=3389
netsh advfirewall firewall add rule name="AMCIS-Block-SMB" dir=in action=block protocol=tcp localport=445
netsh advfirewall firewall add rule name="AMCIS-Block-NetBIOS" dir=in action=block protocol=tcp localport=137,138,139

echo.
echo Network isolation enabled.
echo AMCIS projects are now protected from external connections.
pause
