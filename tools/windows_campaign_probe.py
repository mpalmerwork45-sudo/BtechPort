"""Check packaged Windows campaign routes and console forwarding under Wine.

This uses the isolated test prefix, never the user's Wine setup. A deliberately
small native interpreter stub tests Author.cmd quoting/exit status; it does
not establish a working Windows Python/Tk installation.
"""
import argparse,json,shutil,subprocess
from pathlib import Path
from windows_check import ROOT,WINE,environment,arguments


def run(kit,campaign,output):
    kit=kit.resolve();campaign=campaign.resolve();output=output.resolve()
    output.mkdir(parents=True,exist_ok=False)
    env=environment();env.pop('DISPLAY',None);env.pop('WAYLAND_DISPLAY',None)
    def invoke(args,name,cwd=output):
        result=subprocess.run([str(WINE),*args],cwd=cwd,env=env,capture_output=True,text=True,timeout=45)
        (output/(name+'.log')).write_text(result.stdout+result.stderr)
        return result
    report=dict(routes={},cmd_forwarding=False,windows_python_tk='UNKNOWN; no native Windows Python runtime supplied')
    for name in ('assault','recovery'):
        artifacts=output/name;artifacts.mkdir()
        args=[kit/'build/btp-author-playtest.exe','--project',campaign/'game','--scenario',campaign/'scenarios'/(name+'.json'),
            '--artifacts',artifacts,'--data',ROOT/'Original DOS','--dialogue-data',ROOT/'work/talk-data.bin',
            '--combat-data',ROOT/'work/combat-data.bin','--world-data',ROOT/'work/world-data.bin']
        result=invoke(arguments(args),name)
        if result.returncode:raise RuntimeError(result.stdout+result.stderr)
        native=next((campaign/'checks/suite'/(name+'-seed-11223583')).glob('final-*.btp'))
        win=next(artifacts.glob('final-*.btp'))
        assert native.read_bytes()==win.read_bytes(),name+' Windows/Linux saves differ'
        report['routes'][name]=dict(status='passed',identical_save_bytes=True)
    # Test the actual command file through Wine cmd, from another directory.
    # The stub logs argv/cwd and returns 23, which Author.cmd must preserve.
    wrapper=output/'Kit with spaces';(wrapper/'runtime').mkdir(parents=True)
    shutil.copy2(kit/'Author.cmd',wrapper/'Author.cmd')
    source=output/'argv-probe.c'
    source.write_text('#include <stdio.h>\n#include <direct.h>\nint main(int n,char **a){char cwd[4096];puts(_getcwd(cwd,sizeof(cwd)));for(int i=1;i<n;i++)puts(a[i]);return 23;}\n')
    compiler=next(line.split('=',1)[1] for line in (ROOT/'build-windows/CMakeCache.txt').read_text().splitlines() if line.startswith('CMAKE_C_COMPILER:'))
    subprocess.run([compiler,str(source),'-o',str(wrapper/'runtime/python.exe')],check=True,capture_output=True,text=True,timeout=20)
    script=arguments([wrapper/'Author.cmd'])[0]
    # Put cmd syntax in a batch file: passing nested cmd quoting through Wine's
    # Unix argv adapter would test that extra adapter rather than our launcher.
    driver=output/'launcher-check.cmd'
    driver.write_bytes((f'@echo off\r\ncall "{script}" recipe build --file "relative recipe.json"\r\nexit /b %errorlevel%\r\n').encode('ascii'))
    result=invoke(['cmd.exe','/d','/c',arguments([driver])[0]],'cmd-forwarding')
    lines=result.stdout.splitlines()
    assert result.returncode==23,(result.returncode,result.stdout,result.stderr)
    assert lines[0].lower()==arguments([output])[0].lower(),lines
    assert lines[1:]==['-E','-s',arguments([wrapper/'tools/author.py'])[0],'recipe','build','--file','relative recipe.json'],lines
    report['cmd_forwarding']=True
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kit',type=Path,required=True);p.add_argument('--campaign',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(run(a.kit,a.campaign,a.output),indent=2))
