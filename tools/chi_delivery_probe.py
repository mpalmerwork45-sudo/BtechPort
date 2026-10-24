"""Exercise an unpacked kit's CHI import/reconstruction without setup caches.

Run with that kit's Python and native binaries, from outside the checkout.
The supplied source is read-only input; every generated file goes under a new
private output. This is CLI/native delivery evidence, not a Windows Tk claim.
"""
from pathlib import Path
import copy,hashlib,json,subprocess,sys
from chi_import import ROOT,import_campaigns,plain_path
from editor_model import EditorError,ProjectDocument,encoded


def check_saved_games(document,output,player):
    """Exercise shipped recovery code using only this probe's private files.

    A retained imported campaign must remain playable when its editable root
    becomes invalid and then moves. This deliberately damages only an exported
    working copy, never the supplied project, a personal save or a reference.
    """
    from app_runtime import project_slot_name
    from save_catalogue import SaveCatalogue,retain_revision,retained_package_id
    output=Path(output);output.mkdir()
    working=output/'Working campaign é 漢字';document.export(working)
    doc=ProjectDocument(working,document.validator);state=output/'Private settings'
    model=SaveCatalogue(state,dict(player=str(player)),document=doc,validator=doc.validator)
    retained=retain_revision(doc,state);directory=model.directory();directory.mkdir(parents=True)
    before=None
    for slot in range(1,6):
        destination=directory/project_slot_name(doc,slot)
        value=json.loads(subprocess.check_output([str(player),'--project',str(working),'--save',str(destination)],cwd=output,text=True,timeout=20))
        if before is not None and value!=before:raise ValueError('Packaged save catalogue slots start in different states.')
        before=value
    rows=model.scan()
    if [r.slot for r in rows]!=list(range(1,7)) or rows[5].path.exists() or not all(r.mtime for r in rows[:5]):
        raise ValueError('Packaged save catalogue did not show six correctly labelled slots and dates.')
    selected=rows[2];original=selected.path.read_bytes();backup=model.backup(selected)
    if backup.read_bytes()!=original:raise ValueError('Packaged backup changed save bytes.')
    recovered=model.recover(selected,6)
    if recovered.read_bytes()!=original:raise ValueError('Packaged recovery changed save bytes.')
    try:model.recover(selected,6)
    except EditorError as error:
        if 'occupied' not in str(error):raise
    else:raise ValueError('Packaged recovery accepted an occupied slot.')
    if recovered.read_bytes()!=original:raise ValueError('Rejected recovery changed the occupied slot.')
    # Existing revisions, including their exact native fingerprints, are the
    # authority after either a broken edit or a relocated source directory.
    (working/'project.json').write_bytes(b'{invalid private probe draft')
    held=next(r for r in model.scan() if r.path==selected.path)
    if held.project!=retained or not model.warnings:raise ValueError('Invalid working project hid its retained save revision.')
    working.rename(output/'Moved working campaign é 漢字')
    identity=retained_package_id(state,working)
    if identity!=doc.manifest['package_id']:raise ValueError('Moved campaign identity was lost.')
    restored=SaveCatalogue(state,dict(player=str(player)),package_id=identity,validator=doc.validator)
    held=next(r for r in restored.scan() if r.path==selected.path)
    command,checked=restored.resume(held)
    continued=json.loads(subprocess.check_output(command,cwd=output,text=True,timeout=20))
    if checked!=before or continued!=before or selected.path.read_bytes()!=original:
        raise ValueError('Packaged retained-revision continuation changed saved progress.')
    return dict(status='passed',slots=6,source_sha256=hashlib.sha256(original).hexdigest(),
        checks=['six labelled slots and timestamps','exact backup and recovery copies','occupied-slot rejection',
                'invalid and moved working project','native Continue from exact retained revision'])


def edit_dialogue_for_recipe(document):
    """Include the audit's copied-text case in actual packaged export checks."""
    from chi_bld import data,insert
    from chi_editor import native_dialogue,set_dialogue
    program=next(p for p in data(document)['programs'] if any(n['op']=='text' and len(n['text'])>200 for n in p['nodes']))
    original=next(n for n in program['nodes'] if n['op']=='text' and len(n['text'])>200)
    cloned=copy.deepcopy(original);cloned.pop('origin',None);cloned.pop('original_size',None)
    cloned['id']='delivery:modified-clone';cloned['text']+='!'
    insert(document,program['id'],original['id'],cloned)
    protected=[original['text']]
    for index in (55,373):
        text=native_dialogue(document)[index];protected.append(text);set_dialogue(document,index,text+'!')
    return protected


def check_dialogue_recipe(recipe,originals):
    """Fail the delivery gate if edited copies expose original text spans."""
    payload=json.dumps(recipe)
    for text in originals:
        for at in range(0,len(text)-31,16):
            if json.dumps(text[at:at+32])[1:-1] in payload:
                raise ValueError('Packaged recipe contains an original dialogue span.')
    if '$chi_text' not in payload or 'chi/talk-data.bin' not in payload:
        raise ValueError('Packaged dialogue recipe omitted original text references.')

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
    # A freshly delivered import must contain both appended terminal messages.
    # This checks shipped extraction/data; visual fidelity remains a GUI gate.
    from chi_editor import native_dialogue
    from prepare_talk import extract
    expected=extract((source/'BTECH.EXE').read_bytes())[0]
    for edition in ('original','updated'):
        imported=ProjectDocument(moved/edition,tool)
        if len(native_dialogue(imported))!=375 or imported.snapshot['chi/talk-data.bin']!=expected:
            raise ValueError('Packaged import omitted current endgame dialogue.')
    checks+=['both imports include exact current 375-entry native dialogue cache']
    doc=ProjectDocument(moved/'updated',tool)
    saves=check_saved_games(doc,output/'Save management é 漢字',player)
    checks+=['packaged save catalogue retains, backs up, recovers and continues an unavailable working campaign']
    # Preserve both imported baselines for later cross-platform continuation
    # of the twelve saves; recipe edits belong to another private working copy.
    edited=output/'Edited campaign é 漢字';doc.export(edited);doc=ProjectDocument(edited,tool)
    example(doc);protected=edit_dialogue_for_recipe(doc);doc.save()
    recipe=output/'Shared changes é 漢字.json';export_recipe(doc,source,recipe)
    check_dialogue_recipe(json.loads(recipe.read_bytes()),protected)
    rebuilt=output/'Reconstructed é 漢字';build_recipe(json.loads(recipe.read_bytes()),source,rebuilt,tool)
    if fingerprint(runtime_files(doc))!=fingerprint(runtime_files(ProjectDocument(rebuilt,tool))):raise ValueError('Packaged recipe changed runtime bytes.')
    checks+=['edited quest and cloned/native dialogue recipe reconstructs exact content without original text literals']
    beacon=ProjectDocument(ROOT/'examples/battletech-demo',tool)
    if derived_images(beacon.files()):raise ValueError('Packaged Last Beacon contains original pixels.')
    restored=output/'Private Last Beacon';reconstruct(beacon,restored,source)
    local=ProjectDocument(restored,tool);images={i['id']:i for i in local.art['images']}
    records=json.loads(beacon.metadata['CHI-TILES.json'])['tiles']
    if len(records)!=20 or any(digest(images[r['id']]['frames'])!=r['original_sha256'] for r in records):raise ValueError('Packaged Last Beacon base reconstruction differs.')
    checks+=['clean packaged Last Beacon reconstructs all 20 original bases locally']
    report=dict(status='passed',kit=str(ROOT),interpreter=sys.executable,checks=checks,slots=states,save_management=saves,
        projects={edition:str(moved/edition) for edition in ('original','updated')},
        edited_project=str(edited),reconstructed_project=str(rebuilt),
        windows_native_Tk='UNKNOWN',limits=['The probe supplies original files to import/reconstruction; completed projects run without any original/cache command arguments.','Native menu slot routing, death-screen pixels and actual GUI controls are checked separately.'])
    (output/'evidence.json').write_bytes(encoded(report));print(json.dumps(report,indent=2));return report

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--data',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    run(a.data,a.output)
