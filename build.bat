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

REM 只安装 Chromium（不装 firefox / webkit）
echo [2/4] 安装 Chromium 浏览器...
python -m playwright install chromium --with-deps
if errorlevel 1 (
    echo [警告] Chromium 安装可能失败，继续打包...
)

REM 打包
echo [3/4] 打包为 exe（仅含 Chromium）...
pyinstaller build_exe.spec --noconfirm
if errorlevel 1 (
    echo [错误] 打包失败
    pause
    exit /b 1
)

REM 显示打包大小
echo [4/4] 统计打包大小...
for /f "tokens=3" %%a in ('dir /s "dist\赛马监控" ^| findstr "个文件"') do set SIZE=%%a
echo   总大小: %SIZE% 字节

echo.
echo ========================================
echo   打包完成！（仅含 Chromium 浏览器）
echo   输出目录: dist\赛马监控\
echo   可执行文件: dist\赛马监控\赛马监控.exe
echo ========================================
echo.
pause
