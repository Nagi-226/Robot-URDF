"""Optional release version check used by packaged builds."""

from __future__ import annotations

import json
import re
import urllib.request


_VERSION_RE = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")


def version_tuple(version: str) -> tuple[int, int, int]:
    match = _VERSION_RE.search(version)
    if not match:
        return (0, 0, 0)
    return tuple(int(part) for part in match.groups())


def is_newer_version(candidate: str, current: str) -> bool:
    return version_tuple(candidate) > version_tuple(current)


def fetch_latest_release_tag(api_url: str, timeout: float = 2.0) -> str | None:
    """Return a GitHub-style latest release tag, or None on any failure."""
    try:
        request = urllib.request.Request(
            api_url,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "RobotURDFStudio"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None
    tag = data.get("tag_name") if isinstance(data, dict) else None
    return str(tag) if tag else None
