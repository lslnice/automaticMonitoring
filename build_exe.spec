# -*- mode: python ; coding: utf-8 -*-
"""
赛马实时监控 — PyInstaller 打包配置
用法（在 Windows 上执行）：
    pip install pyinstaller
    pyinstaller build_exe.spec
生成目录：dist/赛马监控/赛马监控.exe
"""

import sys
import os
import glob
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# ---- 项目根目录 ----
PROJ_DIR = os.path.abspath(SPECPATH)

# ---- Playwright 驱动数据 ----
playwright_datas = collect_data_files("playwright")

# ---- 只打包 Chromium 浏览器（跳过 firefox / webkit） ----
browser_datas = []
_pw_candidates = [
    os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "ms-playwright"),
    os.path.join(os.path.expanduser("~"), "Library", "Caches", "ms-playwright"),
]
for _pw_root in _pw_candidates:
    if not os.path.isdir(_pw_root):
        continue
    # 找 chromium-* 目录
    for d in sorted(glob.glob(os.path.join(_pw_root, "chromium*")), reverse=True):
        if os.path.isdir(d):
            dirname = os.path.basename(d)
            browser_datas.append((d, os.path.join("playwright_browsers", dirname)))
            print(f"[spec] 打包 Chromium: {d}")
            break
    break

# ---- 主分析 ----
a = Analysis(
    [os.path.join(PROJ_DIR, "main.py")],
    pathex=[PROJ_DIR],
    binaries=[],
    datas=[
        *playwright_datas,
        *browser_datas,
    ],
    hiddenimports=[
        "playwright",
        "playwright.sync_api",
        "playwright.async_api",
        "playwright._impl",
        "playwright._impl._api_types",
        "playwright._impl._connection",
        "playwright._impl._driver",
        "playwright._impl._transport",
        *collect_submodules("playwright"),
        "PySide6.QtCore",
        "PySide6.QtWidgets",
        "PySide6.QtGui",
        "greenlet",
        "core",
        "core.browser_worker",
        "core.change_detector",
        "core.models",
        "core.text_parser",
        "core.trade_grouper",
        "core.wechat_sender",
        "config",
        "config.settings",
        "gui",
        "gui.main_window",
        "gui.panels",
        "gui.panels.header_panel",
        "gui.panels.trades_panel",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter", "matplotlib", "numpy", "pandas",
        "scipy", "PIL", "cv2", "torch",
    ],
    noarchive=False,
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
    upx=True,
    console=False,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="赛马监控",
)
