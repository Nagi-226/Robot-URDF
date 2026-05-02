from __future__ import annotations

import sys
import traceback

from PySide6.QtWidgets import QApplication, QMessageBox

from app.window import MainWindow


APP_TITLE = "Robot URDF Studio"


def _excepthook(exc_type, exc_value, exc_tb):
    formatted = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(formatted, file=sys.stderr)
    if QApplication.instance() is not None:
        QMessageBox.critical(None, "Unexpected Error", formatted)


def main() -> int:
    sys.excepthook = _excepthook
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    window = MainWindow()
    window.show()
    return app.exec()
