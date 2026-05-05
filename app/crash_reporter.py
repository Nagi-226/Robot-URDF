"""Crash log helper for packaging-ready desktop builds."""

from __future__ import annotations

import datetime as _dt
import sys
import traceback
from pathlib import Path

from config import CONFIG


def write_crash_log(exc_type, exc_value, exc_tb) -> Path | None:
    """Persist an unhandled exception traceback and return the log path."""
    try:
        crash_dir = Path(CONFIG.crash_log_dir)
        crash_dir.mkdir(parents=True, exist_ok=True)
        stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        path = crash_dir / f"crash-{stamp}.log"
        formatted = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        path.write_text(
            "\n".join([
                "Robot URDF Studio crash report",
                f"timestamp={_dt.datetime.now().isoformat(timespec='seconds')}",
                f"python={sys.version}",
                "",
                formatted,
            ]),
            encoding="utf-8",
        )
        return path
    except OSError:
        return None
