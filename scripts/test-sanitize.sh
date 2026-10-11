#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"
env -u CFLAGS -u CPPFLAGS -u CXXFLAGS -u LDFLAGS PATH="/usr/bin:/bin:$PATH" \
    cmake -S . -B build/sanitize -DCMAKE_C_COMPILER=/usr/bin/gcc \
    -DCMAKE_C_FLAGS= -DCMAKE_EXE_LINKER_FLAGS= -DCMAKE_BUILD_TYPE=Debug \
    -DBTP_SANITIZE=ON -DBTP_FRONTEND=OFF
env PATH="/usr/bin:/bin:$PATH" cmake --build build/sanitize -j 4
ctest --test-dir build/sanitize --output-on-failure
build/sanitize/btp-tests "Original DOS"
build/sanitize/btp-script-tests "Original DOS"
build/sanitize/btp-shop-tests "Original DOS"
build/sanitize/btp-save-tests "Original DOS"
python3 tools/verify_m1.py --binary build/sanitize/btech-headless
python3 tools/verify_m2.py --binary build/sanitize/btech-headless
python3 tools/verify_m2b.py --binary build/sanitize/btech-headless
python3 tools/verify_m2c.py --binary build/sanitize/btech-headless
python3 tools/verify_m2d.py --binary build/sanitize/btech-headless
python3 tools/verify_m2e.py --binary build/sanitize/btech-headless
python3 tools/verify_m2f.py --binary build/sanitize/btech-headless
python3 tools/verify_m2g.py --binary build/sanitize/btech-headless
