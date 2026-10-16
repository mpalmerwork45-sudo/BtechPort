#!/bin/sh
# Cross-build the Windows executable without changing the host installation.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$root"
tool_path="$root/local-deps/windows/root/usr/bin:/usr/bin:/bin:$PATH"
compiler=${BTP_WINDOWS_CC:-$(PATH="$tool_path" command -v x86_64-w64-mingw32-gcc-posix || true)}
if [ -z "$compiler" ]; then
    echo "Install gcc-mingw-w64-x86-64-posix or set BTP_WINDOWS_CC." >&2
    exit 1
fi
sdl=${BTP_WINDOWS_SDL2:-$root/local-deps/windows/SDL2-2.32.4/x86_64-w64-mingw32/lib/cmake/SDL2}
if [ ! -f "$sdl/sdl2-config.cmake" ]; then
    echo "Set BTP_WINDOWS_SDL2 to the MinGW SDL2 CMake configuration directory." >&2
    exit 1
fi
python3 tools/prepare_talk.py
python3 tools/prepare_combat.py
python3 tools/prepare_world.py
env -u CFLAGS -u CPPFLAGS -u CXXFLAGS -u LDFLAGS PATH="$tool_path" \
    cmake -S "$root" -B "$root/build-windows" \
    -DCMAKE_SYSTEM_NAME=Windows -DCMAKE_C_COMPILER="$compiler" \
    -DCMAKE_C_FLAGS= -DCMAKE_EXE_LINKER_FLAGS= -DCMAKE_BUILD_TYPE=Debug \
    -DSDL2_DIR="$sdl" \
    "-DCMAKE_CROSSCOMPILING_EMULATOR=/usr/bin/python3;$root/tools/windows_check.py" "$@"
env PATH="$tool_path" cmake --build "$root/build-windows" -j 4
