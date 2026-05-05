"""Theme loading and persistence for the v0.7.x desktop shell."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from config import CONFIG


THEME_DIR = Path(__file__).resolve().parent.parent / "assets" / "themes"


@dataclass(frozen=True)
class ThemeDefinition:
    key: str
    label: str
    filename: str
    description: str


THEMES: tuple[ThemeDefinition, ...] = (
    ThemeDefinition(
        key="industrial_dark",
        label="Industrial Dark",
        filename="industrial_dark.qss",
        description="Dark industrial precision for the main engineering cockpit.",
    ),
    ThemeDefinition(
        key="high_contrast",
        label="High Contrast",
        filename="high_contrast.qss",
        description="Accessibility-oriented contrast for inspection and demos.",
    ),
    ThemeDefinition(
        key="compact",
        label="Compact",
        filename="compact.qss",
        description="Dense power-user layout with tighter spacing.",
    ),
)


_THEME_BY_KEY = {theme.key: theme for theme in THEMES}


class ThemeManager(QObject):
    """Loads QSS themes, applies them to Qt objects, and stores preference."""

    theme_changed = Signal(str)

    _instance: "ThemeManager | None" = None

    def __init__(self) -> None:
        if ThemeManager._instance is not None:
            raise RuntimeError("Use ThemeManager.instance()")
        super().__init__()
        self._theme_key = self._load_preference()
        ThemeManager._instance = self

    @classmethod
    def instance(cls) -> "ThemeManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def current_theme_key(self) -> str:
        return self._theme_key

    def available_themes(self) -> tuple[ThemeDefinition, ...]:
        return THEMES

    def load_qss(self, theme_key: str | None = None) -> str:
        key = self._normalise_key(theme_key or self._theme_key)
        theme = _THEME_BY_KEY[key]
        path = THEME_DIR / theme.filename
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            if key == CONFIG.default_theme:
                return ""
            return self.load_qss(CONFIG.default_theme)

    def apply_to(self, target, theme_key: str | None = None, persist: bool = True) -> str:
        key = self._normalise_key(theme_key or self._theme_key)
        qss = self.load_qss(key)
        if hasattr(target, "setStyleSheet"):
            target.setStyleSheet(qss)
        changed = key != self._theme_key
        self._theme_key = key
        if persist:
            self._save_preference(key)
        if changed:
            self.theme_changed.emit(key)
        return qss

    def set_theme(self, theme_key: str, target=None) -> str:
        key = self._normalise_key(theme_key)
        if target is None:
            from PySide6.QtWidgets import QApplication

            target = QApplication.instance()
        if target is None:
            self._theme_key = key
            self._save_preference(key)
            self.theme_changed.emit(key)
            return self.load_qss(key)
        return self.apply_to(target, key)

    @staticmethod
    def _normalise_key(theme_key: str) -> str:
        return theme_key if theme_key in _THEME_BY_KEY else CONFIG.default_theme

    def _load_preference(self) -> str:
        path = Path(CONFIG.preferences_path)
        if not path.is_file():
            return CONFIG.default_theme
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return CONFIG.default_theme
        key = str(data.get("theme", CONFIG.default_theme))
        return self._normalise_key(key)

    def _save_preference(self, theme_key: str) -> None:
        path = Path(CONFIG.preferences_path)
        data = {}
        if path.is_file():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    data.update(loaded)
            except (OSError, json.JSONDecodeError):
                data = {}
        data["theme"] = self._normalise_key(theme_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
