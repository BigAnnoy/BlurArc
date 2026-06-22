@echo off
chcp 65001 >nul 2>&1
title BlurArc Dev Tools
setlocal enabledelayedexpansion

:: ====================== 全局配置区（核对本地路径） ======================
set ROOT_DIR=F:\AI\Frame_Album
set BACKEND_LOG=%ROOT_DIR%\backend.log
set BACKEND_PORT=5000
set PYTHON=E:\Applications\anaconda_base\python.exe

set FLUTTER_PROJ=%ROOT_DIR%\blurarc_app
set PUB_CACHE=%ROOT_DIR%\.pub_cache
set FLUTTER_BIN=E:\Applications\flutter\bin\flutter.bat

set ANDROID_SDK=C:\Users\BIGANNOY\AppData\Local\Android\Sdk
set ADB=%ANDROID_SDK%\platform-tools\adb.exe
set EMULATOR=%ANDROID_SDK%\emulator\emulator.exe
set AVD_NAME=BlurArc_Test
set AVD_TABLET_NAME=BlurArc_Tablet
set APP_PACKAGE=com.example.blurarc_app
:: ======================================================================

cls 2>nul
echo.
echo  ==========================================
echo             BlurArc Dev Launcher
echo  ==========================================
echo.
echo  [1] Start backend (Flask only)
echo  [2] Deploy to phone   (build APK + install to USB device)
echo  [3] Deploy to emulator (build APK + install to emulator)
echo  [4] Full start (backend + phone)
echo  [5] Build PC exe (npm build + PyInstaller)
echo  [6] View backend log (last 50 lines)
echo  [7] Deploy to tablet emulator (build APK + install to tablet AVD)
echo  [8] Run PC app (frontend build + python BlurArc.py)
echo  [9] Exit
echo.

set /p CHOICE=Select [1-9]:

if "%CHOICE%"=="1" goto start_backend
if "%CHOICE%"=="2" goto deploy_phone
if "%CHOICE%"=="3" goto deploy_emulator
if "%CHOICE%"=="4" goto full_start_phone
if "%CHOICE%"=="5" goto build_exe
if "%CHOICE%"=="6" goto show_log
if "%CHOICE%"=="7" goto deploy_tablet_emulator
if "%CHOICE%"=="8" goto run_pc_app
if "%CHOICE%"=="9" exit /b 0
echo Invalid input, please input 1~9
pause
exit /b 1

:: ====================== 启动后端 ======================
:start_backend
echo.
echo [Backend] Kill process on port %BACKEND_PORT%
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%BACKEND_PORT% " ^| findstr LISTENING 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
    echo Killed PID:%%a
)
timeout /t 1 /nobreak >nul

if not exist "%PYTHON%" (
    echo ERROR: Python not found: %PYTHON%
    pause
    exit /b 1
)

echo [Backend] Start Flask server
cd /d "%ROOT_DIR%"
echo. > "%BACKEND_LOG%"
start "BlurArc Backend" /min cmd /c ""%PYTHON%" -m backend.api_server > "%BACKEND_LOG%" 2>&1"
timeout /t 4 /nobreak >nul

curl --version >nul 2>&1
if !ERRORLEVEL! equ 0 (
    curl -s http://127.0.0.1:%BACKEND_PORT%/api/health >nul 2>&1
    if !ERRORLEVEL! equ 0 (
        echo [Backend] Service OK - http://0.0.0.0:%BACKEND_PORT%
    ) else (
        echo [Backend] Health check failed, see backend.log
    )
) else (
    echo WARN: curl not found, skip health check
)
echo.
goto :eof

:: ====================== 构建 APK ======================
:build_apk
if not exist "%FLUTTER_BIN%" (
    echo ERROR: flutter not found: %FLUTTER_BIN%
    pause
    exit /b 1
)
if not exist "%FLUTTER_PROJ%" (
    echo ERROR: Flutter project not found: %FLUTTER_PROJ%
    pause
    exit /b 1
)
echo Build debug APK
cd /d "%FLUTTER_PROJ%"
call "%FLUTTER_BIN%" build apk --debug
if !ERRORLEVEL! NEQ 0 (
    echo ERROR: Build APK failed
    pause
    exit /b 1
)
echo Build finished
goto :eof

:: ====================== 部署到手机 ======================
:deploy_phone
echo.
if not exist "%ADB%" (
    echo ERROR: adb not found: %ADB%
    pause
    exit /b 1
)

call :build_apk

echo Install APK to phone...
"%ADB%" install -r "build\app\outputs\flutter-apk\app-debug.apk"
if !ERRORLEVEL! NEQ 0 (
    echo ERROR: Install APK failed. Check USB connection and developer mode.
    pause
    exit /b 1
)

echo Launch App
"%ADB%" shell am start -n %APP_PACKAGE%/.MainActivity
echo Deploy finished!
echo.
pause
exit /b 0

:: ====================== 部署到模拟器（公共，供手机/平板 AVD 共用） ======================
:: 调用前需设置：
::   DEPLOY_AVD_NAME        - AVD 名称
::   DEPLOY_AVD_LABEL       - 用于日志显示的标签（"emulator"/"tablet emulator"）
::   DEPLOY_AVD_SKIN        - 可选，emulator 启动参数 -skin 的值；留空则不加 -skin
::   DEPLOY_WAIT_LABEL      - 启动窗口标题（"Android Emulator"/"Android Tablet Emulator"）
::   DEPLOY_FINISH_MSG      - 结束提示语
:deploy_avd_common
echo.
if not exist "%ADB%" (
    echo ERROR: adb not found: %ADB%
    pause
    exit /b 1
)
if not exist "%EMULATOR%" (
    echo ERROR: emulator not found: %EMULATOR%
    pause
    exit /b 1
)
if not exist "%FLUTTER_BIN%" (
    echo ERROR: flutter not found: %FLUTTER_BIN%
    pause
    exit /b 1
)
if not exist "%FLUTTER_PROJ%" (
    echo ERROR: Flutter project not found: %FLUTTER_PROJ%
    pause
    exit /b 1
)

echo Check AVD exists: %DEPLOY_AVD_NAME%
"%EMULATOR%" -list-avds | findstr "%DEPLOY_AVD_NAME%" >nul
if !ERRORLEVEL! NEQ 0 (
    echo ERROR: AVD "%DEPLOY_AVD_NAME%" does not exist
    echo Available AVD list:
    "%EMULATOR%" -list-avds
    echo.
    echo Create one with Android Studio AVD Manager or:
    echo   "%EMULATOR%" -create-avd -n %DEPLOY_AVD_NAME% -k "system-images;android-34;google_apis;x86_64" -d "pixel_tablet"
    pause
    exit /b 1
)

"%ADB%" devices 2>nul | findstr "emulator-" >nul
if !ERRORLEVEL! NEQ 0 (
    echo No running %DEPLOY_AVD_LABEL%, launch AVD %DEPLOY_AVD_NAME%
    if defined DEPLOY_AVD_SKIN (
        start "%DEPLOY_WAIT_LABEL%" "%EMULATOR%" -avd %DEPLOY_AVD_NAME% -skin %DEPLOY_AVD_SKIN%
    ) else (
        start "%DEPLOY_WAIT_LABEL%" "%EMULATOR%" -avd %DEPLOY_AVD_NAME%
    )

    echo Wait emulator device online
    :wait_avd_dev
    timeout /t 10 /nobreak >nul
    "%ADB%" devices 2>nul | findstr "emulator-" >nul
    if !ERRORLEVEL! NEQ 0 (
        tasklist | findstr emulator.exe >nul || (
            echo ERROR: Emulator process exited, launch failed
            pause
            exit /b 1
        )
        goto wait_avd_dev
    )

    echo Wait system boot complete
    :wait_avd_boot
    "%ADB%" shell getprop sys.boot_completed 2>nul | findstr "1" >nul
    if !ERRORLEVEL! NEQ 0 (
        timeout /t 5 /nobreak >nul
        goto wait_avd_boot
    )
    echo %DEPLOY_AVD_LABEL% boot finished
) else (
    echo Emulator already running
)

call :build_apk

echo Install APK to %DEPLOY_AVD_LABEL%
"%ADB%" install -r "build\app\outputs\flutter-apk\app-debug.apk"
if !ERRORLEVEL! NEQ 0 (
    echo ERROR: Install APK failed
    pause
    exit /b 1
)

echo Launch App
"%ADB%" shell am start -n %APP_PACKAGE%/.MainActivity
echo %DEPLOY_FINISH_MSG%
echo.
pause
exit /b 0

:: ====================== 部署到模拟器（手机 AVD） ======================
:deploy_emulator
set DEPLOY_AVD_NAME=%AVD_NAME%
set DEPLOY_AVD_LABEL=emulator
set DEPLOY_WAIT_LABEL=Android Emulator
set DEPLOY_FINISH_MSG=Deploy finished!
call :deploy_avd_common

:: ====================== 一键启动（后端 + 手机） ======================
:full_start_phone
call :start_backend
call :deploy_phone
echo.
echo ==========================================
echo Full launch finished
echo Backend: http://127.0.0.1:%BACKEND_PORT%
echo App running on phone
echo ==========================================
pause
exit /b 0

:: ====================== 构建 PC exe ======================
:build_exe
echo.
echo [PC Exe] Step 1/4: Clean old builds
cd /d "%ROOT_DIR%"
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"

echo [PC Exe] Step 2/4: Build frontend
cd /d "%ROOT_DIR%\frontend"
call npm run build
if !ERRORLEVEL! NEQ 0 (
    echo ERROR: Frontend build failed
    pause
    exit /b 1
)

echo [PC Exe] Step 3/4: Run PyInstaller
cd /d "%ROOT_DIR%"
call pyinstaller BlurArc.spec --noconfirm
if !ERRORLEVEL! NEQ 0 (
    echo ERROR: PyInstaller build failed
    pause
    exit /b 1
)

echo [PC Exe] Step 4/4: Verify output
if not exist "%ROOT_DIR%\dist\BlurArc\BlurArc.exe" (
    echo ERROR: BlurArc.exe not generated
    pause
    exit /b 1
)

echo.
echo ==========================================
echo Build successful!
echo ==========================================
echo Output: dist\BlurArc\
for %%f in ("%ROOT_DIR%\dist\BlurArc\BlurArc.exe") do echo   BlurArc.exe: %%~zf bytes
echo.
pause
exit /b 0

:: ====================== 部署到平板模拟器 ======================
:deploy_tablet_emulator
set DEPLOY_AVD_NAME=%AVD_TABLET_NAME%
set DEPLOY_AVD_LABEL=tablet emulator
set DEPLOY_AVD_SKIN=1280x800
set DEPLOY_WAIT_LABEL=Android Tablet Emulator
set DEPLOY_FINISH_MSG=Deploy to tablet finished!
call :deploy_avd_common

:: ====================== 启动 PC 端（前端构建 + BlurArc.py） ======================
:run_pc_app
echo.
if not exist "%PYTHON%" (
    echo ERROR: Python not found: %PYTHON%
    pause
    exit /b 1
)
if not exist "%ROOT_DIR%\frontend\package.json" (
    echo ERROR: frontend/package.json not found: %ROOT_DIR%\frontend
    pause
    exit /b 1
)
if not exist "%ROOT_DIR%\src\BlurArc.py" (
    echo ERROR: src/BlurArc.py not found: %ROOT_DIR%\src
    pause
    exit /b 1
)

echo [PC App] Step 1/2: Build frontend (npm run build)
cd /d "%ROOT_DIR%\frontend"
call npm run build
if !ERRORLEVEL! NEQ 0 (
    echo ERROR: Frontend build failed
    pause
    exit /b 1
)

echo [PC App] Step 2/2: Launch BlurArc.py
cd /d "%ROOT_DIR%"
start "BlurArc" "%PYTHON%" "%ROOT_DIR%\src\BlurArc.py"
echo PC app launched.
echo.
pause
exit /b 0

:: ====================== 查看后端日志 ======================
:show_log
echo.
echo Last 50 lines of backend.log
echo --------------------------------------------------
if exist "%BACKEND_LOG%" (
    powershell -Command "Get-Content ""%BACKEND_LOG%"" -Tail 50 -ErrorAction SilentlyContinue"
) else (
    echo backend.log not found, start backend first
)
echo --------------------------------------------------
pause
exit /b 0
