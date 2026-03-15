@echo off
REM AMCIS Windows Installer Build Script
REM Creates standalone Windows executable using PyInstaller

echo ==========================================
echo AMCIS Windows Installer Builder
echo ==========================================
echo.

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    exit /b 1
)

REM Check for PyInstaller
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM Install required dependencies
echo Installing dependencies...
pip install -r ..\AMCIS_Q_SEC_CORE\requirements.txt

REM Create dist directory
if not exist "dist" mkdir dist
if not exist "build" mkdir build

REM Build the executable
echo.
echo Building AMCIS Windows executable...
echo This may take several minutes...
echo.

pyinstaller amcis_windows.spec --clean --noconfirm

if errorlevel 1 (
    echo ERROR: Build failed!
    exit /b 1
)

REM Create installer package
echo.
echo Creating installer package...

if not exist "dist\AMCIS-Installer" mkdir "dist\AMCIS-Installer"

xcopy /E /I /Y "dist\AMCIS-Security-Platform" "dist\AMCIS-Installer\" 2>nul
copy "..\README.md" "dist\AMCIS-Installer\" 2>nul
copy "..\.env.example" "dist\AMCIS-Installer\.env.example" 2>nul
copy "install_instructions_windows.txt" "dist\AMCIS-Installer\" 2>nul

REM Create ZIP archive
echo Creating ZIP archive...
cd dist
powershell Compress-Archive -Path "AMCIS-Installer" -DestinationPath "AMCIS-Security-Platform-Windows.zip" -Force
cd ..

echo.
echo ==========================================
echo Build Complete!
echo ==========================================
echo Output: dist\AMCIS-Security-Platform-Windows.zip
echo.
pause
