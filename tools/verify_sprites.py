#!/usr/bin/env python3
"""Verify sprite crops, original walking frames, palette/placement and persistence.

Export only numeric observations and hashes, never original asset pixels.
The RAM export is an independent oracle: dimensions/pixels come from the EXE's
allocated planar sprites, not the port's atlas-rectangle calculations.
"""
import argparse
import hashlib
import json
import struct
import subprocess
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/reference-sprites.json'
WORK = ROOT / 'work/sprite-verification'


def check(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def export(atlas_run, walk_run):
    from PIL import Image
    row = json.loads((atlas_run/'start-state.json').read_text())
    ram = (atlas_run/'start-ram.bin').read_bytes()
    ds = int(row['data_segment'], 16)*16
    def word(at): return struct.unpack_from('<H', ram, at)[0]
    segment = word(ds+0x539e)*16
    crops = []
    for sid in range(376):
        at = segment+0x39fa+4*sid
        p = word(at)+16*word(at+2)
        w, h = ram[p+2]*8, ram[p+1]+1
        check(w in (8, 16, 24) and 1 <= h <= 24, 'Invalid original sprite header')
        data = bytes(sum(((ram[p+4+y*w//2+x//8*4+j] >> (7-x%8)) & 1) << j
                         for j in range(4)) for y in range(h) for x in range(w))
        crops.append({'id': sid, 'width': w, 'height': h, 'sha256': sha(data)})
    directions = []
    for i in range(8):
        at = ds+0x27a+4*i
        p = word(at)+16*word(at+2)
        check(ram[p:p+2] == bytes([253, i]) and ram[p+6:p+8] == bytes([254, 5]), 'Human animation program differs')
        directions.append(list(ram[p+2:p+6]))
    movement = json.loads((ROOT/'tests/fixtures/reference-movement.json').read_text())
    walks = []
    for step in movement['steps']:
        r = json.loads((walk_run/(step['label']+'-state.json')).read_text())
        check(r['sprite_bases'][4] == 150, 'Jason palette group differs')
        walks.append({'action': step['action'], 'label': step['label'],
                      'position': [v & 127 for v in r['cursor_raw']], 'sprite': 150+r['sprite_frames'][4]})
    pixels = []
    for shot, label in [('start','start'), ('wall','up5'), ('hedge','down7'), ('west-wall','return-down3')]:
        im = Image.open(walk_run/'captures'/(shot+'.png')).convert('RGB').crop((208,96,216,104))
        pixels.append({'label': label, 'sha256': sha(im.tobytes())})
    frames = json.loads((atlas_run/'sprites-frames.json').read_text())['frames']
    data = {'evidence': {'atlas_run': atlas_run.name, 'walk_run': walk_run.name,
            'ram_sha256': sha(ram), 'executable_sha256': sha((ROOT/'Original DOS/BTECH.EXE').read_bytes()),
            'atlas_sha256': sha((ROOT/'Original DOS/MECHSHAP.CMP').read_bytes()),
            'note': 'Walk run completed all checkpoints; its later 12-second wait was rejected. Separate 10-second trace completed.'},
            'crops': crops, 'human_directions': directions, 'walk': walks, 'player_pixels': pixels, 'outdoor_frames': frames}
    # Compact each observation, retaining readable evidence metadata and lists.
    sections = []
    for key, value in data.items():
        encoded = ('[\n    '+',\n    '.join(json.dumps(row) for row in value)+'\n  ]') if isinstance(value,list) else json.dumps(value,indent=2)
        sections.append('  '+json.dumps(key)+': '+encoded)
    FIXTURE.write_text('{\n'+',\n'.join(sections)+'\n}\n')
    print('Exported 376 RAM crop hashes, walking checkpoints and stable outdoor frames.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, default=ROOT/'build/btech-headless')
    parser.add_argument('--export-atlas-run', type=Path)
    parser.add_argument('--export-walk-run', type=Path)
    args = parser.parse_args()
    if args.export_atlas_run:
        check(args.export_walk_run, 'Both reference runs are required')
        export(args.export_atlas_run, args.export_walk_run)
    fixture = json.loads(FIXTURE.read_text())
    WORK.mkdir(parents=True, exist_ok=True)
    binary = str(args.binary.resolve())
    def run(*options):
        return subprocess.run([binary, *map(str, options)], cwd=ROOT, check=True,
                              text=True, capture_output=True, timeout=20).stdout
    check(sha((ROOT/'Original DOS/MECHSHAP.CMP').read_bytes()) == fixture['evidence']['atlas_sha256'], 'Atlas source differs')
    crops = WORK/'crops.bin'
    run('--export-sprites', crops)
    data, at = crops.read_bytes(), 4
    check(data[:4] == b'BTSP', 'Bad sprite export')
    pixels = 0
    for row in fixture['crops']:
        w, h = data[at:at+2]; at += 2
        check([w,h] == [row['width'],row['height']] and sha(data[at:at+w*h]) == row['sha256'], f"Sprite {row['id']} differs from original RAM")
        at += w*h; pixels += w*h
    check(at == len(data), 'Unexpected trailing crop data')
    actions = WORK/'walk.actions'
    actions.write_text(''.join(r['action']+'\n' for r in fixture['walk']))
    states = [json.loads(s) for s in run('--replay', actions, '--trace').splitlines()]
    for row, state in zip(fixture['walk'], states[1:], strict=True):
        check([state['x_half'],state['y_half']] == row['position'] and state['player_sprite'] == row['sprite'], f"Player walking frame differs: {row['label']}")
    # PPM is emitted by our frontend; no Pillow dependency for normal checks.
    for row in fixture['player_pixels']:
        tick = next(i+1 for i,s in enumerate(fixture['walk']) if s['label'] == row['label'])
        actions.write_text(''.join(r['action']+'\n' for r in fixture['walk'][:tick]))
        path = WORK/(row['label']+'.ppm')
        run('--replay',actions,'--frame',path)
        ppm = path.read_bytes(); check(ppm.startswith(b'P6\n320 200\n255\n'), 'Unexpected PPM format')
        rgb = ppm[len(b'P6\n320 200\n255\n'):]
        crop = b''.join(rgb[(y*320+208)*3:(y*320+216)*3] for y in range(96,104))
        check(sha(crop) == row['sha256'], f"Original player pixel crop differs: {row['label']}")
    # Seed one canonical observed state, then run an uninterrupted idle trace.
    start = fixture['outdoor_frames'][0]
    slot = WORK/'start.btp'; run('--save',slot)
    payload = bytearray(slot.read_bytes()[16:])
    def put16(at, value): struct.pack_into('<H',payload,at,value)
    def put32(at, value): struct.pack_into('<I',payload,at,value)
    put16(12,start['cursor'][0]&127); put16(14,start['cursor'][1]&127)
    payload[151] = start['phase']; payload[153:156] = bytes(start['rng'])
    put16(156,start['search'][0]); payload[158] = start['search'][1]
    payload[200] = start['loop_timer']; put32(224,start['credits']); put16(228,start['allowance_cap'])
    payload[201] = int(start['credits']+sum(start['investments']) < start['allowance_cap'])
    for i in range(3): put32(320+4*i,start['investments'][i])
    payload[394] = start['sprite_frames'][4]-16
    for i,n in enumerate(start['npcs']):
        payload[128+2*i:130+2*i] = bytes(n['pair'])
        put16(160+5*i,n['position'][0]); put16(162+5*i,n['position'][1]); payload[164+5*i] = n['direction']
        payload[395+i] = start['sprite_frames'][16+i]-16
    slot.write_bytes(b'BTS1'+struct.pack('<III',len(payload),zlib.crc32(payload),0)+payload)
    total = 0
    for a,b in zip(fixture['outdoor_frames'],fixture['outdoor_frames'][1:]):
        check((a['loop_timer']-b['loop_timer'])%256 == 1, 'Original animation trace has a gap')
        total += 4
    actions.write_text('idle\n'*total)
    states = [json.loads(s) for s in run('--load',slot,'--replay',actions,'--trace').splitlines()]
    for i,row in enumerate(fixture['outdoor_frames']):
        state = states[4*i]
        check(state['npc_sprites'] == [254+f for f in row['sprite_frames'][16:24]], f'NPC animation differs at frame {i}')
        check(state['npcs'] == [n['position']+[n['direction']] for n in row['npcs']] and
              state['npc_rng'] == row['rng'] and state['npc_phase'] == row['phase'], f'NPC state differs at frame {i}')
    # A fresh process restores an intermediate animation frame, then continues.
    actions.write_text('idle\n'*73)
    resumed = WORK/'resumed.btp'; run('--load',slot,'--replay',actions,'--save',resumed)
    actions.write_text('idle\n'*(total-73))
    check(json.loads(run('--load',resumed,'--replay',actions)) == states[-1], 'Animation/save continuation differs')
    print(f"PASS: {len(fixture['crops'])} original RAM sprites / {pixels} pixels; {len(fixture['walk'])} walking checkpoints; four exact 8x8 player crops; {len(fixture['outdoor_frames'])-1} full NPC animation frame steps; process-restarted animation.")


if __name__ == '__main__':
    main()
