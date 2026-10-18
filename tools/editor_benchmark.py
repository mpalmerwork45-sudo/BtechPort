"""Declared larger editor fixture; no game or reference files are modified."""
import copy
import json
from pathlib import Path
import resource
import time
from editor_model import create_project


def fixture(directory,validator):
    root=Path(__file__).resolve().parents[1]
    document=create_project(root/'examples/beacon-demo',directory,'editor-scale','Large editor fixture',validator)
    content=copy.deepcopy(document.content);adventure=copy.deepcopy(document.adventure)
    for i in range(len(content['mechs']),200):
        unit=copy.deepcopy(content['mechs'][0]);unit.update(id=f'bench:unit-{i}',name=f'Fixture unit {i}');content['mechs'].append(unit)
    for i in range(len(adventure['maps']),16):
        scene=copy.deepcopy(adventure['maps'][0]);scene.update(id=f'bench:map-{i}',name=f'Fixture map {i}',origin=[256+(i%4)*64,256+(i//4)*64],rows=['.'*64]*64,overlays=[],entrances=[]);adventure['maps'].append(scene)
    for i in range(len(adventure['events']),256):adventure['events'].append(dict(id=f'bench:event-{i}',op='end'))
    from art_editing import new_image
    art=copy.deepcopy(document.art)
    for i in range(1024):
        image=new_image('bench',[],f'Fixture tile {i}','tile',16,16,1);image['id']=f'bench:image-{i}';art['images'].append(image)
    document.replace_both(content,adventure);document.replace_art(art);document.save()
    document.undo_stack=[];document.undo_labels=[]
    return document


def run(workspace,directory,validator,work):
    from editor_tasks import validate
    document=fixture(directory,validator);workspace.app.set_document(document);workspace.window.update()
    beats=[];timer=None;running=True
    def heartbeat():
        nonlocal timer
        beats.append(time.monotonic())
        if running:timer=workspace.window.after(10,heartbeat)
    heartbeat();started=time.monotonic();validate(workspace,workspace.app._editor_scope);feedback=time.monotonic()-started
    while workspace.tasks.jobs:
        workspace.window.update();time.sleep(.005)
        if time.monotonic()-started>30:raise AssertionError('Large-fixture validation timed out')
    running=False
    if timer:workspace.window.after_cancel(timer)
    # Linux getrusage can retain the launcher/fork's pre-exec high-water mark.
    # /proc reports this executable image's own resident-set high-water mark.
    memory={}
    for line in Path('/proc/self/status').read_text().splitlines():
        if line.startswith(('VmRSS:','VmHWM:')):memory[line.split(':')[0]]=int(line.split()[1])/1024
    result=dict(units=200,maps=16,events=256,images=1024,package_bytes=sum(map(len,document.files().values())),
        feedback_ms=round(feedback*1000,1),validation_ms=round((time.monotonic()-started)*1000,1),
        heartbeat_max_ms=round(max((b-a for a,b in zip(beats,beats[1:])),default=0)*1000,1),
        process_peak_rss_mib=round(memory['VmHWM'],1),process_rss_mib=round(memory['VmRSS'],1))
    (work/'editor-performance.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Larger editor fixture: '+json.dumps(result))


def standalone(env,work):
    import tkinter as tk
    import tempfile
    from editor_workspace import Workspace
    with tempfile.TemporaryDirectory(prefix='editor-benchmark-',dir=work) as temporary:
        directory=Path(temporary);root=tk.Tk();workspace=Workspace(root,Path('build/btp-project'),directory/'state')
        try:run(workspace,directory/'game',Path('build/btp-project'),work)
        finally:root.destroy()
