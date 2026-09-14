from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from build_manifest_from_harbor_tasks import main as build_manifest_main


def main() -> None:
    parser = argparse.ArgumentParser(description="Harbor helper entry point. Use subcommands.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build-manifest")
    args, rest = parser.parse_known_args()
    if args.cmd == "build-manifest":
        sys.argv = [sys.argv[0], *rest]
        build_manifest_main()


if __name__ == "__main__":
    main()
