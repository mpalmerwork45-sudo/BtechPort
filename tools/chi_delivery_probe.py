"""Exercise an unpacked kit's CHI import/reconstruction without setup caches.

Run with that kit's Python and native binaries, from outside the checkout.
The supplied source is read-only input; every generated file goes under a new
private output. This is CLI/native delivery evidence, not a Windows Tk claim.
"""
from pathlib import Path
import hashlib,json,subprocess,sys
from chi_import import ROOT,import_campaigns,plain_path
from editor_model import ProjectDocument,encoded

def run(source,output):
    from app_runtime import binary
    from chi_recipe import export_recipe,build_recipe,fingerprint,runtime_files
    from chi_bridge import example
    from asset_provenance import reconstruct,derived_images,digest
    source=plain_path(source);output=plain_path(output)
    if output.exists():raise ValueError('Delivery probe needs a new private output folder.')
    output.mkdir();tool=binary('btp-project');player=binary('btech-headless');checks=[]
    import_campaigns(source,output/'fresh é 漢字',validator=tool)
    moved=output/'Moved campaigns é 漢字';(output/'fresh é 漢字').rename(moved)
    states={}
    for edition in ('original','updated'):
        project=moved/edition;states[edition]=[]
        for slot in range(6):
            save=output/(edition+' slot '+str(slot+1)+' 漢字.btp')
            command=[str(player),'--project',str(project)]
            start=json.loads(subprocess.check_output([*command,'--save',str(save)],cwd=output,text=True,timeout=20))
            resumed=json.loads(subprocess.check_output([*command,'--load',str(save)],cwd=output,text=True,timeout=20))
            if start!=resumed:raise ValueError('Packaged save/load differs.')
            other=moved/('updated' if edition=='original' else 'original')
            rejected=subprocess.run([str(player),'--project',str(other),'--load',str(save)],cwd=output,capture_output=True,timeout=20)
            if not rejected.returncode:raise ValueError('Cross-edition project save accepted.')
            states[edition].append(dict(slot=slot+1,rules=start.get('combat_rules','legacy'),sha256=hashlib.sha256(save.read_bytes()).hexdigest()))
    checks+=['fresh both-profile import with bundled tools','moved Unicode/spaced project paths','no external original/cache arguments','12 native saves and cross-project rejection']
    doc=ProjectDocument(moved/'updated',tool);example(doc);doc.save()
    recipe=output/'Shared changes é 漢字.json';export_recipe(doc,source,recipe)
    rebuilt=output/'Reconstructed é 漢字';build_recipe(json.loads(recipe.read_bytes()),source,rebuilt,tool)
    if fingerprint(runtime_files(doc))!=fingerprint(runtime_files(ProjectDocument(rebuilt,tool))):raise ValueError('Packaged recipe changed runtime bytes.')
    checks+=['edited quest recipe exported and reconstructed with exact content']
    beacon=ProjectDocument(ROOT/'examples/battletech-demo',tool)
    if derived_images(beacon.files()):raise ValueError('Packaged Last Beacon contains original pixels.')
    restored=output/'Private Last Beacon';reconstruct(beacon,restored,source)
    local=ProjectDocument(restored,tool);images={i['id']:i for i in local.art['images']}
    records=json.loads(beacon.metadata['CHI-TILES.json'])['tiles']
    if len(records)!=20 or any(digest(images[r['id']]['frames'])!=r['original_sha256'] for r in records):raise ValueError('Packaged Last Beacon base reconstruction differs.')
    checks+=['clean packaged Last Beacon reconstructs all 20 original bases locally']
    report=dict(status='passed',kit=str(ROOT),interpreter=sys.executable,checks=checks,slots=states,
        windows_native_Tk='UNKNOWN',limits=['The probe supplies original files to import/reconstruction; completed projects run without any original/cache command arguments.','Native menu slot routing is checked separately by the campaign acceptance helper.'])
    (output/'evidence.json').write_bytes(encoded(report));print(json.dumps(report,indent=2));return report

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    run(a.data,a.output)
