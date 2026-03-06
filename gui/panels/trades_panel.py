"""交易面板：显示已证实交易的马号列表"""
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QAbstractItemView,
)
from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QBrush, QFont

from config.settings import HIGHLIGHT_DURATION_MS, HIGHLIGHT_COLOR


class TradesPanel(QFrame):
    """已证实交易表格"""

    def __init__(self, title="已证实交易", parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self._highlight_timers = []
        self._init_ui(title)

    def _init_ui(self, title: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        title_label = QLabel(title)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["场", "马号", "原始数据"])
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        layout.addWidget(self._table)

    def update_trades(self, trades: tuple, changes: dict | None = None):
        """更新交易列表"""
        self._table.setUpdatesEnabled(False)
        try:
            new_combos = changes.get("added", []) if changes else []

            self._table.setRowCount(len(trades))
            for i, trade in enumerate(trades):
                # 场
                item0 = QTableWidgetItem(trade.race)
                item0.setTextAlignment(Qt.AlignCenter)
                self._table.setItem(i, 0, item0)

                # 马号
                item1 = QTableWidgetItem(trade.horse_combo)
                item1.setTextAlignment(Qt.AlignCenter)
                combo_font = QFont()
                combo_font.setBold(True)
                combo_font.setPointSize(12)
                item1.setFont(combo_font)
                self._table.setItem(i, 1, item1)

                # 原始数据
                raw = " | ".join(trade.cells) if trade.cells else ""
                item2 = QTableWidgetItem(raw)
                self._table.setItem(i, 2, item2)

                # 新增行高亮
                if trade.horse_combo in new_combos:
                    highlight = QBrush(QColor(HIGHLIGHT_COLOR))
                    for col in range(3):
                        it = self._table.item(i, col)
                        if it:
                            it.setBackground(highlight)
                    self._schedule_reset(i)

        finally:
            self._table.setUpdatesEnabled(True)

    def _schedule_reset(self, row: int):
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda r=row: self._reset_row(r))
        timer.start(HIGHLIGHT_DURATION_MS)
        self._highlight_timers.append(timer)

    def _reset_row(self, row: int):
        white = QBrush(QColor("white"))
        for col in range(3):
            item = self._table.item(row, col)
            if item:
                item.setBackground(white)
