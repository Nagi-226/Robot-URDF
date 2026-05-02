"""File-system helpers for workspace project tree population."""

from __future__ import annotations

from pathlib import Path

PROJECT_HINTS = ["models", "assets", "configs", "logs", "firmware", "urdf"]


def populate_project_tree_hints(root: Path) -> dict[str, list[str]]:
    """Return a dict of folder→children for populating a project tree widget.

    Returns empty dict if root does not exist.
    """
    if not root.exists():
        return {}
    result: dict[str, list[str]] = {}
    for child in sorted(root.iterdir()):
        if child.is_dir() and child.name.lower() in PROJECT_HINTS:
            result[child.name] = [c.name for c in sorted(child.iterdir())][:20]
    return result
