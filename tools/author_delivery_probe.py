"""Headless authoring installation check, including paths containing spaces.

Runs with the kit's Python on Linux or Windows. The independent game executes
in a minimal folder with no authoring files or Python runtime present.
"""
import json,os,shutil,subprocess,sys,tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def check():
    suffix='.exe' if os.name=='nt' else ''
    with tempfile.TemporaryDirectory(prefix='Construction Kit CLI ') as tmp:
        folder=Path(tmp)
        def invoke(*args,ok=True):
            command=([str(ROOT/'Author')] if os.name!='nt' and (ROOT/'Author').is_file() else [sys.executable,str(ROOT/'tools/author.py')])+list(args)
            result=subprocess.run(command,cwd=folder,capture_output=True,text=True,timeout=45)
            assert (result.returncode==0)==ok,result.stdout+result.stderr
            return json.loads(result.stdout)
        caps=invoke('capabilities');assert caps['features']['recorded_campaign_recipes']
        assert invoke('recipe','list')['recipes']
        invoke('create','My independent game','--id','delivery-test','--title','Offline delivery check')
        invoke('source','convert','My independent game','--output','My sources')
        invoke('source','build','My sources','--output','Standalone game')
        scenario=dict(format='btp-author-scenario-v1',steps=[dict(op='pages'),dict(op='checkpoint'),dict(op='capture')])
        (folder/'scenario.json').write_text(json.dumps(scenario))
        invoke('scenario','Standalone game','--file','scenario.json','--output','Gameplay checks')
        invoke('validate','No such game',ok=False)
        recipe=json.loads((ROOT/'examples/authoring/greybank/recipe.json').read_bytes())
        (folder/'My recipe.json').write_text(json.dumps(recipe))
        result=invoke('recipe','build','--file','My recipe.json','--output','Greybank sources','--check',
            '--data','No original assets','--dialogue-data','No talk cache','--combat-data','No combat cache','--world-data','No world cache',ok=False)
        assert all(d['code']=='dependency.missing' for d in result['checks']['diagnostics'])
        invoke('validate','Greybank sources/source')
        # Only the native game binary and its platform libraries are present.
        # The process cannot import an authoring module or call a model service.
        native=folder/'Native only';native.mkdir()
        shutil.copy2(ROOT/'build'/('btech-headless'+suffix),native/('btech-headless'+suffix))
        if os.name=='nt':
            for dll in (ROOT/'build').glob('*.dll'):shutil.copy2(dll,native/dll.name)
        result=subprocess.run([str(native/('btech-headless'+suffix)),'--project',str(folder/'Standalone game'),
            '--save',str(native/'checkpoint.btp')],cwd=native,capture_output=True,text=True,timeout=15)
        assert result.returncode==0,result.stderr
        assert (native/'checkpoint.btp').is_file()
    print('PASS: installed CLI discovery, create/source/build/scenario, relative spaced paths, JSON errors, missing-asset report and native-only saved game.')


if __name__=='__main__':check()
