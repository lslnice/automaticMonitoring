"""
浏览器工作线程：QThread + asyncio + Playwright
策略：用 JS 递归采集所有 frame 文本 → Python 解析
每 500ms 轮询（实时）
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

# 递归采集所有 frame 文本的 JS（同源时可跨 frame 访问）
_JS_COLLECT_ALL = """() => {
    function collect(doc) {
        let t = '';
        try { t = doc.body ? doc.body.innerText : ''; } catch(e) {}
        try {
            const frames = doc.querySelectorAll('frame, iframe');
            for (const f of frames) {
                try {
                    const d = f.contentDocument || f.contentWindow.document;
                    if (d) t += '\\n' + collect(d);
                } catch(e) {}
            }
        } catch(e) {}
        return t;
    }
    return collect(document);
}"""


class BrowserWorker(QThread):

    status_changed = Signal(str)
    page_snapshot = Signal(int, object)
    data_changed = Signal(int, object, object)
    page_count_changed = Signal(int)
    debug_log = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop_requested = False
        self._loop = None

    def request_stop(self):
        self._stop_requested = True
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

    def run(self):
        self._stop_requested = False
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
            if not self._stop_requested:
                self.debug_log.emit("工作线程意外退出")
            self.status_changed.emit("stopped")

    async def _async_main(self):
        from playwright.async_api import async_playwright

        self.status_changed.emit("launching")
        os.makedirs(CHROME_USER_DATA_DIR, exist_ok=True)

        async with async_playwright() as pw:
            context = await pw.chromium.launch_persistent_context(
                user_data_dir=CHROME_USER_DATA_DIR,
                headless=False,
                channel="chrome",
                args=["--disable-blink-features=AutomationControlled"],
                viewport=None,
                no_viewport=True,
            )

            # 监听浏览器断开
            disconnected = False

            def on_close():
                nonlocal disconnected
                disconnected = True

            context.on("close", lambda: on_close())

            first_page = context.pages[0] if context.pages else await context.new_page()
            try:
                await first_page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=15000)
            except Exception:
                pass

            self.status_changed.emit("waiting_login")

            try:
                await self._monitor_loop(context)
            except Exception as e:
                if not disconnected:
                    self.debug_log.emit(f"监控主循环异常: {e}")
            finally:
                try:
                    if not disconnected:
                        await context.close()
                except Exception:
                    pass

    async def _monitor_loop(self, context):
        monitored = {}  # page -> state
        idx_counter = 0
        debug_done = set()
        consecutive_errors = 0

        while not self._stop_requested:
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
                        self.status_changed.emit("monitoring")

                self.page_count_changed.emit(len(monitored))

                if not monitored:
                    consecutive_errors = 0
                    await asyncio.sleep(PAGE_DETECT_INTERVAL_S)
                    continue

                # 实时轮询
                poll_ok = False
                for page, state in list(monitored.items()):
                    if self._stop_requested:
                        break
                    try:
                        if page.is_closed():
                            monitored.pop(page, None)
                            continue
                    except Exception:
                        monitored.pop(page, None)
                        continue

                    try:
                        # 在主 frame 上执行 JS，递归采集所有子 frame 文本
                        combined = await page.evaluate(_JS_COLLECT_ALL)

                        if not combined or len(combined) < 20:
                            continue

                        poll_ok = True

                        # 首次调试输出
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
                            # 页面导航中，重置debug标记以便下次重新输出
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
