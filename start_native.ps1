# AMCIS Native Windows Startup Script
# No Docker Required - Runs services directly

param(
    [switch]$Install,
    [switch]$Start,
    [switch]$Stop,
    [switch]$Status
)

$services = @{
    "AMCIS-API" = @{ Port = 8080; Script = "AMCIS_Q_SEC_CORE\src\amcis_main.py"; Args = @("--port", "8080") }
    "CTVP-API" = @{ Port = 8000; Script = "CTVP\api\gateway.py"; Args = @() }
}

function Test-Port($port) {
    $connection = Test-NetConnection -ComputerName localhost -Port $port -WarningAction SilentlyContinue
    return $connection.TcpTestSucceeded
}

function Install-AMCIS {
    Write-Host "=== Installing AMCIS Dependencies ===" -ForegroundColor Green
    
    # Install Python deps
    Set-Location $PSScriptRoot\AMCIS_Q_SEC_CORE
    pip install -r requirements.txt -q
    
    # Install CTVP deps
    if (Test-Path ..\CTVP\requirements.txt) {
        pip install -r ..\CTVP\requirements.txt -q
    }
    
    # Install Redis for Windows (optional)
    Write-Host "Note: Install Redis for Windows manually if needed:" -ForegroundColor Yellow
    Write-Host "  https://github.com/microsoftarchive/redis/releases" -ForegroundColor Gray
    
    # Install PostgreSQL for Windows (optional)
    Write-Host "Note: Install PostgreSQL for Windows manually if needed:" -ForegroundColor Yellow
    Write-Host "  https://www.postgresql.org/download/windows/" -ForegroundColor Gray
    
    Write-Host "Installation complete!" -ForegroundColor Green
}

function Start-AMCIS {
    Write-Host "=== Starting AMCIS Services ===" -ForegroundColor Green
    
    # Start AMCIS API
    if (-not (Test-Port 8080)) {
        Write-Host "Starting AMCIS API on port 8080..." -ForegroundColor Cyan
        $env:AMCIS_ENV = "development"
        $env:AMCIS_LOG_LEVEL = "INFO"
        $env:DATABASE_URL = "sqlite:///./amcis.db"  # SQLite fallback
        $env:REDIS_URL = ""  # Disable Redis if not available
        
        Start-Process python -ArgumentList "-m", "uvicorn", "AMCIS_Q_SEC_CORE.src.amcis_main:app", "--host", "0.0.0.0", "--port", "8080" -WindowStyle Hidden
        Start-Sleep 3
    } else {
        Write-Host "Port 8080 already in use!" -ForegroundColor Red
    }
    
    # Check status
    Check-Status
}

function Stop-AMCIS {
    Write-Host "=== Stopping AMCIS Services ===" -ForegroundColor Yellow
    
    # Kill Python processes running AMCIS
    Get-Process python -ErrorAction SilentlyContinue | Where-Object { 
        $_.CommandLine -match "amcis|ctvp" 
    } | Stop-Process -Force
    
    Write-Host "Services stopped." -ForegroundColor Green
}

function Check-Status {
    Write-Host "`n=== Service Status ===" -ForegroundColor Cyan
    
    foreach ($svc in $services.GetEnumerator()) {
        $running = Test-Port $svc.Value.Port
        $status = if ($running) { "✅ RUNNING" } else { "❌ STOPPED" }
        $color = if ($running) { "Green" } else { "Red" }
        Write-Host "$($svc.Key) (port $($svc.Value.Port)): " -NoNewline
        Write-Host $status -ForegroundColor $color
    }
    
    Write-Host "`n=== Health Endpoints ===" -ForegroundColor Cyan
    if (Test-Port 8080) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8080/health/live" -UseBasicParsing -TimeoutSec 2
            Write-Host "AMCIS Health: " -NoNewline
            Write-Host $response.Content -ForegroundColor Green
        } catch {
            Write-Host "AMCIS Health: Unable to connect" -ForegroundColor Red
        }
    }
}

# Main
if ($Install) { Install-AMCIS }
if ($Start) { Start-AMCIS }
if ($Stop) { Stop-AMCIS }
if ($Status) { Check-Status }

if (-not ($Install -or $Start -or $Stop -or $Status)) {
    Write-Host @"
AMCIS Native Windows Launcher
==============================

Usage:
  .\start_native.ps1 -Install   # Install dependencies
  .\start_native.ps1 -Start     # Start services
  .\start_native.ps1 -Stop      # Stop services
  .\start_native.ps1 -Status    # Check status

Or run without flags for this help.

Services will use SQLite instead of PostgreSQL (no Docker needed).
Redis caching will be disabled if Redis is not installed locally.
"@
}
