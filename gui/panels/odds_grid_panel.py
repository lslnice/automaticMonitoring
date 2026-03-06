"""赔率网格面板（预留，当前主要聚焦交易监控）"""
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtGui import QFont


class OddsGridPanel(QFrame):
    """赔率网格面板 — 预留扩展"""

    def __init__(self, title="赔率", parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(self)

        title_label = QLabel(title)
        title_font = QFont()
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        self._placeholder = QLabel("（赔率网格预留区域）")
        layout.addWidget(self._placeholder)
        layout.addStretch()
