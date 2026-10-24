"""Opt-in quests over an imported CHI campaign; GUI/CLI share these edits.

The native spatial projection remains separate. QuestDocument is a live view
of metadata using the parent's history, transaction and content validator.
No original graphics, dialogue or compiled programs are distributed here.
"""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
from editor_model import EditorError, encoded

FILE='chi-bridge.json'
EVENTS='chi-events.json'
FORMAT='btp-chi-bridge-v1'
OPS=('call','return','chi_native','chi_if','chi_sound','chi_film')

def data(document):
    return json.loads(document.metadata.get(FILE,encoded(dict(format=FORMAT,schema_version=1,entrances=[],native_calls=[]))))

def events(document):
    if EVENTS not in document.metadata:raise EditorError('Enable CHI quests first.')
    return json.loads(document.metadata[EVENTS])

def empty_events():
    # Standard authored format. Startup is a valid editor preview definition;
    # the bridge runtime preserves the actual native campaign's crew/money.
    return dict(format='btp-adventure-v3',schema_version=3,
        tiles=[dict(id='quest:ground',sheet='chi:land',graphic=64,terrain='clear',mini_color=2)],
        maps=[dict(id='quest:field',name='Quest field',origin=[64,64],rows=[['quest:ground']*32 for _ in range(32)],overlays=[],entrances=[])],
        people=[dict(id='quest:preview',identity='chi:jason',attributes=[8,9,7],skills=[2,2,2,3,3,2,1],weapon=7,armor=2)],
        shops=[],encounters=[],flags=[],events=[dict(id='quest:end',op='end')],
        start=dict(map='quest:field',at=[24,28],event='quest:end',credits=35,party=[dict(person='quest:preview',mech='none')]))

def enable(document):
    if document.manifest.get('chi_bridge'):return
    if document.manifest.get('requires')!='chi-local-dos-1.03':raise EditorError('CHI quests require an imported CHI campaign.')
    from chi_spatial import enable as enable_maps
    from chi_bld import enable as enable_scripts
    with document.command('Enable CHI quests'):
        enable_maps(document);enable_scripts(document)
        manifest=copy.deepcopy(document.manifest);manifest.update(chi_bridge=FILE,chi_events=EVENTS)
        meta=dict(document.metadata);meta[FILE]=encoded(data(document));meta[EVENTS]=encoded(empty_events())
        document.replace_all(document.content,document.adventure,document.art,manifest,meta);document.validate()

def put(document,bridge=None,quest=None):
    with document.command('Edit CHI quest'):
        enable(document);meta=dict(document.metadata)
        if bridge is not None:meta[FILE]=encoded(bridge)
        if quest is not None:meta[EVENTS]=encoded(quest)
        document.replace_all(document.content,document.adventure,document.art,document.manifest,meta);document.validate()

class QuestDocument:
    """One document/history, two named content views; never swap global maps."""
    def __init__(self,base):self.base=base
    def __getattr__(self,key):return getattr(self.base,key)
    @property
    def adventure(self):return events(self.base) if self.base.manifest.get('chi_bridge') else empty_events()
    @property
    def saved_adventure(self):return json.loads(self.base.saved_metadata.get(EVENTS,encoded(empty_events())))
    def replace_adventure(self,value):self.replace_all(self.content,value,self.art,self.manifest)
    def replace_all(self,content,adventure,art,manifest,metadata=None):
        if not self.base.manifest.get('chi_bridge'):raise EditorError('Quest support was undone. Redo Enable CHI quests before editing this view.')
        meta=dict(self.base.metadata if metadata is None else metadata);meta[EVENTS]=encoded(adventure)
        self.base.replace_all(content,self.base.adventure,art,manifest,meta)
    def replace_art(self,art,adventure=None,metadata=None):
        manifest=copy.deepcopy(self.manifest);manifest.setdefault('graphics','graphics.json')
        self.replace_all(self.content,self.adventure if adventure is None else adventure,art,manifest,metadata)

def upsert(document,collection,value):
    if collection not in ('entrances','native_calls'):raise EditorError('Choose entrances or native_calls.')
    with document.command('Edit CHI quest binding'):
        enable(document);b=data(document);rows=b[collection]
        index=next((i for i,v in enumerate(rows) if v['id']==value['id']),None)
        if index is None:rows.append(copy.deepcopy(value))
        else:rows[index]=copy.deepcopy(value)
        put(document,b)

def example(document):
    """Add the same small optional contract in either edition, in one undo."""
    from chi_spatial import change,find,data as spatial
    from chi_bld import data as scripts,find as program
    with document.command('Add CHI quest example'):
        enable(document)
        if any(e['id']=='bridge:welcome' for e in events(document)['events']):raise EditorError('The bridge example already exists.')
        native=spatial(document);town=find(native['maps'],'chi:map-01')
        slot=next((d['slot'] for d in town['entrances'] if d['slot']<12 and not d['active']),None)
        if slot is None:raise EditorError('The example needs a vacant Citadel door slot.')
        # Use an accessible tile beside the starting training ground. This is
        # an added contract marker, never a replacement for a native building.
        half=[71,25]
        def marker(v):
            d=find(v['maps'],'chi:map-01')['entrances'][slot]
            d.update(name='Relay contract',active=1,half=half,room=2)
        change(document,marker,'Place quest doorway')
        p=program(scripts(document),'chi:bld-comstar')
        entry=next(n['id'] for n in p['nodes'] if n['op']=='native' and n['action']==7)
        # The return boundary follows the original receipt wait. It is a
        # stable label, so changing earlier dialogue does not break a save PC.
        receipt=next(i for i,n in enumerate(p['nodes']) if n.get('origin')==0x2ce and n['op']=='wait')
        end=p['nodes'][receipt+1]['id']
        b=data(document);b['native_calls'].append(dict(id='bridge:bank',program=p['id'],entry=entry,**{'return':end}))
        b['entrances'].append(dict(id='bridge:relay-door',map=town['id'],entrance=slot,event='bridge:welcome'))
        a=events(document);a['flags'].append('bridge:paid')
        a['people'].append(dict(id='bridge:raider',identity='chi:hunter',attributes=[2,2,2],skills=[0]*7,weapon=0,armor=0))
        a['encounters'].append(dict(id='bridge:patrol',map='quest:field',party_at=[24,28],enemies=[dict(kind='person',definition='bridge:raider',at=[36,28])]))
        a['events'] += [
            dict(id='bridge:welcome',op='chi_if',story_index=4,value=0,then='bridge:cadet',**{'else':'bridge:veteran'}),
            dict(id='bridge:cadet',op='say',text='A relay operator welcomes the cadet. An optional patrol contract is available.',next='bridge:choice'),
            dict(id='bridge:veteran',op='say',text='A relay operator recognizes a veteran. The original campaign continues beyond this contract.',next='bridge:choice'),
            dict(id='bridge:choice',op='choice',text='The relay needs help. You can also visit its ComStar investment desk.',options=[dict(label='Patrol the relay',next='bridge:check'),dict(label='Buy shares',next='bridge:bank-call'),dict(label='Leave',next='bridge:cancel')],cancel='bridge:cancel'),
            dict(id='bridge:bank-call',op='chi_native',call='bridge:bank',next='bridge:choice',failure='bridge:no-service',cancel='bridge:choice'),
            dict(id='bridge:no-service',op='say',text='The service could not complete. Your existing accounts are unchanged.',next='bridge:choice'),
            dict(id='bridge:check',op='if',flag='bridge:paid',value=1,then='bridge:repeat',**{'else':'bridge:sound'}),
            dict(id='bridge:sound',op='chi_sound',program=1,next='bridge:film',failure='bridge:failed'),
            dict(id='bridge:film',op='chi_film',film=1,next='bridge:fight',failure='bridge:failed'),
            dict(id='bridge:fight',op='battle',encounter='bridge:patrol',win='bridge:reward',loss='bridge:lost',flee='bridge:retreated',failure='bridge:failed'),
            dict(id='bridge:reward',op='reward',credits=250,next='bridge:paid-flag',failure='bridge:failed'),
            dict(id='bridge:paid-flag',op='flag',flag='bridge:paid',value=1,next='bridge:thanks'),
            dict(id='bridge:thanks',op='say',text='The relay is secure. Your 250 C-bill reward has been credited.',next='quest:end'),
            dict(id='bridge:repeat',op='say',text='The relay remains secure. This contract has already been paid.',next='quest:end'),
            dict(id='bridge:lost',op='say',text='The patrol was defeated. Surviving crew return without a reward.',next='bridge:failed'),
            dict(id='bridge:retreated',op='say',text='You withdrew from the patrol. No reward was paid. You may return later.',next='bridge:cancel'),
            dict(id='bridge:failed',op='return',result='failure'),dict(id='bridge:cancel',op='return',result='cancel')]
        put(document,b,a)
        return dict(map=town['id'],entrance=slot,half=half,event='bridge:welcome')

def schema():
    from authoring_contract import obj,array,ID,integer
    binding=obj(dict(id=ID,map={'enum':[f'chi:map-{i:02}' for i in range(1,14)]},entrance=integer(0,11),event=ID),['id','map','entrance','event'])
    call=obj(dict(id=ID,program=ID,entry=ID,**{'return':ID}),['id','program','entry','return'])
    return obj(dict(format={'const':FORMAT},schema_version={'const':1},entrances=array(binding,0,64),native_calls=array(call,0,64)),['format','schema_version','entrances','native_calls'])

def main():
    from editor_model import ProjectDocument
    from app_runtime import binary
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',type=Path,required=True)
    sub=p.add_subparsers(dest='command',required=True)
    for name in ('enable','list','example'):sub.add_parser(name)
    a=p.parse_args()
    try:
        d=ProjectDocument(a.project,binary('btp-project'))
        if a.command=='list':print(json.dumps(dict(bridge=data(d),quest=events(d)),indent=2));return
        enable(d) if a.command=='enable' else example(d)
        print(d.save())
    except (EditorError,OSError,ValueError) as e:p.exit(1,str(e)+'\n')
if __name__=='__main__':main()
