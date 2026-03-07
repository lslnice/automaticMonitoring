"""
一键发送文本到微信当前聊天窗口
跨平台：macOS (osascript) / Windows (ctypes Win32 API)
前提：用户已打开微信并停留在目标聊天窗口
"""
import platform
import subprocess
import time

SYSTEM = platform.system()


def send_to_wechat(text: str) -> bool:
    """复制到剪贴板 → 切到微信 → 粘贴 → 回车发送"""
    try:
        if SYSTEM == "Darwin":
            return _send_macos(text)
        elif SYSTEM == "Windows":
            return _send_windows(text)
        else:
            print(f"[WeChat] 不支持的系统: {SYSTEM}")
            return False
    except Exception as e:
        print(f"[WeChat] 发送失败: {e}")
        return False


# ========== macOS ==========

def _send_macos(text: str) -> bool:
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True, timeout=5)

    applescript = '''
    tell application "System Events"
        set frontmost of process "WeChat" to true
        delay 0.3
        keystroke "v" using command down
        delay 0.15
        key code 36
    end tell
    '''
    result = subprocess.run(
        ["osascript", "-e", applescript],
        capture_output=True, text=True, timeout=10,
    )
    return result.returncode == 0


# ========== Windows ==========

def _send_windows(text: str) -> bool:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    # 1. 复制到剪贴板
    _clipboard_set_text(user32, kernel32, text)

    # 2. 找到微信窗口并切到前台
    hwnd = user32.FindWindowW("WeChatMainWndForPC", None)
    if not hwnd:
        # 备用：按窗口标题找
        hwnd = user32.FindWindowW(None, "微信")
    if not hwnd:
        print("[WeChat] 找不到微信窗口")
        return False

    user32.SetForegroundWindow(hwnd)
    time.sleep(0.3)

    # 3. Ctrl+V 粘贴
    VK_CONTROL = 0x11
    VK_V = 0x56
    VK_RETURN = 0x0D
    KEYEVENTF_KEYUP = 0x0002

    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_V, 0, 0, 0)
    user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

    time.sleep(0.15)

    # 4. Enter 发送
    user32.keybd_event(VK_RETURN, 0, 0, 0)
    user32.keybd_event(VK_RETURN, 0, KEYEVENTF_KEYUP, 0)

    return True


def _clipboard_set_text(user32, kernel32, text: str):
    """用 Win32 API 设置剪贴板文本（支持中文）"""
    import ctypes

    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002

    data = text.encode("utf-16le") + b"\x00\x00"

    user32.OpenClipboard(0)
    user32.EmptyClipboard()

    h = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
    p = kernel32.GlobalLock(h)
    ctypes.memmove(p, data, len(data))
    kernel32.GlobalUnlock(h)

    user32.SetClipboardData(CF_UNICODETEXT, h)
    user32.CloseClipboard()
