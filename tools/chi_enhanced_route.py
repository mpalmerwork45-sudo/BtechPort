"""Generate a private, input-only Updated campaign using Enhanced throughout.

Planning observes actual saved state and emits ordinary inputs. No save fields,
quest flags, RNG values or combat definitions are changed to win a mission.
"""
from collections import deque
from pathlib import Path
import json,struct,shutil
from chi_updated_route import Updated
from make_fresh_campaign_replay import ROOT
from exepack import unpack
from prepare_talk import DS


class Enhanced(Updated):
    def __init__(self,project,output,source=None):
        self.project=Path(project).resolve();self.work=Path(output).resolve();self.work.mkdir()
        self.original_data=Path(source or ROOT/'Original DOS').resolve()
        self.source='Fresh Updated start; default Enhanced rules throughout'
        self.binary=ROOT/'build/btech-headless';self.slot=self.work/'current.btp';self.leg=self.work/'leg.actions'
        self.checkpoints=[];self.notes=self.checkpoints
        self.actions=(ROOT/'tests/fixtures/ordinary-rubble-story.actions').read_text().splitlines()
        self.leg.write_text('\n'.join(self.actions)+'\n')
        self.state=self.execute('--replay',self.leg,'--save',self.slot)
        if self.state['combat_rules']!='enhanced' or self.state['story_flags'][0]!=2 or self.state['menu_id']!=7:
            raise RuntimeError('Enhanced drive/rubble prerequisites did not complete.')
        image,_=unpack((self.original_data/'BTECH.EXE').read_bytes())
        self.answers=struct.unpack_from('<10H',image,DS+0x28ec)
        self.note('drive-and-rubble-complete')

    def advance(self,keys):
        super().advance(keys)
        if self.state['combat_rules']!='enhanced':raise RuntimeError('Enhanced route changed combat rules.')

    def note(self,label):
        state=self.state
        self.notes.append(dict(label=label,tick=len(self.actions),mode=state['mode'],assignment=state['mission']['assignment'],
            story=state['story_flags'][:2],rules=state['combat_rules']))
        (self.work/'checkpoints.json').write_text(json.dumps(self.notes,indent=2)+'\n')
        print(label,len(self.actions),state['mode'],flush=True)

    def walk_return(self):
        terrain=(self.project/'chi/MAP1.MTP').read_bytes()[541:]
        def tile(x,y):return 255 if not 0<=x<64 or not 0<=y<64 else terrain[(y&56)*64+(y&7)*8+(x&56)*8+(x&7)]
        start=self.state['x_half'],self.state['y_half'];parents={start:None};queue=deque([start]);goal=None
        while queue:
            p=queue.popleft()
            if p[0]<=60 and 73<=p[1]<=79:goal=p;break
            for action,dx,dy in (('up',0,-1),('right',1,0),('down',0,1),('left',-1,0)):
                q=p[0]+dx,p[1]+dy;x,y=q
                if q in parents or not 0<=x<126 or not 2<=y<128:continue
                if tile(x//2,(y-2)//2)>=85 or tile(x//2+1,(y-2)//2)>=85:continue
                parents[q]=(p,action);queue.append(q)
        if goal is None:raise RuntimeError('No training return path.')
        keys=[]
        while parents[goal] is not None:goal,action=parents[goal];keys.append(action)
        self.advance(list(reversed(keys))+['idle'])

    def next_loan(self,delay=0):
        self.advance(['idle']*((self.state['story_flags'][20]*1100+223)//224+delay))
        # Pre-invasion walking uses the single cadet's exact door contact,
        # rather than the later compact-party/world entrance convention.
        from make_campaign_replay import Session
        Session.route(self,0);self.advance(['accept','accept'])
        if self.state['mode']!='training-quiz':raise RuntimeError('Training quiz did not open: '+str(self.state['mode']))
        if self.state['quiz']['phase']!=2:self.advance(['accept'])
        for _ in range(3):
            q=self.state['quiz'];self.advance(['down']*((self.answers[q['point']]-q['selected'])%20)+['accept'])
        self.advance(['accept','accept'])
        if self.state['menu_id']!=7:raise RuntimeError('Next loan menu unavailable.')

    def launch(self):
        self.advance(['down']*((2-self.state['menu_selected'])%3)+['accept'])
        for _ in range(128):
            if not self.state['animation']['active']:break
            self.advance(['idle'])
        for _ in range(8):
            c=self.state['combat']
            if c['phase'] not in (1,2,3):break
            # The allowed global-control question starts on No. Explicit Yes
            # uses the ordinary computer option; later assignments use orders.
            self.advance((['left'] if c['phase']==1 else [])+['accept'])
        if self.state['combat']['phase']!=4 and not self.state['campaign']['invasion']:raise RuntimeError('Combat command menu unavailable.')
        self.note('training-combat-start')

    def automatic_victory(self):
        if not self.state['combat']['automatic']:self.command(5)
        for _ in range(2048):
            c=self.state['combat']
            if not c['phase']:break
            if c['phase']==4:self.command(9)
            else:self.advance(['idle']*64)
        else:raise RuntimeError('Enhanced combat exceeded its turn budget.')
        if not self.state['combat']['won']:raise RuntimeError('Enhanced training was not won.')
        self.note('training-victory')
        if self.state['mission']['phase']!=7:raise RuntimeError('Missing return-to-base popup.')
        self.advance(['accept']);self.walk_return()
        for _ in range(128):
            if self.state['mode']=='local-exploration':break
            self.advance(['idle']*8 if self.state['animation']['active'] else ['accept'])
        self.note('training-report')

    def device(self):
        from make_campaign_replay import Session
        Session.route(self,7);self.advance(['accept'])
        self.advance(['down']*((0-self.state['menu_selected'])%2)+['accept'])
        if self.state['talk_phase']!=2 or not self.state['talk_mask']&1:raise RuntimeError('Rick was not invited.')
        self.advance(['up']*self.state['talk_selected']+['accept'])
        for _ in range(5):self.advance(['accept'])
        if not self.state['device']:raise RuntimeError('Rick did not provide the device.')
        self.advance(['down']*((1-self.state['menu_selected'])%2)+['accept'])
        for _ in range(128):
            if self.state['mode']=='local-exploration':break
            self.advance(['idle']*8 if self.state['animation']['active'] else ['accept'])
        self.note('rick-device')

    def invasion(self):
        # Try bounded ordinary waits outdoors, where the original NPC clock
        # actually runs. Each trial resumes the same real checkpoint, answers
        # its own quiz and finishes startup. Only its ordinary inputs are used
        # in the final route; no state/RNG bytes are patched or imported.
        for delay in range(32):
            trial=object.__new__(Enhanced);trial.__dict__=dict(self.__dict__)
            trial.work=self.work/('invasion-trial-'+str(delay));trial.work.mkdir()
            trial.slot=trial.work/'current.btp';trial.leg=trial.work/'leg.actions';shutil.copy2(self.slot,trial.slot)
            trial.actions=list(self.actions);trial.notes=list(self.notes);trial.checkpoints=trial.notes
            trial.next_loan(delay);trial.launch()
            if trial.state['campaign']['invasion']:
                self.advance(trial.actions[len(self.actions):]);break
        else:raise RuntimeError('No invasion in the bounded ordinary wait choices.')
        if not self.state['campaign']['invasion']:raise RuntimeError('Invasion did not begin.')
        self.story_popups();self.note('invasion-start')
        self.advance(self.helper('btp-combat-escape'))
        self.advance(['idle'])
        for _ in range(256):
            if self.state['mode']=='local-exploration':break
            self.advance(['idle']*8 if self.state['animation']['active'] else ['accept'])
        if not self.state['campaign']['owned'] or not self.state['story_flags'][4]:raise RuntimeError('Invasion escape did not retain a mech.')
        self.note('invasion-escaped');self.save_fixture('invasion')


def training(project,output,source=None):
    session=Enhanced(project,output,source)
    for assignment in range(2,6):
        if assignment!=2:session.next_loan()
        session.launch()
        if session.state['mission']['assignment']!=assignment:raise RuntimeError('Unexpected training assignment.')
        session.automatic_victory()
        session.save_fixture('training-'+str(assignment))
        if assignment==4:session.device()
    session.invasion()
    return session


def generate(project,output,resume_route=None,source=None):
    if resume_route is None:s=training(project,output,source)
    else:
        # Reuse a retained input prefix for planner iteration. It is replayed
        # from a fresh game, never loaded as an imported/edited save.
        s=object.__new__(Enhanced);s.project=Path(project).resolve();s.work=Path(output).resolve();s.work.mkdir()
        s.original_data=Path(source or ROOT/'Original DOS').resolve()
        s.binary=ROOT/'build/btech-headless';s.slot=s.work/'current.btp';s.leg=s.work/'leg.actions'
        s.actions=Path(resume_route).read_text().splitlines();s.notes=[];s.checkpoints=s.notes
        s.leg.write_text('\n'.join(s.actions)+'\n');s.state=s.execute('--replay',s.leg,'--save',s.slot)
        if s.state['combat_rules']!='enhanced' or not s.state['story_flags'][4]:raise RuntimeError('Expected an Enhanced invasion-escape input prefix.')
    from make_later_campaign_replay import main as recruits
    from make_story_replay import main as companions
    from make_cache_replay import finish
    recruits(s,speed_shop=False);companions(s)
    if sum(p[0]!=255 for p in s.state['people'])!=5:raise RuntimeError('Enhanced full party not recruited.')
    s.travel_crew();s.advance(['credit-10000']);s.upgrade(1300,1092,2,9);s.upgrade(1184,1443,3,10)
    s.enter(1553,1545);s.settle_building()
    if not s.state['campaign_flags'][50]:raise RuntimeError('Missing Enhanced disk prerequisite.')
    s.enter(522,390);s.settle_building()
    if not all(s.state['campaign_flags'][i] for i in (53,54)):raise RuntimeError('Missing Enhanced password prerequisites.')
    finish(s,output=s.work/'complete',prerequisite='Fresh Updated start, default Enhanced throughout. Drive/recovery and four training victories, Rick/device, invasion escape, five-person party, paid apprenticeships and all cache doors. Ordinary inputs including bounded outdoor wait planning and owner-authorized credits; no state/RNG/rule edits.')
    return s.work/'complete.actions'


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--project',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--data',type=Path,default=ROOT/'Original DOS',help='Supported DOS source used to plan quiz/cache answers.')
    parser.add_argument('--training-only',action='store_true');parser.add_argument('--resume-route',type=Path,help='Replan from a retained ordinary-input invasion prefix; it is still replayed from a fresh game.')
    args=parser.parse_args()
    training(args.project,args.output,args.data) if args.training_only else generate(args.project,args.output,args.resume_route,args.data)
