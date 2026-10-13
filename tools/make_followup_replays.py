#!/usr/bin/env python3
"""Regenerate dependent ordinary follow-up routes in their prerequisite order."""
import argparse,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--training',action='store_true',help='Regenerate combat prerequisites and both invasion routes first')
args=parser.parse_args()
if args.training:
    for tool,arguments in (
        ('make_combat_replay.py',['--generate']),
        ('make_training_combat_replay.py',['--generate']),
        ('make_training_combat_replay.py',['--kick','--generate']),
        ('make_training_combat_replay.py',['--campaign','--generate']),
        ('make_campaign_replay.py',['4','0']),
        ('make_campaign_replay.py',['4','0','--loss'])):
        print('Generating',tool,*arguments,flush=True)
        subprocess.run([sys.executable,str(ROOT/'tools'/tool),*arguments],cwd=ROOT,check=True)
for tool in ('make_later_campaign_replay.py','make_story_replay.py',
             'make_hospital_healing_replay.py','make_late_building_replays.py',
             'make_prison_replay.py','make_arena_replay.py','make_cache_replay.py'):
    print('Generating',tool,flush=True)
    subprocess.run([sys.executable,str(ROOT/'tools'/tool)],cwd=ROOT,check=True)
