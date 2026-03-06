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
echo [1/4] 安装依赖...
pip install PySide6 playwright pyinstaller -q
if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

REM 安装 Playwright Chromium 浏览器
echo [2/4] 安装 Chromium 浏览器...
python -m playwright install chromium
if errorlevel 1 (
    echo [警告] Chromium 安装可能失败，继续打包...
)

REM 打包
echo [3/4] 打包为 exe...
pyinstaller build_exe.spec --noconfirm
if errorlevel 1 (
    echo [错误] 打包失败
    pause
    exit /b 1
)

REM 复制 Playwright 浏览器到 dist 目录
echo [4/4] 复制 Playwright 浏览器驱动...
set PW_BROWSERS=%USERPROFILE%\AppData\Local\ms-playwright
if exist "%PW_BROWSERS%" (
    xcopy "%PW_BROWSERS%" "dist\赛马监控\playwright_browsers\" /E /I /Q /Y >nul
    echo     浏览器驱动已复制
) else (
    echo [警告] 未找到 Playwright 浏览器目录: %PW_BROWSERS%
    echo     用户需要手动执行: python -m playwright install chromium
)

echo.
echo ========================================
echo   打包完成！
echo   输出目录: dist\赛马监控\
echo   可执行文件: dist\赛马监控\赛马监控.exe
echo ========================================
echo.
pause
