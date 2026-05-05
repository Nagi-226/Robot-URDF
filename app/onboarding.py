"""First-launch onboarding for packaged v0.7.x builds."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from app.theme import ThemeManager
from config import CONFIG
from i18n import I18nManager


def onboarding_complete() -> bool:
    path = Path(CONFIG.preferences_path)
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return bool(data.get("onboarding_complete", False))


def mark_onboarding_complete() -> None:
    path = Path(CONFIG.preferences_path)
    data = {}
    if path.is_file():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data.update(loaded)
        except (OSError, json.JSONDecodeError):
            data = {}
    data["onboarding_complete"] = True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


class OnboardingDialog(QDialog):
    """Minimal setup: language, theme, and optional sample robot load."""

    sample_requested = Signal(Path)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Robot URDF Studio Setup")
        self.setModal(False)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title = QLabel("First launch setup")
        title.setObjectName("BannerTitle")
        body = QLabel("Choose a working language and visual density. You can load the sample arm to verify 3D rendering immediately.")
        body.setWordWrap(True)
        body.setObjectName("CardBody")

        self.language = QComboBox()
        self.language.addItem("English", "en")
        self.language.addItem("中文", "zh")

        self.theme = QComboBox()
        for theme in ThemeManager.instance().available_themes():
            self.theme.addItem(theme.label, theme.key)

        button_row = QHBoxLayout()
        sample = QPushButton("Load Sample Model")
        skip = QPushButton("Skip")
        sample.clicked.connect(self._load_sample)
        skip.clicked.connect(self._finish)
        button_row.addWidget(sample)
        button_row.addWidget(skip)

        layout.addWidget(title)
        layout.addWidget(body)
        layout.addWidget(QLabel("Language"))
        layout.addWidget(self.language)
        layout.addWidget(QLabel("Theme"))
        layout.addWidget(self.theme)
        layout.addLayout(button_row)

    def _apply_choices(self) -> None:
        I18nManager.instance().set_language(str(self.language.currentData()))
        ThemeManager.instance().set_theme(str(self.theme.currentData()))

    def _load_sample(self) -> None:
        self._apply_choices()
        mark_onboarding_complete()
        self.sample_requested.emit(Path("models/simple_arm.urdf"))
        self.accept()

    def _finish(self) -> None:
        self._apply_choices()
        mark_onboarding_complete()
        self.accept()
