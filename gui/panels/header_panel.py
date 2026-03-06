"""头部信息面板：账户、余额、赛事信息"""
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont

from config.settings import HIGHLIGHT_DURATION_MS


class HeaderPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self._timers = {}
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        bold = QFont()
        bold.setBold(True)
        bold.setPointSize(12)

        self._account = QLabel("账户: --")
        self._account.setFont(bold)
        layout.addWidget(self._account)

        self._sep1 = self._add_sep(layout)

        self._balance = QLabel("信用余额: --")
        self._balance.setFont(bold)
        layout.addWidget(self._balance)

        self._sep2 = self._add_sep(layout)

        self._race = QLabel("赛事: --")
        self._race.setFont(bold)
        layout.addWidget(self._race)

        layout.addStretch()

    def _add_sep(self, layout):
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep)
        return sep

    def update_header(self, header, changes=None):
        self._account.setText(f"账户: {header.account_name}")
        self._balance.setText(f"信用余额: {header.credit_balance}")
        self._race.setText(f"赛事: {header.race_location} 场{header.race_number}")

        if changes:
            if "credit_balance" in changes:
                self._flash(self._balance, "credit_balance")

    def _flash(self, label, key):
        label.setStyleSheet("background-color: #FFFF00; padding: 2px;")
        if key in self._timers:
            self._timers[key].stop()
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: label.setStyleSheet(""))
        timer.start(HIGHLIGHT_DURATION_MS)
        self._timers[key] = timer
