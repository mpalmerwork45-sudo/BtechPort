"""Copy a legacy CHI project with appended endgame text and an optional save.

The old project/save are preserved. Only the two newly extracted terminal
strings may differ; the migration policy proves every gameplay file unchanged.
"""
from pathlib import Path
import hashlib,json,tempfile
from editor_model import ProjectDocument,EditorError,encoded
from chi_import import plain_path,output_path,publish
from prepare_talk import extract
from save_migration import compatible,migrate

def update(project,source,output,validator,save=None,player=None):
    project,source=map(plain_path,(project,source));output=output_path(output,project,source)
    if output.exists():
        raise EditorError('Choose a new output outside the old project and reference/source folders.')
    if not output.parent.is_dir():raise EditorError('Choose an existing output parent.')
    old=ProjectDocument(project,validator)
    if old.manifest.get('requires')!='chi-local-dos-1.03':raise EditorError('Select an imported CHI campaign.')
    cache,origins=extract((source/'BTECH.EXE').read_bytes())
    with tempfile.TemporaryDirectory(prefix='.chi-endgame-',dir=output.parent) as temporary:
        stage=Path(temporary)/'game';old.export(stage);(stage/'chi/talk-data.bin').write_bytes(cache)
        new=ProjectDocument(stage,validator);checks=compatible(old,new)
        record=stage/'IMPORT.json'
        if record.exists():
            value=json.loads(record.read_bytes())
            for row in value.get('resources',[]):
                if row.get('file')=='chi/talk-data.bin':row['sha256']=hashlib.sha256(cache).hexdigest()
            value['endgame_text_update']=dict(format=origins['format'],original_project=str(project),checks=checks)
            record.write_bytes(encoded(value))
        report=dict(status='updated',project=str(output),checks=checks)
        if save:
            result=migrate(old,new,Path(save),stage/'recovered-save.btp',dict(player=str(player or Path(validator).with_name('btech-headless'))))
            report.update(save=str(output/'recovered-save.btp'),tick=result['tick'],credits=result['credits'])
        old.unchanged_on_disk();publish(stage,output)
    return report

if __name__=='__main__':
    import argparse
    from app_runtime import binary
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('project','data','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--save',type=Path);p.add_argument('--validator',type=Path,default=binary('btp-project'));p.add_argument('--player',type=Path,default=binary('btech-headless'));a=p.parse_args()
    try:print(json.dumps(update(a.project,a.data,a.output,a.validator,a.save,a.player),indent=2))
    except (OSError,ValueError,EditorError) as e:p.exit(1,str(e)+'\n')
