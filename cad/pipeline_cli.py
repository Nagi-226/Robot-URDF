from __future__ import annotations

import argparse
from pathlib import Path

from .demo import build_demo_manifest
from .pipeline import CadRunwayPipeline
from .writer_registry import WriterRegistry


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the CAD runway pipeline")
    parser.add_argument("--write", action="store_true", help="write placeholder artifacts to disk")
    parser.add_argument("--writer", default="placeholder", help="writer name: placeholder or cadquery")
    parser.add_argument("--out", default="exports", help="output root directory")
    args = parser.parse_args()

    registry = WriterRegistry()
    writer = registry.get(args.writer)
    pipeline = CadRunwayPipeline(
        output_root=Path(args.out),
        write_placeholders=args.write,
        writer=writer,
    )
    result = pipeline.run(build_demo_manifest())
    print(result.report)
    print(f"writer={result.writer_name}")
    print(f"written_artifacts={len(result.written_artifacts)}")


if __name__ == "__main__":
    main()
