"""常量配置 — 兼容开发环境和打包后的 exe"""
import os
import sys

# 判断是否在 PyInstaller 打包环境中
IS_FROZEN = getattr(sys, "frozen", False)
APP_DIR = os.path.dirname(sys.executable) if IS_FROZEN else os.path.dirname(os.path.abspath(__file__))

# Playwright 浏览器路径（打包后自动查找内置的浏览器）
if IS_FROZEN:
    _candidates = [
        os.path.join(os.path.dirname(sys.executable), "playwright_browsers"),
        os.path.join(getattr(sys, "_MEIPASS", ""), "playwright_browsers"),
    ]
    for _pw_browsers in _candidates:
        if os.path.isdir(_pw_browsers):
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = _pw_browsers
            break

# Chrome 用户数据目录（持久化登录状态）
CHROME_USER_DATA_DIR = os.path.join(os.path.expanduser("~"), ".ctbwp_chrome_profile")

# 目标网站
TARGET_DOMAIN = "ctbwp.com"
TARGET_URL = "https://www.ctbwp.com"

# 轮询间隔
POLL_INTERVAL_S = 0.2              # 实时轮询间隔（秒）— 200ms，肉眼无延迟
PAGE_DETECT_INTERVAL_S = 1.0       # 页面检测间隔（秒）

# GUI 高亮
HIGHLIGHT_DURATION_MS = 2000       # 单元格高亮持续时间（毫秒）
HIGHLIGHT_COLOR = "#FFFF00"        # 高亮颜色（黄色）
