#!/usr/bin/env python3
"""Convenience entry point to the player's shared C authoring validator."""
import argparse
from pathlib import Path
import subprocess


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Project directory or content.json")
    parser.add_argument("--validator", type=Path, default=root / "build/btp-project",
                        help="Native btp-project executable")
    args = parser.parse_args()
    if not args.validator.is_file():
        parser.error("Build btp-project first: cmake --build build -j2")
    command = "validate" if args.path.is_dir() else "validate-content"
    return subprocess.run([str(args.validator.resolve()), command, str(args.path)], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
