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
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# ---- 项目根目录 ----
PROJ_DIR = os.path.abspath(SPECPATH)

# ---- Playwright 浏览器驱动数据 ----
# Playwright 需要浏览器二进制文件，打包后通过环境变量指定路径
# 用户需要先执行: python -m playwright install chromium
playwright_datas = collect_data_files("playwright")

# ---- 主分析 ----
a = Analysis(
    [os.path.join(PROJ_DIR, "main.py")],
    pathex=[PROJ_DIR],
    binaries=[],
    datas=[
        *playwright_datas,
    ],
    hiddenimports=[
        # Playwright 内部模块
        "playwright",
        "playwright.sync_api",
        "playwright.async_api",
        "playwright._impl",
        "playwright._impl._api_types",
        "playwright._impl._connection",
        "playwright._impl._driver",
        "playwright._impl._transport",
        *collect_submodules("playwright"),
        # PySide6
        "PySide6.QtCore",
        "PySide6.QtWidgets",
        "PySide6.QtGui",
        # greenlet（Playwright 依赖）
        "greenlet",
        # 项目模块
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
        "gui.panels.odds_grid_panel",
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
    console=True,  # True 保留控制台窗口方便看调试日志，发布时可改 False
    icon=None,      # 可替换为 .ico 图标路径
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
