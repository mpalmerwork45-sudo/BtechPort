"""Optional sprite actions, with durations measured in 32 ms logical ticks."""
import copy
from editor_model import EditorError

ACTIONS=('idle','walk','fire','jump','damage','destruction')

def parse_sequence(text,count):
    result=[]
    try:
        for pair in text.replace(',',' ').split():
            frame,ticks=map(int,pair.split(':'))
            if not 1<=frame<=count or not 1<=ticks<=255:raise ValueError()
            result.append(dict(frame=frame-1,ticks=ticks))
    except ValueError:raise EditorError('Use image:duration pairs, for example 1:4 2:4. Images start at 1; durations are 1..255 ticks.')
    if not 1<=len(result)<=32 or sum(f['ticks'] for f in result)>255:
        raise EditorError('Each sequence needs 1..32 frames and at most 255 total ticks.')
    return result

def set_track(image,action,lines,sound=0):
    if action not in ACTIONS or len(lines) not in (1,8):raise EditorError('Choose one shared or eight directional sequences.')
    sound=int(sound)
    if not 0<=sound<=18 or (sound and action not in ('fire','damage','destruction')):
        raise EditorError('Sound cues 1..18 are supported for fire, damage and destruction; 0 retains the normal sound.')
    track=dict(directions=[parse_sequence(t,len(image['frames'])) for t in lines],sound=sound)
    image.setdefault('animations',{})[action]=track

def entries(image,action,direction):
    track=image.get('animations',{}).get(action)
    if not track:return None
    return track['directions'][0 if len(track['directions'])==1 else direction]

def edit_track(editor):
    from adventure_editor import Form
    from tkinter import ttk
    action=editor.view.get().lower()
    if action not in ACTIONS:action='walk'
    f=Form(editor,'Animation action')
    f.field('action',action,ACTIONS)
    f.field('layout','Shared',['Shared','Eight directions'])
    f.field('sound',0)
    ttk.Label(f.body,text='Image:duration pairs (1-based images, 32 ms ticks).\nExample: 1:4 2:2 3:4. Shared uses the first line.').grid(row=f.row,column=0,columnspan=2,sticky='w');f.row+=1
    from sprite_editing import DIRECTIONS
    for d,name in enumerate(DIRECTIONS):f.field(name,'1:4')
    def load(*_):
        t=editor.image.get('animations',{}).get(f.values['action'].get(),{})
        dirs=t.get('directions',[[dict(frame=0,ticks=4)]])
        f.values['layout'].set('Shared' if len(dirs)==1 else 'Eight directions');f.values['sound'].set(str(t.get('sound',0)))
        for d,name in enumerate(DIRECTIONS):f.values[name].set(' '.join(f"{e['frame']+1}:{e['ticks']}" for e in dirs[d if len(dirs)==8 else 0]))
    f.values['action'].trace_add('write',load);load()
    def apply(v):
        editor.finish();candidate=copy.deepcopy(editor.image)
        set_track(candidate,v['action'],[v[n] for n in (DIRECTIONS if v['layout']=='Eight directions' else DIRECTIONS[:1])],v['sound'])
        editor.history.append(editor.image);editor.future=[];editor.image=candidate
        editor.view.set(v['action'].title());editor.phase=0;editor.refresh_frames();editor.draw()
    f.submit(apply)
