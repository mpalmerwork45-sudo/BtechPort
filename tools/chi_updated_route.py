"""Produce a private input-only Updated campaign with Legacy selected in-game.

Enhanced remains the edition default. This bounded full-campaign acceptance
route deliberately chooses its supported Legacy setting, then replans travel
and the cache using the actual project/save. It never edits state or RNG.
Enhanced combat has separate prepared mission and multiple-unit regressions.
"""
from pathlib import Path
import json,subprocess
from make_fresh_campaign_replay import Fresh,ROOT
from make_later_campaign_replay import Later,main as recruits
from make_story_replay import main as companions
from make_cache_replay import finish

class Updated(Fresh,Later):
    def __init__(self,project,output):
        self.project=Path(project).resolve();self.work=Path(output).resolve();self.work.mkdir()
        self.source='fresh Updated project; Legacy selected through settings'
        self.binary=ROOT/'build/btech-headless';self.slot=self.work/'current.btp';self.leg=self.work/'leg.actions'
        self.checkpoints=[];self.notes=self.checkpoints
        self.actions=['menu','down','accept']+['down']*4+['accept','down','accept','cancel']
        self.actions+=(ROOT/'tests/fixtures/ordinary-invasion.actions').read_text().splitlines()
        self.leg.write_text('\n'.join(self.actions)+'\n')
        self.state=self.execute('--replay',self.leg,'--save',self.slot)
        if self.state['combat_rules']!='legacy' or not self.state['story_flags'][4] or not self.state['campaign']['owned']:
            raise RuntimeError('Updated training/escape did not complete under its selected Legacy rules.')
        self.note('training-and-escape-legacy')
    def execute(self,*args):
        result=subprocess.run([str(self.binary),'--project',str(self.project),*map(str,args)],capture_output=True,text=True,timeout=120)
        if result.returncode:raise RuntimeError(result.stderr)
        return json.loads(result.stdout)
    def probe(self,keys):
        self.leg.write_text('\n'.join(keys)+'\n');return self.execute('--load',self.slot,'--replay',self.leg)
    def advance(self,keys):
        if not keys:return
        self.leg.write_text('\n'.join(keys)+'\n');self.state=self.execute('--load',self.slot,'--replay',self.leg,'--save',self.slot)
        self.actions.extend(keys)
        if self.state['mode'] in ('script-error','game-over'):raise RuntimeError('Updated route stopped: '+self.state['mode'])
    def helper(self,binary,*args):
        result=subprocess.run([str(ROOT/'build'/binary),str(self.slot),*map(str,args),'--project',str(self.project)],capture_output=True,text=True,timeout=120)
        if result.returncode:raise RuntimeError(result.stderr)
        return result.stdout.splitlines()
    def world_route(self,x,y):self.advance(self.helper('btp-world-route',x,y))
    def route(self,kind,index=0,probe=False):
        try:keys=self.helper('btp-cache-route',kind,index)
        except RuntimeError:
            if probe:return False
            raise
        if probe:return True
        self.advance(keys)
    def save_fixture(self,name):
        (self.work/(name+'.actions')).write_text('\n'.join(self.actions)+'\n')
        print('Updated '+name+': '+str(len(self.actions))+' inputs',flush=True)

def generate(project,output):
    s=Updated(project,output);recruits(s);companions(s)
    if sum(p[0]!=255 for p in s.state['people'])!=5:raise RuntimeError('Updated full party not recruited.')
    s.travel_crew();s.advance(['credit-10000']);s.upgrade(1300,1092,2,9);s.upgrade(1184,1443,3,10)
    s.enter(1553,1545);s.settle_building()
    if not s.state['campaign_flags'][50]:raise RuntimeError('Missing disk prerequisite.')
    s.enter(522,390);s.settle_building()
    if not all(s.state['campaign_flags'][i] for i in (53,54)):raise RuntimeError('Missing password prerequisite.')
    finish(s,output=s.work/'complete',prerequisite='Fresh Updated start; ordinary Settings selects Legacy. Training, escape, five companions, apprenticeships and cache. Owner-authorized money inputs only; no state/RNG edits.')
    return s.work/'complete.actions'

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    generate(a.project,a.output)
