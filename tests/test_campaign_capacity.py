"""Campaign bounds, high handles and actual old/new saved continuations."""
import copy
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from editor_model import ProjectDocument,EditorError,create_project,encoded
from campaign_capacity import campaign,scenario
from campaign_limits import EXPANDED,LEGACY,upgrade_campaign,schema
from campaign_source import convert,build
from authoring_contract import check
from authoring_service import apply_batch,revision
from authoring_inspect import summary,capabilities
from authoring_scenarios import run
from save_migration import compatible
TOOL=Path(os.environ.get('BTP_PROJECT_TOOL',ROOT/'build/btp-project'))
PLAYER=ROOT/'build/btech-headless'
RUNNER=ROOT/'build/btp-author-playtest'


def maximum_campaign():
    a=campaign(1)
    for key,maximum in EXPANDED.items():
        while len(a[key])<maximum:
            record=copy.deepcopy(a[key][-1]);record['id']=f'capacity:{key}-{len(a[key])}'
            if key=='maps':record['entrances']=[]
            a[key].append(record)
    # Exercise 64 full-size local maps AND all 256 generated sectors. The
    # last city's active sector is 319, beyond both byte and old scene bounds.
    a['worlds']=[dict(id='capacity:large-world',name='Capacity planet',
        pieces=[['capacity:plain']*128 for _ in range(128)],patches=[],cities=[m['id'] for m in a['maps']])]
    for i,m in enumerate(a['maps']):
        m['rows']=[['beacon:grass']*64 for _ in range(64)]
        m['origin']=[128*(i%8),128*(i//8)]
    a['maps'][-1]['origin']=[960,960]
    return a


class CampaignCapacity(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='btp-capacity-');self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.doc=create_project(ROOT/'examples/beacon-demo',self.root/'game','capacity-test','Capacity test',TOOL)

    def play(self,doc,*args,ok=True):
        p=subprocess.run([str(PLAYER),'--project',str(doc.root),*map(str,args)],capture_output=True,text=True,timeout=20)
        self.assertEqual(p.returncode==0,ok,p.stderr)
        return p

    def route(self,steps,name='run'):
        result=run(self.doc,dict(format='btp-author-scenario-v1',steps=steps),self.root/name,RUNNER)
        self.assertEqual(result['status'],'passed',result)
        return result

    def test_twenty_contracts_from_sources_and_all_checkpoints(self):
        self.doc.replace_adventure(campaign());self.doc.save();check(self.doc.adventure,schema())
        source=convert(self.doc,self.root/'source');a=build(source,self.root/'built');b=build(source,self.root/'again')
        self.assertEqual(a['files'],b['files']);self.assertEqual(a['fingerprint'],b['fingerprint'])
        result=run(source,scenario(),self.root/'contracts',RUNNER)
        self.assertEqual(result['status'],'passed',result)
        state=result['result']['state'];self.assertEqual(state['credits'],4000)
        self.assertTrue(all(v=='complete' for v in state['objectives'].values()))
        self.assertEqual(len(state['objectives']),40)
        self.assertTrue(all(v==1 for v in state['variables'].values()))
        saved=(self.root/'contracts'/result['result']['save']).read_bytes()
        self.assertEqual(saved[164],52)
        self.assertTrue(any(saved[160+512+4:160+512+100]))  # once-only events beyond 255

    def test_maximum_definitions_and_one_beyond_each_limit(self):
        maximum=maximum_campaign();self.doc.replace_adventure(maximum);self.doc.validate()
        for key,limit in EXPANDED.items():
            with self.subTest(collection=key):
                bad=copy.deepcopy(maximum);extra=copy.deepcopy(bad[key][-1]);extra['id']='capacity:overflow'
                bad[key].append(extra);self.doc.replace_adventure(bad)
                with self.assertRaisesRegex(EditorError,rf'\$.{key}\['):self.doc.validate()
        self.doc.replace_adventure(maximum)

    def test_legacy_formats_do_not_silently_expand(self):
        base=campaign(1,2)
        for key,limit in LEGACY.items():
            with self.subTest(collection=key):
                bad=copy.deepcopy(base)
                while len(bad[key])<=limit:
                    extra=copy.deepcopy(bad[key][-1]);extra['id']=f'capacity:extra-{len(bad[key])}'
                    bad[key].append(extra)
                self.doc.replace_adventure(bad)
                with self.assertRaises(EditorError):self.doc.validate()

    def test_last_event_variable_objective_scene_and_once_bits_survive_reload(self):
        a=maximum_campaign();ids=[f'capacity:node-{i}' for i in range(1024)]
        a['events']=[dict(id=k,op='end') for k in ids]
        for m in a['maps']:m['entrances']=[]
        var=a['variables'][-1]['id'];obj=a['objectives'][-1]['id']
        a['events'][1020]=dict(id=ids[1020],op='variable',variable=var,action='add',value=1,once=1,next=ids[1021],failure=ids[1])
        a['events'][1021]=dict(id=ids[1021],op='objective',objective=obj,state='complete',next=ids[1022],failure=ids[1])
        a['events'][1022]=dict(id=ids[1022],op='reward',credits=5,next=ids[1023],failure=ids[1])
        a['events'][1023]=dict(id=ids[1023],op='choice',text='Checkpoint at the highest handles.',
            options=[dict(label='Repeat',next=ids[1020]),dict(label='Leave',next=ids[0])],cancel=ids[0])
        a['start'].update(map=a['maps'][-1]['id'],event=ids[1020],credits=0)
        self.doc.replace_adventure(a);self.doc.save()
        result=self.route([dict(op='assert',credits=5,variable=var,value=1,objective=obj,status='complete'),
            dict(op='checkpoint'),dict(op='choose',label='Repeat'),dict(op='assert',credits=5,variable=var,value=1),
            dict(op='checkpoint'),dict(op='choose',label='Leave'),dict(op='checkpoint'),
            dict(op='input',action='menu'),dict(op='input',action='down',repeat=7),
            dict(op='input',action='accept'),dict(op='input',action='up'),dict(op='checkpoint'),dict(op='capture')])
        self.assertEqual(result['result']['state']['map'],'world:planet-1-sector-15-15')
        saved=(self.root/'run'/result['result']['save']).read_bytes()
        self.assertEqual(struct.unpack_from('<H',saved,160+20057+112)[0],319)
        self.assertEqual(saved[160+512+99],0x50)  # variable 1020 and payment 1022, once each
        self.assertEqual(saved[160+2667],127)  # Journal page 128, held across save/reload.

    def test_corrupt_extension_and_downgraded_save_are_rejected(self):
        self.doc.replace_adventure(campaign());self.doc.save()
        save=self.root/'save.btp';self.play(self.doc,'--save',save);original=save.read_bytes()
        for offset,value in [(160+512,2),(160+514,1),(160+512+1023,1),(160+512+484,4),
                             (160+512+100,255),(164,51)]:
            with self.subTest(offset=offset):
                data=bytearray(original);data[offset]=value
                if offset==160+512+100:data[offset:offset+4]=b'\xff'*4
                if offset==164:data[160:164]=b'BTPp'
                struct.pack_into('<I',data,8,zlib.crc32(data[16:]));bad=self.root/'bad.btp';bad.write_bytes(data)
                self.play(self.doc,'--load',bad,ok=False)
        self.assertEqual(save.read_bytes(),original)

    def test_optional_combat_mission_state_with_extended_events(self):
        a=campaign(1)
        while len(a['encounters'])<64:
            enemy=copy.deepcopy(a['encounters'][0]);enemy['id']=f'capacity:encounter-{len(a["encounters"])}';a['encounters'].append(enemy)
        next(e for e in a['events'] if e['op']=='battle')['encounter']=a['encounters'][-1]['id']
        a['events']=[dict(id=f'capacity:padding-{i}',op='end') for i in range(300)]+a['events']
        a['combat_hooks']=[dict(id='capacity:hook',encounter=a['encounters'][-1]['id'],when='start',repeat='once',event='capacity:end')]
        self.doc.replace_adventure(a);self.doc.save()
        result=run(self.doc,scenario(1),self.root/'combat',RUNNER)
        self.assertEqual(result['status'],'passed',result)
        data=(self.root/'combat'/result['result']['save']).read_bytes();self.assertEqual(data[160+513],1)
        self.assertEqual(data[160+4096+5600+3],63)

    def test_old_real_save_fixtures_resave_identically_and_upgrade_refuses_them(self):
        for version in (49,50,51):
            with self.subTest(version=version):
                if version==49:old=ProjectDocument(ROOT/'examples/beacon-demo',TOOL)
                else:
                    old=create_project(ROOT/'examples/beacon-demo',self.root/f'old-{version}',
                        'capacity-8' if version==50 else 'capacity-hooks','Capacity 8' if version==50 else 'Capacity hooks',TOOL)
                    a=campaign(8,2)
                    if version==51:a['combat_hooks']=[dict(id='capacity:start-hook',encounter='capacity:c01-patrol-fight',when='start',repeat='once',event='capacity:end')]
                    old.replace_adventure(a);old.save()
                fixture=ROOT/f'tests/fixtures/capacity-v{version}.btp';out=self.root/f'resaved-{version}.btp'
                self.play(old,'--load',fixture,'--save',out);self.assertEqual(out.read_bytes(),fixture.read_bytes())
                updated=copy.deepcopy(old);upgrade_campaign(updated)
                with self.assertRaisesRegex(EditorError,'format upgrades'):compatible(old,updated)
                updated.stage(self.root/f'upgraded-{version}');new=ProjectDocument(self.root/f'upgraded-{version}',TOOL)
                self.assertIn('exact saved content',self.play(new,'--load',fixture,ok=False).stderr)

    def test_upgrade_command_undo_capabilities_and_same_version_art_operations(self):
        before=copy.deepcopy(self.doc.adventure);self.assertEqual(summary(self.doc,TOOL)['capacity']['maps']['limit'],16)
        request=dict(api_version=1,request_id='capacity-upgrade',project_id=self.doc.manifest['package_id'],
            expected_revision=revision(self.doc),label='Upgrade capacity',scope=['adventure'],operations=[dict(op='campaign.upgrade')])
        apply_batch(self.doc,request);self.assertEqual(self.doc.adventure['schema_version'],3)
        self.assertEqual(summary(self.doc,TOOL)['capacity']['maps']['limit'],64)
        self.doc.undo();self.assertEqual(self.doc.adventure,before);self.doc.redo()
        from world_editing import create_world
        a=copy.deepcopy(self.doc.adventure);create_world(a,'capacity',8,8,'Additional planet')
        self.assertEqual(a['schema_version'],3);self.doc.replace_adventure(a);self.doc.validate()
        caps=capabilities(TOOL)['runtime'];self.assertEqual(caps['format_requirements']['btp-adventure-v3']['save_version'],52)
        for key,maximum in EXPANDED.items():self.assertEqual(caps['limits'][key],maximum)

    def test_unplaced_maps_get_distinct_discovery_without_planets(self):
        a=campaign(1);a.pop('worlds');a['start']['event']='capacity:end'
        a['maps'][1]['origin']=a['maps'][0]['origin'][:]
        self.doc.replace_adventure(a);self.doc.save();save=self.root/'local.btp'
        self.play(self.doc,'--save',save);first=save.read_bytes()
        # The other map has its own bitmap allocation even at identical XY.
        a['start']['map']=a['maps'][1]['id'];self.doc.replace_adventure(a);self.doc.save()
        second=self.root/'other.btp';self.play(self.doc,'--save',second)
        offset=lambda data:struct.unpack_from('<H',data,160+20057+117)[0]
        self.assertEqual(offset(first),0);self.assertEqual(offset(second.read_bytes()),12)


if __name__=='__main__':unittest.main()
