@echo off
chcp 65001 >nul
title 赛马监控 - 一键打包

echo ========================================
echo   赛马监控 - Windows 一键打包
echo ========================================
echo.

:: 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

:: 安装依赖
echo [1/4] 安装依赖...
pip install -r requirements.txt -q
pip install pyinstaller -q
if %errorlevel% neq 0 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

:: 安装完整 Chromium（非 headless_shell）
echo [2/4] 安装 Playwright Chromium...
python -m playwright install chromium
if %errorlevel% neq 0 (
    echo [错误] Chromium 安装失败
    pause
    exit /b 1
)

:: 清理旧构建
echo [3/4] 清理旧构建...
if exist build rd /s /q build
if exist dist rd /s /q dist

:: 打包
echo [4/4] PyInstaller 打包中...
echo    （首次打包较慢，请耐心等待）
echo.
pyinstaller --noconfirm --clean build_exe.spec
if %errorlevel% neq 0 (
    echo.
    echo [错误] 打包失败，请查看上方错误信息
    pause
    exit /b 1
)

echo.
echo ========================================
echo   打包成功！
echo   输出目录: dist\赛马监控\
echo   启动文件: dist\赛马监控\赛马监控.exe
echo   分发时将整个赛马监控文件夹打包为 zip
echo ========================================
echo.
pause
