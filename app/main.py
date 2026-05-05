from __future__ import annotations

import sys
import traceback

from PySide6.QtWidgets import QApplication, QMessageBox

from app.crash_reporter import write_crash_log
from app.theme import ThemeManager
from app.window import MainWindow


APP_TITLE = "Robot URDF Studio"


def _excepthook(exc_type, exc_value, exc_tb):
    formatted = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(formatted, file=sys.stderr)
    log_path = write_crash_log(exc_type, exc_value, exc_tb)
    if QApplication.instance() is not None:
        suffix = f"\n\nCrash log: {log_path}" if log_path else ""
        QMessageBox.critical(None, "Unexpected Error", formatted + suffix)


def main() -> int:
    sys.excepthook = _excepthook
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    ThemeManager.instance().apply_to(app)
    window = MainWindow()
    window.show()
    return app.exec()
