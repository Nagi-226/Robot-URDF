"""Small JSON persistence helper for 3D viewport state."""

from __future__ import annotations

import json
from pathlib import Path


STATE_PATH = Path(".robot_urdf_viewport_state.json")


def load_viewport_state(path: str | Path = STATE_PATH) -> dict:
    state_path = Path(path)
    if not state_path.is_file():
        return {}
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_viewport_state(state: dict, path: str | Path = STATE_PATH) -> None:
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    safe_state = {
        "azimuth": float(state.get("azimuth", 45.0)),
        "elevation": float(state.get("elevation", 25.0)),
        "distance": float(state.get("distance", 1.0)),
        "wireframe": bool(state.get("wireframe", False)),
        "highlighted_item": str(state.get("highlighted_item", "")),
    }
    state_path.write_text(json.dumps(safe_state, indent=2), encoding="utf-8")
