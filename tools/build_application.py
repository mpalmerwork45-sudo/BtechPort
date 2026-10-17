#!/usr/bin/env python3
"""Configure/build the three application binaries; original assets are optional."""
import os
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def main():
    env=dict(os.environ)
    for key in ('CFLAGS','CXXFLAGS','CPPFLAGS','LDFLAGS'):env.pop(key,None)
    configure=['cmake','-S',str(ROOT),'-B',str(ROOT/'build')]
    if os.name!='nt' and Path('/usr/bin/gcc').exists():
        env['PATH']='/usr/bin:/bin:'+env.get('PATH','')
        configure+=['-DCMAKE_C_COMPILER=/usr/bin/gcc','-DCMAKE_C_FLAGS=','-DCMAKE_EXE_LINKER_FLAGS=']
    subprocess.run(configure,cwd=ROOT,env=env,check=True)
    subprocess.run(['cmake','--build',str(ROOT/'build'),'--config','Release',
                    '--target','btech-port','btp-project','btech-headless','-j2'],cwd=ROOT,env=env,check=True)


if __name__=='__main__':main()
