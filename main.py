"""赛马实时监控系统 — 入口"""
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from gui.main_window import MainWindow




def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")

    # 强制白色模式
    from PySide6.QtGui import QPalette, QColor
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(255, 255, 255))
    palette.setColor(QPalette.WindowText, QColor(0, 0, 0))
    palette.setColor(QPalette.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.AlternateBase, QColor(245, 245, 245))
    palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
    palette.setColor(QPalette.ToolTipText, QColor(0, 0, 0))
    palette.setColor(QPalette.Text, QColor(0, 0, 0))
    palette.setColor(QPalette.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ButtonText, QColor(0, 0, 0))
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Link, QColor(0, 120, 215))
    palette.setColor(QPalette.Highlight, QColor(0, 120, 215))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.Light, QColor(255, 255, 255))
    palette.setColor(QPalette.Midlight, QColor(227, 227, 227))
    palette.setColor(QPalette.Dark, QColor(160, 160, 160))
    palette.setColor(QPalette.Mid, QColor(200, 200, 200))
    palette.setColor(QPalette.Shadow, QColor(105, 105, 105))
    app.setPalette(palette)

    try:
        window = MainWindow()
        window.show()
    except Exception:
        import traceback
        QMessageBox.critical(None, "启动失败", traceback.format_exc())
        sys.exit(1)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
