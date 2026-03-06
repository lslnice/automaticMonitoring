@echo off
chcp 65001 >nul
echo ========================================
echo   赛马实时监控 - 一键打包
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

REM 安装依赖
echo [1/3] 安装依赖...
pip install PySide6 playwright pyinstaller -q
if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

REM 安装 Playwright Chromium 浏览器
echo [2/3] 安装 Chromium 浏览器...
python -m playwright install chromium
if errorlevel 1 (
    echo [警告] Chromium 安装可能失败，继续打包...
)

REM 打包（浏览器已通过 spec 自动打包进 dist）
echo [3/3] 打包为 exe（含 Chromium 浏览器）...
pyinstaller build_exe.spec --noconfirm
if errorlevel 1 (
    echo [错误] 打包失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo   打包完成！（Chromium 浏览器已内置）
echo   输出目录: dist\赛马监控\
echo   可执行文件: dist\赛马监控\赛马监控.exe
echo ========================================
echo.
pause
