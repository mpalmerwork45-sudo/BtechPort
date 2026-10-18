"""Prefer the distribution's antialiased Tk when a minimal Conda Tk is active."""
import os
from pathlib import Path
import subprocess
import sys


def prefer_system_tk():
    # Some Conda builds use old X core fonts (no Xft), including broken UTF-8
    # glyph fallback. Keep the same launch command but use a complete local
    # system Tk when available. Nothing is installed or downloaded at startup.
    if os.environ.get('BTP_BUNDLED_RUNTIME'):return
    candidate=Path('/usr/bin/python3')
    if sys.platform!='linux' or not candidate.exists():return
    root=Path(__file__).resolve().parents[1]/'local-deps/editor-tk/root/usr/lib'
    paths=[]
    for stdlib in sorted(root.glob('python3.*')):paths.extend([str(stdlib),str(stdlib/'lib-dynload')])
    if Path(sys.executable).resolve()==candidate.resolve():
        # Desktop launchers often start system Python directly. Its optional
        # local Tk extraction needs the same module paths as our Conda handoff.
        sys.path[1:1]=[p for p in paths if p not in sys.path]
        if paths:os.environ['PYTHONPATH']=os.pathsep.join(paths)
        return
    if 'conda' not in sys.prefix.lower() and os.environ.get('CONDA_PREFIX')!=sys.prefix:return
    env=dict(os.environ);env.pop('PYTHONHOME',None)
    # Do not carry another interpreter's site-packages into system Python.
    env['PYTHONPATH']=os.pathsep.join(paths)
    try:
        result=subprocess.run([str(candidate),'-c','import tkinter; import PIL'],env=env,capture_output=True,timeout=3)
    except (OSError,subprocess.TimeoutExpired):return
    if result.returncode==0:os.execve(candidate,[str(candidate),*sys.argv],env)
