"""
浏览器工作线程：QThread + asyncio + Playwright
浏览器生命周期独立于监控：
  - 首次 Start 打开浏览器并开始监控
  - Stop 仅停止监控、清空数据，浏览器保持打开
  - 再次 Start 复用已有浏览器，重新开始监控
  - 关闭窗口时才关闭浏览器
"""
import asyncio
import time
import os

from PySide6.QtCore import QThread, Signal

from core.models import PageSnapshot
from core.text_parser import parse_page_text
from core.change_detector import detect_changes
from config.settings import (
    CHROME_USER_DATA_DIR,
    TARGET_DOMAIN,
    TARGET_URL,
    PAGE_DETECT_INTERVAL_S,
    POLL_INTERVAL_S,
)

# 单frame文本提取JS
_JS_GET_TEXT = "() => document.body ? document.body.innerText : ''"


class BrowserWorker(QThread):
    """持久浏览器工作线程，监控可反复启停"""

    status_changed = Signal(str)
    page_snapshot = Signal(int, object)
    data_changed = Signal(int, object, object)
    page_count_changed = Signal(int)
    debug_log = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._monitoring = False       # 是否正在监控
        self._close_browser = False    # 是否要关闭浏览器（仅退出时）
        self._loop = None
        self._monitor_event = None     # asyncio.Event 控制监控启停

    def start_monitoring(self):
        """开始监控（如果线程未运行则同时启动浏览器）"""
        self._monitoring = True
        self._close_browser = False
        if not self.isRunning():
            self.start()
        else:
            # 线程已在运行（浏览器已打开），通知恢复监控
            if self._loop and self._monitor_event:
                self._loop.call_soon_threadsafe(self._monitor_event.set)

    def stop_monitoring(self):
        """停止监控，但保持浏览器打开"""
        self._monitoring = False
        if self._loop and self._monitor_event:
            self._loop.call_soon_threadsafe(self._monitor_event.set)

    def close_browser(self):
        """关闭浏览器并退出线程（仅在关闭窗口时调用）"""
        self._monitoring = False
        self._close_browser = True
        if self._loop and self._monitor_event:
            self._loop.call_soon_threadsafe(self._monitor_event.set)

    @staticmethod
    def cleanup_lock():
        lock_file = os.path.join(CHROME_USER_DATA_DIR, "SingletonLock")
        try:
            if os.path.exists(lock_file) or os.path.islink(lock_file):
                os.remove(lock_file)
        except Exception:
            pass

    def run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._async_main())
        except Exception as e:
            msg = f"error: {e}"
            print(f"[BrowserWorker] {msg}")
            self.status_changed.emit(msg)
        finally:
            try:
                self._loop.close()
            except Exception:
                pass
            self._loop = None
            self.status_changed.emit("stopped")

    async def _async_main(self):
        from playwright.async_api import async_playwright

        self.status_changed.emit("launching")
        os.makedirs(CHROME_USER_DATA_DIR, exist_ok=True)
        self.cleanup_lock()

        self._monitor_event = asyncio.Event()

        async with async_playwright() as pw:
            context = await pw.chromium.launch_persistent_context(
                user_data_dir=CHROME_USER_DATA_DIR,
                headless=False,
                channel="chrome",
                args=["--disable-blink-features=AutomationControlled"],
                viewport=None,
                no_viewport=True,
            )

            disconnected = False

            def on_close():
                nonlocal disconnected
                disconnected = True
                # 浏览器被用户手动关闭，退出线程
                self._monitoring = False
                self._close_browser = True
                if self._monitor_event:
                    self._monitor_event.set()

            context.on("close", lambda: on_close())

            first_page = context.pages[0] if context.pages else await context.new_page()
            try:
                await first_page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=15000)
            except Exception:
                pass

            # 主循环：监控 ↔ 等待，直到 close_browser
            while not self._close_browser:
                if self._monitoring:
                    self.status_changed.emit("monitoring")
                    await self._monitor_loop(context)
                    # 监控结束（用户点了Stop），发出停止信号
                    if not self._close_browser:
                        self.status_changed.emit("stopped")
                        self.page_count_changed.emit(0)
                else:
                    # 等待下一次 start_monitoring 或 close_browser
                    self._monitor_event.clear()
                    await self._monitor_event.wait()

            # 关闭浏览器
            try:
                if not disconnected:
                    await context.close()
            except Exception:
                pass
            self.cleanup_lock()

    async def _monitor_loop(self, context):
        monitored = {}
        idx_counter = 0
        debug_done = set()
        consecutive_errors = 0

        while self._monitoring and not self._close_browser:
            try:
                # 发现目标页面
                target_pages = []
                try:
                    pages = context.pages
                except Exception as e:
                    self.debug_log.emit(f"获取页面列表失败: {e}")
                    consecutive_errors += 1
                    if consecutive_errors > 30:
                        self.debug_log.emit("连续错误过多，停止监控")
                        break
                    await asyncio.sleep(PAGE_DETECT_INTERVAL_S)
                    continue

                for page in pages:
                    try:
                        if page.is_closed():
                            continue
                        if TARGET_DOMAIN in page.url:
                            target_pages.append(page)
                    except Exception:
                        continue

                # 清理
                for p in list(monitored.keys()):
                    try:
                        if p.is_closed() or p not in target_pages:
                            monitored.pop(p, None)
                    except Exception:
                        monitored.pop(p, None)

                # 新增
                for page in target_pages:
                    if page not in monitored:
                        monitored[page] = {"snapshot": None, "index": idx_counter}
                        idx_counter += 1

                self.page_count_changed.emit(len(monitored))

                if not monitored:
                    consecutive_errors = 0
                    await asyncio.sleep(PAGE_DETECT_INTERVAL_S)
                    continue

                # 实时轮询
                poll_ok = False
                for page, state in list(monitored.items()):
                    if not self._monitoring:
                        break
                    try:
                        if page.is_closed():
                            monitored.pop(page, None)
                            continue
                    except Exception:
                        monitored.pop(page, None)
                        continue

                    try:
                        # 用 Playwright frame API 采集所有 frame 文本（含跨域）
                        parts = []
                        for frame in page.frames:
                            try:
                                t = await frame.evaluate(_JS_GET_TEXT)
                                if t and len(t.strip()) > 5:
                                    parts.append(t)
                            except Exception:
                                pass
                        combined = "\n".join(parts)

                        if not combined or len(combined) < 20:
                            continue

                        poll_ok = True

                        if page not in debug_done:
                            debug_done.add(page)
                            print(f"[页面{state['index']}] 递归采集文本长度={len(combined)}")
                            idx = combined.find("我的交易")
                            if idx != -1:
                                snippet = combined[idx:idx + 500]
                                print(f"['我的交易'附近500字]:\n{snippet}")
                            eat_lines = [l for l in combined.split("\n")
                                         if "吃" in l and len(l) < 200]
                            if eat_lines:
                                print(f"[含'吃'的行 前10条]:")
                                for el in eat_lines[:10]:
                                    print(f"  {el}")
                            if "已证实" in combined:
                                ci = combined.find("已证实")
                                print(f"['已证实'附近]:\n{combined[max(0,ci-30):ci+300]}")
                            print("=" * 60)

                        parsed = parse_page_text(combined)
                        new_snap = PageSnapshot(
                            header=parsed["header"],
                            trades=tuple(parsed["trades"]),
                            page_index=state["index"],
                            timestamp=time.time(),
                        )

                        old_snap = state["snapshot"]
                        if old_snap is None:
                            state["snapshot"] = new_snap
                            self.page_snapshot.emit(state["index"], new_snap)
                            self.debug_log.emit(
                                f"[首次] 页面{state['index']}: "
                                f"trades={len(parsed['trades'])}条 "
                                f"header={parsed['header'].account_name}"
                            )
                        else:
                            changes = detect_changes(old_snap, new_snap)
                            if changes:
                                state["snapshot"] = new_snap
                                self.data_changed.emit(state["index"], new_snap, changes)

                    except Exception as e:
                        err = str(e)
                        self.debug_log.emit(f"页面{state['index']}提取异常: {err[:100]}")
                        if "closed" in err.lower() or "crashed" in err.lower():
                            monitored.pop(page, None)
                            debug_done.discard(page)
                        elif "context" in err.lower() and "destroy" in err.lower():
                            debug_done.discard(page)

                if poll_ok:
                    consecutive_errors = 0
                else:
                    consecutive_errors += 1

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.debug_log.emit(f"监控循环异常: {e}")
                consecutive_errors += 1
                if consecutive_errors > 30:
                    self.debug_log.emit("连续错误过多，停止监控")
                    break

            await asyncio.sleep(POLL_INTERVAL_S)
