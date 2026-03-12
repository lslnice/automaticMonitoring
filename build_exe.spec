# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

PROJECT_ROOT = Path.cwd()


def _resolve_chromium_dir() -> Path:
    """找到本机安装的完整 Chromium 目录（非 headless_shell）"""
    browsers_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if not browsers_path:
        if sys.platform == "win32":
            local_app_data = os.environ.get("LOCALAPPDATA", "")
            browsers_path = str(Path(local_app_data) / "ms-playwright") if local_app_data else ""
        else:
            browsers_path = str(Path.home() / "Library" / "Caches" / "ms-playwright")

    p_root = Path(browsers_path) if browsers_path else Path("")
    if not p_root.exists():
        raise SystemExit(f"[错误] Playwright 浏览器目录不存在: {p_root}\n请先执行: python -m playwright install chromium")

    chromium_dirs = sorted(p_root.glob("chromium-*"), reverse=True)
    if not chromium_dirs:
        raise SystemExit("[错误] 未找到完整 Chromium。\n请执行: python -m playwright install chromium")

    p = chromium_dirs[0]
    print(f"[spec] 打包 Chromium: {p}")
    return p


chromium_dir = _resolve_chromium_dir()

datas = [
    ("config", "config"),
    ("core", "core"),
    ("gui", "gui"),
    # Playwright Python 包自带的驱动数据
    *collect_data_files("playwright"),
]

# macOS 上 Chromium 是 .app 包，PyInstaller 签名会失败，改由 build_mac.sh 手动复制
# Windows 上直接打包进去
if sys.platform == "win32":
    datas.append((str(chromium_dir), f"playwright_browsers/{chromium_dir.name}"))
else:
    print(f"[spec] macOS: Chromium 将由 build_mac.sh 在打包后手动复制")

hiddenimports = [
    *collect_submodules("playwright"),
    "PySide6.QtCore",
    "PySide6.QtWidgets",
    "PySide6.QtGui",
    "greenlet",
]

a = Analysis(
    ["main.py"],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "pandas", "scipy", "PIL", "cv2", "torch"],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="赛马监控",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="赛马监控",
)

# macOS 生成 .app
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="赛马监控.app",
        bundle_identifier="com.saima.monitor",
    )
