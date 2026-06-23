@echo off
chcp 65001 >nul 2>&1
title BlurArc Dev Tools
setlocal enabledelayedexpansion

rem ====================== Global config ======================
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
rem ============================================================

cls 2>nul
echo.
echo  ==========================================
echo            BlurArc Dev Launcher
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
echo  [9] Hot run phone emulator   (PC + AVD auto-start, hot reload)
echo  [10] Hot run tablet emulator (PC + AVD auto-start, hot reload)
echo  [11] Exit
echo.

set /p CHOICE=Select [1-11]:

if "%CHOICE%"=="1" goto start_backend
if "%CHOICE%"=="2" goto deploy_phone
if "%CHOICE%"=="3" goto deploy_emulator
if "%CHOICE%"=="4" goto full_start_phone
if "%CHOICE%"=="5" goto build_exe
if "%CHOICE%"=="6" goto show_log
if "%CHOICE%"=="7" goto deploy_tablet_emulator
if "%CHOICE%"=="8" goto run_pc_app
if "%CHOICE%"=="9" goto hotrun_emulator
if "%CHOICE%"=="10" goto hotrun_tablet_emulator
if "%CHOICE%"=="11" exit /b 0
echo Invalid input, please input 1~11
pause
exit /b 1

rem ====================== Start backend ======================
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
if errorlevel 1 goto skip_health
curl -s http://127.0.0.1:%BACKEND_PORT%/api/health >nul 2>&1
if errorlevel 1 (
    echo [Backend] Health check failed, see backend.log
) else (
    echo [Backend] Service OK - http://0.0.0.0:%BACKEND_PORT%
)
goto health_done
:skip_health
echo WARN: curl not found, skip health check
:health_done
echo.
goto :eof

rem ====================== Build APK ======================
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
if errorlevel 1 (
    echo ERROR: Build APK failed
    pause
    exit /b 1
)
echo Build finished
goto :eof

rem ====================== Deploy to phone ======================
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
if errorlevel 1 (
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

rem ====================== AVD common logic ======================
rem Caller must set:
rem   DEPLOY_AVD_NAME, DEPLOY_AVD_LABEL, DEPLOY_AVD_SKIN
rem   DEPLOY_WAIT_LABEL, DEPLOY_FINISH_MSG, DEPLOY_HOT
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
if errorlevel 1 (
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
if errorlevel 1 (
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
    if errorlevel 1 (
        tasklist | findstr emulator.exe >nul
        if errorlevel 1 (
            echo ERROR: Emulator process exited, launch failed
            pause
            exit /b 1
        )
        goto wait_avd_dev
    )

    echo Wait system boot complete
    :wait_avd_boot
    "%ADB%" shell getprop sys.boot_completed 2>nul | findstr "1" >nul
    if errorlevel 1 (
        timeout /t 5 /nobreak >nul
        goto wait_avd_boot
    )
    echo %DEPLOY_AVD_LABEL% boot finished
) else (
    echo Emulator already running
)

rem Mode branch
if "%DEPLOY_HOT%"=="1" goto hotrun_branch
goto install_branch

:hotrun_branch
echo.
echo ============================================================
echo Hot run Flutter on %DEPLOY_AVD_LABEL% (auto-detect device)
echo ============================================================
echo Tips: Press  r  = hot reload  (preserve state, ~1-2s)
echo       Press  R  = hot restart (reset state,    ~5s)
echo       Press  q  = quit
echo       Press  h  = help (more commands)
echo Note : Modify .dart code in IDE and save, then press r.
echo        First run takes longer (build and install on device).
echo ============================================================
echo.
cd /d "%FLUTTER_PROJ%"
call "%FLUTTER_BIN%" run
echo.
echo [Hot run] flutter run exited
pause
exit /b 0

:install_branch
call :build_apk

echo Install APK to %DEPLOY_AVD_LABEL%
"%ADB%" install -r "build\app\outputs\flutter-apk\app-debug.apk"
if errorlevel 1 (
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

rem ====================== Deploy emulator (phone) ======================
:deploy_emulator
set DEPLOY_AVD_NAME=%AVD_NAME%
set DEPLOY_AVD_LABEL=emulator
set DEPLOY_WAIT_LABEL=Android Emulator
set DEPLOY_FINISH_MSG=Deploy finished!
call :deploy_avd_common
pause
exit /b 0

rem ====================== Full start (backend + phone) ======================
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

rem ====================== Build PC exe ======================
:build_exe
echo.
echo [PC Exe] Step 1/4: Clean old builds
cd /d "%ROOT_DIR%"
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"

echo [PC Exe] Step 2/4: Build frontend
cd /d "%ROOT_DIR%\frontend"
call npm run build
if errorlevel 1 (
    echo ERROR: Frontend build failed
    pause
    exit /b 1
)

echo [PC Exe] Step 3/4: Run PyInstaller
cd /d "%ROOT_DIR%"
call pyinstaller BlurArc.spec --noconfirm
if errorlevel 1 (
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

rem ====================== Deploy tablet emulator ======================
:deploy_tablet_emulator
set DEPLOY_AVD_NAME=%AVD_TABLET_NAME%
set DEPLOY_AVD_LABEL=tablet emulator
set DEPLOY_AVD_SKIN=1280x800
set DEPLOY_WAIT_LABEL=Android Tablet Emulator
set DEPLOY_FINISH_MSG=Deploy to tablet finished!
call :deploy_avd_common
pause
exit /b 0

rem ====================== Hot run phone emulator ======================
:hotrun_emulator
call :run_pc_app_core
if errorlevel 1 (
    echo [Hot run] PC 端启动失败，已中止
    pause
    exit /b 1
)
echo.
set DEPLOY_AVD_NAME=%AVD_NAME%
set DEPLOY_AVD_LABEL=phone emulator
set DEPLOY_AVD_SKIN=
set DEPLOY_WAIT_LABEL=Android Emulator
set DEPLOY_HOT=1
call :deploy_avd_common
exit /b 0

rem ====================== Hot run tablet emulator ======================
:hotrun_tablet_emulator
call :run_pc_app_core
if errorlevel 1 (
    echo [Hot run] PC 端启动失败，已中止
    pause
    exit /b 1
)
echo.
set DEPLOY_AVD_NAME=%AVD_TABLET_NAME%
set DEPLOY_AVD_LABEL=tablet emulator
set DEPLOY_AVD_SKIN=1280x800
set DEPLOY_WAIT_LABEL=Android Tablet Emulator
set DEPLOY_HOT=1
call :deploy_avd_common
exit /b 0

rem ====================== Run PC app core ======================
rem Shared by hotrun_emulator, hotrun_tablet_emulator, and run_pc_app.
rem Exits with /b 1 on failure, /b 0 on success.
:run_pc_app_core
if not exist "%PYTHON%" (
    echo ERROR: Python not found: %PYTHON%
    exit /b 1
)
if not exist "%ROOT_DIR%\frontend\package.json" (
    echo ERROR: frontend/package.json not found: %ROOT_DIR%\frontend
    exit /b 1
)
if not exist "%ROOT_DIR%\src\BlurArc.py" (
    echo ERROR: src/BlurArc.py not found: %ROOT_DIR%\src
    exit /b 1
)

echo [PC App] Step 1/2: Build frontend (npm run build)
cd /d "%ROOT_DIR%\frontend"
call npm run build
if errorlevel 1 (
    echo ERROR: Frontend build failed
    exit /b 1
)

echo [PC App] Step 2/2: Launch BlurArc.py
cd /d "%ROOT_DIR%"
start "BlurArc" "%PYTHON%" "%ROOT_DIR%\src\BlurArc.py"
echo PC app launched.
exit /b 0

rem ====================== Run PC app (menu entry) ======================
:run_pc_app
echo.
call :run_pc_app_core
if errorlevel 1 (
    pause
    exit /b 1
)
echo.
pause
exit /b 0

rem ====================== View backend log ======================
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
