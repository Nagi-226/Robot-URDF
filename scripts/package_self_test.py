"""Post-build smoke test for RobotURDFStudio.exe.

The script launches a packaged executable, waits briefly for it to stay alive,
then terminates it. It is intentionally conservative so CI can catch missing
DLL/data-file failures without requiring visual automation.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


def run_smoke_test(exe_path: Path, timeout_s: float = 8.0) -> int:
    if not exe_path.is_file():
        print(f"Executable not found: {exe_path}", file=sys.stderr)
        return 2

    proc = subprocess.Popen([str(exe_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        time.sleep(timeout_s)
        if proc.poll() is not None:
            stdout, stderr = proc.communicate(timeout=2)
            print(stdout.decode(errors="ignore"))
            print(stderr.decode(errors="ignore"), file=sys.stderr)
            return proc.returncode or 1
        return 0
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=4)
            except subprocess.TimeoutExpired:
                proc.kill()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("exe", nargs="?", default="dist/RobotURDFStudio.exe")
    parser.add_argument("--timeout", type=float, default=8.0)
    args = parser.parse_args()
    return run_smoke_test(Path(args.exe), args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
