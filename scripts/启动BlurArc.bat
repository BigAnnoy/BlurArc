@echo off
REM 启动 Blur Arc PyWebView 应用
REM 使用方法: 在命令行中运行此文件

echo ========================================
echo  Blur Arc - PyWebView 应用
echo ========================================
echo.

REM 检查 Python 是否已安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python
    echo 请先安装 Python 3.8+ 并将其添加到 PATH
    pause
    exit /b 1
)

echo 正在启动应用...
echo.

REM 运行应用
python "%~dp0..\src\BlurArc.py"

if errorlevel 1 (
    echo.
    echo 应用启动失败！
    echo 请检查错误消息并尝试以下操作：
    echo 1. 确保已安装所有依赖: pip install -r ..\requirements.txt
    echo 2. 确保相册路径已配置
    echo 3. 检查防火墙设置 (端口 5000)
    pause
    exit /b 1
)

exit /b 0
