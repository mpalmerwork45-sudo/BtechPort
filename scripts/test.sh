#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"
mkdir -p work
ctest --test-dir build --output-on-failure
build/btp-tests "Original DOS"
build/btp-script-tests "Original DOS"
python3 -m unittest discover -s tests -p test_tools.py
SDL_VIDEODRIVER=dummy build/btech-port --smoke --record work/native-smoke.actions --frame work/native-smoke.ppm
python3 tools/verify_m1.py --native-log work/native-smoke.actions
SDL_VIDEODRIVER=dummy build/btech-port --smoke-citadel --record work/native-citadel.actions --frame work/native-citadel.ppm
python3 tools/verify_m2.py --native-log work/native-citadel.actions
SDL_VIDEODRIVER=dummy build/btech-port --smoke-katrina --record work/native-katrina.actions --frame work/native-katrina.ppm
python3 tools/verify_m2b.py --native-log work/native-katrina.actions
if [ "${1:-}" = "--x11" ]; then
    python3 tools/native_smoke.py
fi
python3 tools/reference_guard.py verify
