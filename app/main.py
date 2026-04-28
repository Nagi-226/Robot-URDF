from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.window import MainWindow


APP_TITLE = "Robot URDF Studio"


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    window = MainWindow()
    window.show()
    return app.exec()
