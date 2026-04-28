from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CadConvention:
    handle_prefix: str = "@cad"
    handle_separator: str = ":"
    comment_prefix: str = "#"

    def format_handle_comment(self, handle_name: str, selector: str, notes: str = "") -> str:
        suffix = f"  # {notes}" if notes else ""
        return f"{self.comment_prefix} {self.handle_prefix}{self.handle_separator} {handle_name} -> {selector}{suffix}"
