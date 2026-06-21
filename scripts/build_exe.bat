@echo off
setlocal enabledelayedexpansion

echo ================================================
echo  Blur Arc Build Script v0.5.3
echo ================================================
echo.

cd /d "%~dp0\.."

echo [1/4] Cleaning old builds...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
echo Done

echo.
echo [2/4] Building frontend...
cd frontend
call npm run build
if %errorlevel% neq 0 (
    echo Frontend build failed!
    pause
    exit /b 1
)
cd ..
echo Done

echo.
echo [3/4] Running PyInstaller...
pyinstaller BlurArc.spec --noconfirm
if %errorlevel% neq 0 (
    echo Build failed!
    pause
    exit /b 1
)
echo Done

echo.
echo [4/4] Verifying output...
if not exist "dist\BlurArc\BlurArc.exe" (
    echo ERROR: BlurArc.exe not generated
    pause
    exit /b 1
)

echo.
echo ================================================
echo Build successful!
echo ================================================
echo Output: dist\BlurArc\
for %%f in ("dist\BlurArc\BlurArc.exe") do echo   BlurArc.exe: %%~zf bytes
echo.

pause