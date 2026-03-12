#!/bin/bash
set -e

echo "========================================"
echo "  赛马监控 - macOS 一键打包"
echo "========================================"
echo ""

# 检查 Python
if ! python3 --version &>/dev/null; then
    echo "[错误] 未检测到 Python3，请先安装"
    exit 1
fi

# 安装依赖
echo "[1/5] 安装依赖..."
pip install -r requirements.txt -q
pip install pyinstaller -q

# 安装完整 Chromium
echo "[2/5] 安装 Playwright Chromium..."
python3 -m playwright install chromium

# 清理旧构建
echo "[3/5] 清理旧构建..."
rm -rf build dist

# 打包
echo "[4/5] PyInstaller 打包中..."
echo "    （首次打包较慢，请耐心等待）"
echo ""
pyinstaller --noconfirm --clean build_exe.spec

# 手动复制 Chromium 到 .app 内部（绕过 PyInstaller 签名问题）
echo "[5/5] 复制 Chromium 浏览器..."
CHROMIUM_SRC=$(find ~/Library/Caches/ms-playwright -maxdepth 1 -name "chromium-*" -type d | sort -r | head -1)
if [ -z "$CHROMIUM_SRC" ]; then
    echo "[错误] 未找到 Chromium，请执行: python3 -m playwright install chromium"
    exit 1
fi
CHROMIUM_NAME=$(basename "$CHROMIUM_SRC")

# 复制到 .app 包内的 Resources 目录
APP_RESOURCES="dist/赛马监控.app/Contents/Resources/playwright_browsers/$CHROMIUM_NAME"
mkdir -p "$APP_RESOURCES"
cp -R "$CHROMIUM_SRC/" "$APP_RESOURCES/"
echo "    已复制到 .app: $APP_RESOURCES"

# 同时复制到文件夹版本（备用）
FOLDER_DEST="dist/赛马监控/playwright_browsers/$CHROMIUM_NAME"
mkdir -p "$FOLDER_DEST"
cp -R "$CHROMIUM_SRC/" "$FOLDER_DEST/"

echo ""
echo "========================================"
echo "  打包成功！"
echo "  .app 文件: dist/赛马监控.app"
echo "  文件夹版:  dist/赛马监控/"
echo ""
echo "  分发时压缩 .app:"
echo "    cd dist && zip -r 赛马监控_mac.zip 赛马监控.app"
echo "========================================"
