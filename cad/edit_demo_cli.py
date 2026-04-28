from __future__ import annotations

from .edit_demo import run_edit_demo


def main() -> None:
    result = run_edit_demo()
    print(f"part={result.part_name}")
    print(f"handle={result.handle_name}")
    print(f"applied={result.applied}")
    print("[before-summary]")
    print(result.before_summary)
    print("[after-summary]")
    print(result.after_summary)
    print("[before-script]")
    print(result.before_script)
    print("[after-script]")
    print(result.after_script)


if __name__ == "__main__":
    main()
