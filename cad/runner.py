from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .workspace import workspace

_SAFE_BUILTINS: dict[str, object] = {
    "True": True,
    "False": False,
    "None": None,
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "range": range,
    "round": round,
    "set": set,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
    "print": print,
    "isinstance": isinstance,
    "math": __import__("math"),
}


@dataclass
class CadRunResult:
    script_name: str
    success: bool
    error: str = ""
    namespace: dict[str, object] = field(default_factory=dict)


@dataclass
class CadScriptRunner:
    def run_source(self, source: str, script_name: str = "<cad-script>") -> CadRunResult:
        namespace: dict[str, object] = {
            "__builtins__": _SAFE_BUILTINS,
            "workspace": workspace,
        }
        try:
            exec(compile(source, script_name, "exec"), namespace)
        except Exception as exc:  # noqa: BLE001
            return CadRunResult(script_name=script_name, success=False, error=str(exc))
        return CadRunResult(script_name=script_name, success=True, namespace=namespace)

    def run_file(self, path: Path) -> CadRunResult:
        try:
            source = path.read_text(encoding="utf-8")
        except OSError as exc:
            return CadRunResult(script_name=str(path), success=False, error=str(exc))
        return self.run_source(source, script_name=str(path))
