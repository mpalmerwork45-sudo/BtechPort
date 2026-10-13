#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"
env -u CFLAGS -u CPPFLAGS -u CXXFLAGS -u LDFLAGS PATH="/usr/bin:/bin:$PATH" \
    cmake -S . -B build/sanitize -DCMAKE_C_COMPILER=/usr/bin/gcc \
    -DCMAKE_C_FLAGS= -DCMAKE_EXE_LINKER_FLAGS= -DCMAKE_BUILD_TYPE=Debug \
    -DBTP_SANITIZE=ON -DBTP_FRONTEND=OFF
env PATH="/usr/bin:/bin:$PATH" cmake --build build/sanitize -j 4
# A focused historical rerun need not repeat the already passing core suites.
# Configuration/build still run, so this option never uses a stale binary.
if [ "${1:-}" != "--historical-only" ]; then
    ctest --test-dir build/sanitize --output-on-failure
fi
if [ "${1:-}" = "--core-only" ]; then
    exit 0
fi
build/sanitize/btp-tests "Original DOS"
build/sanitize/btp-script-tests "Original DOS"
build/sanitize/btp-shop-tests "Original DOS"
build/sanitize/btp-save-tests "Original DOS"
build/sanitize/btp-school-tests "Original DOS"
build/sanitize/btp-training-tests "Original DOS"
build/sanitize/btp-anm-tests "Original DOS"
python3 tools/verify_m1.py --binary build/sanitize/btech-headless
python3 tools/verify_m2.py --binary build/sanitize/btech-headless
python3 tools/verify_m2b.py --binary build/sanitize/btech-headless
python3 tools/verify_m2c.py --binary build/sanitize/btech-headless
python3 tools/verify_m2d.py --binary build/sanitize/btech-headless
python3 tools/verify_m2e.py --binary build/sanitize/btech-headless
python3 tools/verify_m2f.py --binary build/sanitize/btech-headless
python3 tools/verify_m2g.py --binary build/sanitize/btech-headless
python3 tools/verify_m2h.py --binary build/sanitize/btech-headless
python3 tools/verify_sprites.py --binary build/sanitize/btech-headless
python3 tools/verify_m2j.py --binary build/sanitize/btech-headless
python3 tools/verify_m2kl.py --binary build/sanitize/btech-headless
python3 tools/make_training_replay.py --binary build/sanitize/btech-headless
python3 tools/make_combat_replay.py --binary build/sanitize/btech-headless
python3 tools/make_training_combat_replay.py --binary build/sanitize/btech-headless
python3 tools/make_training_combat_replay.py --kick --binary build/sanitize/btech-headless
python3 tools/make_training_combat_replay.py --campaign --binary build/sanitize/btech-headless
python3 tools/verify_animations.py --binary build/sanitize/btp-anm-tests --frame work/rubble-result.ppm --dream-frame work/rest-wake.ppm
