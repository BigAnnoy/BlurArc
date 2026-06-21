# BlurArc 开发工具脚本
# 用法：
#   .\scripts\dev-start.ps1 backend    # 仅重启后端
#   .\scripts\dev-start.ps1 phone      # 构建 APK 并安装到手机（USB）
#   .\scripts\dev-start.ps1 emulator   # 构建 APK 并安装到模拟器
#   .\scripts\dev-start.ps1 all        # 后端 + 部署到手机（默认）
#   .\scripts\dev-start.ps1 log        # 实时跟踪后端日志
#   .\scripts\dev-start.ps1 log -n 30  # 查看最新 30 行
#   .\scripts\dev-start.ps1 build-exe  # 构建 PC exe

param(
    [ValidateSet("backend", "phone", "emulator", "all", "log", "build-exe")]
    [string]$Action = "all",
    [int]$n = 50    # log 模式显示的行数
)

$ErrorActionPreference = "Stop"

# ── 路径常量 ─────────────────────────────
$ProjectRoot  = "F:\AI\Frame_Album"
$BackendLog   = "$ProjectRoot\backend.log"
$FlutterBin   = "E:\Applications\flutter\bin\flutter.bat"
$PythonBin    = "E:\Applications\anaconda_base\python.exe"
$AdbBin       = "C:\Users\BIGANNOY\AppData\Local\Android\Sdk\platform-tools\adb.exe"
$ApkPath      = "$ProjectRoot\blurarc_app\build\app\outputs\flutter-apk\app-debug.apk"
$AppPackage   = "com.example.blurarc_app"
$PubCache     = "$ProjectRoot\.pub_cache"

# ── 辅助函数 ─────────────────────────────
function Write-Step([string]$msg) {
    Write-Host "  ► $msg" -ForegroundColor Cyan
}
function Write-Ok([string]$msg) {
    Write-Host "  ✓ $msg" -ForegroundColor Green
}
function Write-Fail([string]$msg) {
    Write-Host "  ✗ $msg" -ForegroundColor Red
}

# ── 启动后端 ──────────────────────────────
function Start-Backend {
    Write-Host ""
    Write-Host "[ 后端 ]" -ForegroundColor Yellow

    Write-Step "停止旧进程（port 5000）..."
    $pids = netstat -ano | Select-String ":5000 " | Select-String "LISTENING" |
            ForEach-Object { ($_ -split "\s+")[-1] }
    foreach ($pid in $pids) {
        try { Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue } catch {}
    }
    Start-Sleep -Seconds 1

    Write-Step "启动 Flask 后端..."
    Set-Location $ProjectRoot
    $proc = Start-Process -FilePath $PythonBin `
        -ArgumentList "-m backend.api_server" `
        -WorkingDirectory $ProjectRoot `
        -RedirectStandardOutput $BackendLog `
        -RedirectStandardError $BackendLog `
        -WindowStyle Hidden `
        -PassThru
    Start-Sleep -Seconds 4

    # 健康检查
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:5000/api/health" -TimeoutSec 3 -UseBasicParsing
        if ($r.StatusCode -eq 200) {
            Write-Ok "后端启动成功（PID $($proc.Id)）→ http://0.0.0.0:5000"
        }
    } catch {
        Write-Fail "后端健康检查失败，查看日志："
        Write-Host "    $BackendLog" -ForegroundColor Gray
    }
}

# ── 构建 APK ──────────────────────────────
function Build-Apk {
    Write-Step "构建 debug APK..."
    $env:PUB_CACHE = $PubCache
    Set-Location "$ProjectRoot\blurarc_app"
    & $FlutterBin build apk --debug
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "APK 构建失败！"
        exit 1
    }
    Write-Ok "APK 构建完成"
}

# ── 部署到手机 ────────────────────────────
function Deploy-Phone {
    Write-Host ""
    Write-Host "[ 手机 ]" -ForegroundColor Yellow

    Write-Step "检查 USB 设备连接..."
    $devices = & $AdbBin devices 2>$null | Select-String -NotMatch "List|emulator" | Where-Object { $_ -match "device$" }
    if (-not $devices) {
        Write-Fail "未检测到手机！请检查 USB 连接并开启开发者选项 / USB 调试。"
        exit 1
    }
    Write-Ok "手机已连接"

    Build-Apk

    Write-Step "安装 APK 到手机..."
    & $AdbBin install -r $ApkPath
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "APK 安装失败！"
        exit 1
    }
    Write-Ok "安装成功"

    Write-Step "启动 App..."
    & $AdbBin shell am start -n "$AppPackage/.MainActivity" >$null
    Write-Ok "App 已启动"
}

# ── 部署到模拟器 ──────────────────────────
function Deploy-Emulator {
    Write-Host ""
    Write-Host "[ 模拟器 ]" -ForegroundColor Yellow

    Write-Step "检查模拟器连接..."
    $devices = & $AdbBin devices 2>$null | Select-String "emulator"
    if (-not $devices) {
        Write-Fail "未找到模拟器！请先在 Android Studio 中启动模拟器。"
        exit 1
    }
    Write-Ok "模拟器已连接"

    Build-Apk

    Write-Step "安装 APK 到模拟器..."
    & $AdbBin install -r $ApkPath
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "APK 安装失败！"
        exit 1
    }
    Write-Ok "安装成功"

    Write-Step "启动 App..."
    & $AdbBin shell am start -n "$AppPackage/.MainActivity" >$null
    Write-Ok "App 已启动"
}

# ── 查看日志 ──────────────────────────────
function Show-Log {
    Write-Host ""
    Write-Host "[ 后端日志 — 最新 $n 行 ]" -ForegroundColor Yellow
    Write-Host "─" * 50 -ForegroundColor Gray
    if (Test-Path $BackendLog) {
        Get-Content $BackendLog -Tail $n
    } else {
        Write-Fail "日志文件不存在：$BackendLog"
    }
}

# ── 构建 PC exe ─────────────────────────
function Build-Exe {
    Write-Host ""
    Write-Host "[ PC Exe ]" -ForegroundColor Yellow

    Write-Step "Step 1/4: 清理旧构建..."
    $distDir = "$ProjectRoot\dist"
    $buildDir = "$ProjectRoot\build"
    if (Test-Path $distDir) { Remove-Item -Recurse -Force $distDir }
    if (Test-Path $buildDir) { Remove-Item -Recurse -Force $buildDir }
    Write-Ok "清理完成"

    Write-Step "Step 2/4: 构建前端..."
    Set-Location "$ProjectRoot\frontend"
    npm run build
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "前端构建失败！"
        exit 1
    }
    Write-Ok "前端构建完成"

    Write-Step "Step 3/4: 运行 PyInstaller..."
    Set-Location $ProjectRoot
    pyinstaller BlurArc.spec --noconfirm
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "PyInstaller 构建失败！"
        exit 1
    }
    Write-Ok "PyInstaller 构建完成"

    Write-Step "Step 4/4: 验证输出..."
    $exePath = "$ProjectRoot\dist\BlurArc\BlurArc.exe"
    if (-not (Test-Path $exePath)) {
        Write-Fail "BlurArc.exe 未生成！"
        exit 1
    }
    $len = (Get-Item $exePath).Length
    Write-Ok "构建成功！"
    Write-Host "    输出: dist\BlurArc\" -ForegroundColor Gray
    Write-Host "    BlurArc.exe: $($len.ToString('N0')) bytes" -ForegroundColor Gray
}

# ── 入口 ─────────────────────────────────
Write-Host ""
Write-Host "  BlurArc Dev Tools" -ForegroundColor Magenta
Write-Host "  ─────────────────" -ForegroundColor DarkGray

switch ($Action) {
    "backend"   { Start-Backend }
    "phone"     { Deploy-Phone }
    "emulator"  { Deploy-Emulator }
    "all"       { Start-Backend; Deploy-Phone }
    "log"       { Show-Log }
    "build-exe" { Build-Exe }
}

Write-Host ""
