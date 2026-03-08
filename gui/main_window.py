"""主窗口：交易监控 + 归类 + 一键发微信"""
import json
import ssl
import urllib.request

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStatusBar, QLineEdit,
    QRadioButton, QButtonGroup, QTextEdit, QGroupBox,
    QSplitter, QMessageBox,
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont

from core.browser_worker import BrowserWorker
from core.models import PageSnapshot
from core.trade_grouper import group_trades, format_message
from core.wechat_sender import send_to_wechat
from gui.panels.header_panel import HeaderPanel
from gui.panels.trades_panel import TradesPanel

SUFFIX_OPTIONS = ["正", "正负", "+-", "/", "W", "WP", "="]

STATUS_URL = "https://api.liveframe.cn/api/app/base/comm/systemStatus"


def check_remote_status() -> bool:
    """启动时检查远程开关，仅调用一次，不影响后续监控延迟"""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(STATUS_URL, method="GET")
        with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body.get("data") is True
    except Exception:
        return False

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("赛马实时监控")
        self.resize(1000, 700)
        self._worker = None
        self._page_snapshots = {}
        self._all_trades = {}  # horse_combo -> TradeRow（累积，只增不减）
        self._init_ui()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(6)

        # ── 工具栏 ──
        bar = QHBoxLayout()
        self._start_btn = QPushButton("Start")
        self._start_btn.setFixedWidth(80)
        self._start_btn.clicked.connect(self._on_start)
        bar.addWidget(self._start_btn)

        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setFixedWidth(80)
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._on_stop)
        bar.addWidget(self._stop_btn)

        self._status_label = QLabel("状态: 就绪")
        bar.addWidget(self._status_label)
        self._page_count_label = QLabel("监控页面: 0")
        bar.addWidget(self._page_count_label)
        bar.addStretch()
        root.addLayout(bar)

        # ── Header ──
        self._header_panel = HeaderPanel()
        root.addWidget(self._header_panel)

        # ── 左右分割：交易表 | 归类发送 ──
        splitter = QSplitter(Qt.Horizontal)

        self._trades_panel = TradesPanel("已证实交易（汇总）")
        splitter.addWidget(self._trades_panel)

        splitter.addWidget(self._build_send_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        root.addWidget(splitter, stretch=1)

        self.setStatusBar(QStatusBar())

    def _build_send_panel(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(8)

        # 归类预览
        gb = QGroupBox("归类结果")
        gbl = QVBoxLayout(gb)
        self._grouped_text = QTextEdit()
        self._grouped_text.setReadOnly(True)
        self._grouped_text.setFont(QFont("Menlo", 14))
        self._grouped_text.setPlaceholderText("等待数据...")
        self._grouped_text.setStyleSheet("QTextEdit{background:#FFFFFF;color:#000000;border:1px solid #CCC;}")
        gbl.addWidget(self._grouped_text)
        layout.addWidget(gb, stretch=1)

        # 后缀
        sb = QGroupBox("后缀")
        sl = QHBoxLayout(sb)
        self._suffix_group = QButtonGroup(self)
        for i, label in enumerate(SUFFIX_OPTIONS):
            rb = QRadioButton(label)
            self._suffix_group.addButton(rb, i)
            sl.addWidget(rb)
            if i == 0:
                rb.setChecked(True)
        layout.addWidget(sb)

        # 金额
        al = QHBoxLayout()
        al.addWidget(QLabel("金额:"))
        self._amount_input = QLineEdit()
        self._amount_input.setPlaceholderText("输入金额")
        self._amount_input.setFixedWidth(120)
        al.addWidget(self._amount_input)
        al.addStretch()
        layout.addLayout(al)

        # 预览
        layout.addWidget(QLabel("发送预览:"))
        self._preview_text = QTextEdit()
        self._preview_text.setReadOnly(True)
        self._preview_text.setFont(QFont("Menlo", 14))
        self._preview_text.setMaximumHeight(100)
        self._preview_text.setStyleSheet("QTextEdit{background:#FFFFFF;color:#000000;border:1px solid #CCC;}")
        layout.addWidget(self._preview_text)

        # 发送按钮
        self._send_btn = QPushButton("一键发送到微信")
        self._send_btn.setFixedHeight(40)
        f = QFont()
        f.setBold(True)
        f.setPointSize(13)
        self._send_btn.setFont(f)
        self._send_btn.setStyleSheet(
            "QPushButton{background:#07C160;color:white;border-radius:6px}"
            "QPushButton:hover{background:#06AD56}"
        )
        self._send_btn.clicked.connect(self._on_send)
        layout.addWidget(self._send_btn)

        # 测试发送按钮
        self._test_btn = QPushButton("测试微信")
        self._test_btn.setFixedHeight(24)
        self._test_btn.setStyleSheet(
            "QPushButton{background:#999;color:white;border-radius:4px;font-size:11px;padding:2px 8px}"
            "QPushButton:hover{background:#777}"
        )
        self._test_btn.clicked.connect(self._on_test_send)
        layout.addWidget(self._test_btn)

        # 信号 → 更新预览
        self._suffix_group.buttonClicked.connect(self._update_preview)
        self._amount_input.textChanged.connect(self._update_preview)

        return w

    # ──── 浏览器控制 ────

    def _ensure_worker(self):
        """确保 worker 线程存在（浏览器只打开一次）"""
        if self._worker is None:
            self._worker = BrowserWorker(self)
            self._worker.status_changed.connect(self._on_status)
            self._worker.page_snapshot.connect(self._on_snapshot)
            self._worker.data_changed.connect(self._on_changed)
            self._worker.page_count_changed.connect(
                lambda n: self._page_count_label.setText(f"监控页面: {n}")
            )
            self._worker.debug_log.connect(self._on_debug)

    @Slot()
    def _on_start(self):
        # 远程开关检查

        if not check_remote_status():
            QMessageBox.critical(self, "无法启动", "系统当前不可用，请联系管理员。")
            return
        # 清空上一场数据
        self._page_snapshots.clear()
        self._all_trades.clear()
        self._trades_panel.update_trades((), None)
        self._grouped_text.setPlainText("")
        self._preview_text.setPlainText("")

        self._ensure_worker()
        self._worker.start_monitoring()
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)

    @Slot()
    def _on_stop(self):
        """停止监控，清空数据，但保持浏览器打开"""
        if self._worker:
            self._worker.stop_monitoring()
        self._page_snapshots.clear()
        self._all_trades.clear()
        self._trades_panel.update_trades((), None)
        self._grouped_text.setPlainText("")
        self._preview_text.setPlainText("")
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._status_label.setText("状态: 已停止（浏览器保持打开）")

    # ──── 信号处理 ────

    @Slot(str)
    def _on_status(self, s):
        self._status_label.setText(f"状态: {s}")
        # 工作线程意外停止时，自动恢复按钮状态
        if s == "stopped" and self._worker and not self._stop_btn.isEnabled():
            return  # 用户手动停止的，忽略
        if s == "stopped":
            self._start_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)
        if s.startswith("error"):
            self._start_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)

    @Slot(int, object)
    def _on_snapshot(self, idx, snap):
        self._page_snapshots[idx] = snap
        self._refresh(None)

    @Slot(int, object, object)
    def _on_changed(self, idx, snap, changes):
        self._page_snapshots[idx] = snap
        self._refresh(changes)

    # ──── 合并 & 归类 ────

    def _refresh(self, changes):
        header = None

        # 累积所有交易（只增不减，防止页面刷新瞬间丢数据）
        for snap in self._page_snapshots.values():
            if snap.header.account_name:
                header = snap.header
            for t in snap.trades:
                if t.horse_combo not in self._all_trades:
                    self._all_trades[t.horse_combo] = t

        all_trades = list(self._all_trades.values())

        if header:
            hc = changes.get("header") if changes else None
            self._header_panel.update_header(header, hc)

        tc = changes.get("trades") if changes else None
        self._trades_panel.update_trades(tuple(all_trades), tc)

        # 归类
        combos = [t.horse_combo for t in all_trades]
        grouped = group_trades(combos)
        self._grouped_text.setPlainText("\n".join(grouped) if grouped else "")
        self._update_preview()

    def _update_preview(self):
        text = self._grouped_text.toPlainText().strip()
        if not text:
            self._preview_text.setPlainText("")
            return
        grouped = [l.strip() for l in text.split("\n") if l.strip()]
        btn = self._suffix_group.checkedButton()
        suffix = btn.text() if btn else ""
        amount = self._amount_input.text().strip()
        self._preview_text.setPlainText(format_message(grouped, suffix, amount))

    @Slot()
    def _on_test_send(self):
        if send_to_wechat("test"):
            self.statusBar().showMessage("测试发送成功", 3000)
        else:
            QMessageBox.warning(self, "测试失败", "请确认微信已打开且有聊天窗口")

    @Slot()
    def _on_send(self):
        msg = self._preview_text.toPlainText().strip()
        if not msg:
            QMessageBox.warning(self, "提示", "没有可发送的内容")
            return
        if send_to_wechat(msg):
            self.statusBar().showMessage("已发送到微信", 3000)
        else:
            QMessageBox.warning(self, "发送失败", "请确认微信已打开且有聊天窗口")

    @Slot(str)
    def _on_debug(self, msg):
        print(f"[DEBUG] {msg}")
        self.statusBar().showMessage(msg, 5000)

    def closeEvent(self, event):
        """关闭窗口时才关闭浏览器"""
        if self._worker:
            self._worker.close_browser()
            self._worker.wait(5000)
            self._worker = None
        event.accept()
