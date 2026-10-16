#!/usr/bin/env python3
"""Run a Windows build under an isolated, optional Wine installation.

This is also a CMake cross-compiling emulator: absolute host arguments are
mapped through Wine's Z: drive; relative fixture paths keep the project cwd.
It never imports a user's Wine prefix or changes the system installation.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
LOCAL_WINE = ROOT/'local-deps/windows/root/usr/lib/wine/wine64'
WINE = LOCAL_WINE if LOCAL_WINE.exists() else (shutil.which('wine64') or shutil.which('wine'))


def environment(base=None):
    env = dict(os.environ if base is None else base,
        WINEPREFIX=str(ROOT/'work/wine-test'),WINEARCH='win64',
        WINEDLLOVERRIDES='mscoree,mshtml=',WINEDEBUG='-all')
    if WINE==LOCAL_WINE:
        env['WINEDLLPATH']=str(ROOT/'local-deps/windows/root/usr/lib/x86_64-linux-gnu/wine')
    return env


def arguments(args):
    return [('Z:'+str(a).replace('/', '\\')) if str(a).startswith('/') else str(a) for a in args]


def main():
    if not WINE:
        raise SystemExit('Wine was not found. Install wine64 to run Windows tests on Linux.')
    env = environment()
    if sys.argv[1:2]==['--debug']:
        env['WINEDEBUG']='+loaddll';del sys.argv[1]
    if sys.argv[1:2]==['--ctest']:
        # These tests have no window. Keep Wine's diagnostic windows off the
        # user's desktop; a crash must fail the test in its captured log.
        env.pop('DISPLAY',None)
        env.pop('WAYLAND_DISPLAY',None)
        raise SystemExit(subprocess.call(['ctest','--test-dir',str(ROOT/'build-windows'),
            '--output-on-failure',*sys.argv[2:]],env=env,cwd=ROOT))
    if not sys.argv[1:]:
        raise SystemExit('Usage: windows_check.py executable.exe [arguments...]')
    # Debian's wineserver wrapper uses an absolute /usr path. The local
    # dependency setup installs its adjacent wineserver64 as wineserver.
    raise SystemExit(subprocess.call([str(WINE), *arguments(sys.argv[1:])], env=env, cwd=ROOT))


if __name__ == '__main__':
    main()
