#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"
python3 tools/prepare_talk.py
# This Kubuntu shell has Conda compiler/linker flags and an older ld in PATH.
# Select the host compiler/tools without changing the user's shell configuration.
env -u CFLAGS -u CPPFLAGS -u CXXFLAGS -u LDFLAGS PATH="/usr/bin:/bin:$PATH" \
    cmake -S "$root" -B "$root/build" -DCMAKE_C_COMPILER=/usr/bin/gcc \
    -DCMAKE_C_FLAGS= -DCMAKE_EXE_LINKER_FLAGS= -DCMAKE_BUILD_TYPE=Debug "$@"
env PATH="/usr/bin:/bin:$PATH" cmake --build "$root/build" -j 4
