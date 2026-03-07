"""
一键发送文本到微信当前聊天窗口
跨平台：macOS (osascript) / Windows (clip + ctypes)
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

    user32 = ctypes.windll.user32

    # 1. 用 PowerShell 设置剪贴板（稳定支持中文）
    _clipboard_set_text_ps(text)

    # 2. 找到微信窗口并切到前台
    hwnd = user32.FindWindowW("WeChatMainWndForPC", None)
    if not hwnd:
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


def _clipboard_set_text_ps(text: str):
    """用 PowerShell Set-Clipboard 设置剪贴板（稳定支持中文）"""
    # 转义文本中的单引号
    escaped = text.replace("'", "''")
    cmd = f"Set-Clipboard -Value '{escaped}'"
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", cmd],
        check=True, timeout=5,
        creationflags=0x08000000,  # CREATE_NO_WINDOW
    )
