#!/usr/bin/env python3
"""Compare maintained game routes against a retained pre-refactor executable.

Trace text, frames and saves are temporary local artifacts. Only their hashes
and comparison results are printed; no original assets enter the repository.
"""
import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    "fresh": ["--replay", "tests/fixtures/ordinary-fresh-campaign.actions"],
    "spy": ["--replay", "tests/fixtures/ordinary-spy-replacement.actions"],
    "services": ["--replay", "tests/fixtures/ordinary-services.actions"],
}


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            value.update(block)
    return value.hexdigest()


def capture(binary, args, directory):
    directory.mkdir()
    with (directory / "trace").open("wb") as output:
        result = subprocess.run([str(binary), *args, "--trace", "--save-file",
                        str(directory / "slot.btp"), "--save",
                        str(directory / "save"), "--frame", str(directory / "frame")],
                                cwd=ROOT, stdout=output, stderr=subprocess.PIPE,
                                check=True, timeout=120)
    if result.stderr:
        raise RuntimeError(result.stderr.decode(errors="replace"))
    return {name: digest(directory / name) for name in ("trace", "save", "frame")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, default=ROOT / "build/btech-headless")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="btp-preparation-") as temporary:
        root = Path(temporary)
        for case, inputs in CASES.items():
            before = capture(args.before.resolve(), inputs, root / (case + "-before"))
            after = capture(args.after.resolve(), inputs, root / (case + "-after"))
            if before != after:
                raise SystemExit(f"FAIL {case}: before={before}, after={after}")
            print(f"PASS {case}: every traced input, final save and frame match", flush=True)


if __name__ == "__main__":
    main()
