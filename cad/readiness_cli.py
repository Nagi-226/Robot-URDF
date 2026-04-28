from __future__ import annotations

from .readiness import check_v043_readiness


def main() -> None:
    print(check_v043_readiness().render())


if __name__ == "__main__":
    main()
