"""Library edits and cross-project imports use the real shared validator/player."""
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from editor_model import ProjectDocument,EditorError
from unit_library import UnitLibrary,closure,import_units,stage_preview,needs_original,preview_files
from library_defaults import apply_sprite_defaults
from app_runtime import default_settings,game_command

TOOL=Path(os.environ.get('BTP_PROJECT_TOOL',ROOT/'build/btp-project'))
PLAYER=Path(os.environ.get('BTP_HEADLESS',ROOT/'build/btech-headless'))


class UnitLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='unit-library-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.library=UnitLibrary(self.root/'library',TOOL)
        shutil.copytree(ROOT/'examples/beacon-demo',self.root/'game');self.game=ProjectDocument(self.root/'game',TOOL)
        self.vehicles=ProjectDocument(ROOT/'examples/vehicle-lab',TOOL)

    def vehicle(self,name='patton'):return closure(self.vehicles,'vehicles:'+name,'Vehicles')

    def test_preview_terrain_is_independent_of_edited_demo_map(self):
        from unittest.mock import patch
        from unit_library import read_json
        def edited(path):
            value=read_json(path)
            if path.name=='adventure.json':
                value['schema_version']=2
                value['tiles']=[dict(id='edited:tile',sheet='package:art',graphic='edited:missing',terrain='clear',mini_color=2)]
                value['maps'][0]['rows']=[['edited:tile']*32 for _ in range(24)]
                value['worlds']=[{'id':'edited:world'}]
            return value
        bundle=self.vehicle()
        with patch('unit_library.read_json',side_effect=edited):
            self.library.validate(bundle)
            adventure=preview_files(bundle)['adventure.json']
        self.assertEqual(adventure['schema_version'],1)
        self.assertEqual(adventure['maps'][0]['rows'],['.'*32 for _ in range(24)])
        self.assertNotIn('worlds',adventure)

    def test_local_edit_revision_and_external_conflict(self):
        saved=self.library.save(self.vehicle());stage_preview(saved,self.root/'edit')
        draft=ProjectDocument(self.root/'edit',TOOL);content=copy.deepcopy(draft.content)
        content['mechs'][0]['price']=9876;draft.replace(content)
        revised=self.library.export_unit(draft,saved['definition'],'Vehicles',expected=saved)
        self.assertEqual(revised['revision'],2)
        self.assertEqual(self.vehicles.content['mechs'][0]['price'],24750)
        with self.assertRaisesRegex(EditorError,'changed'):
            self.library.save(saved,expected=saved)
        self.assertEqual(self.library.entries()[0],revised)

    def test_variant_is_distinct_and_imports_without_replacing_source(self):
        source=self.library.save(self.vehicle());variant=self.library.save(source,variant=True)
        self.assertNotEqual(source['definition'],variant['definition'])
        result=import_units(self.game,[source,variant]);self.assertEqual(len(result),2)
        self.game.save();self.assertEqual(len(self.game.content['mechs']),5)

    def test_import_includes_equipment_ammunition_and_owned_sprite(self):
        imported=import_units(self.game,[self.vehicle()]);self.assertEqual(imported,[('Vehicles','vehicles:patton')])
        self.game.save();reopened=ProjectDocument(self.game.root,TOOL)
        self.assertEqual(reopened.art,self.game.art)
        self.assertTrue(reopened.metadata['LIBRARY-SOURCES.json'])
        a=copy.deepcopy(self.game.adventure);a['start']['party'][0]['mech']='vehicles:patton';self.game.replace_adventure(a);self.game.save()
        result=subprocess.run([str(PLAYER),'--project',str(self.game.root),'--save',str(self.root/'game.btp')],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        # Equipment is part of the dependency closure, not an unrelated roster.
        from unit_editing import add_equipment
        c=copy.deepcopy(self.game.content);equipment=add_equipment(c)
        c['mechs'][0]['equipment']=[dict(definition=equipment,location='left_torso',quantity=1)]
        self.game.replace(c);bundle=closure(self.game,c['mechs'][0]['id'])
        self.assertEqual(bundle['content']['equipment'][0]['id'],equipment)
        self.library.validate(bundle)

    def test_shared_weapon_collision_does_not_change_other_units(self):
        import_units(self.game,[self.vehicle(),self.vehicle('rommel')]);before=copy.deepcopy(self.game.content)
        changed=self.vehicle();weapon=changed['content']['weapons'][0];weapon['damage']-=1
        imported=import_units(self.game,[changed],'replace');self.assertEqual(len(imported),1)
        untouched=next(m for m in self.game.content['mechs'] if m['id']=='vehicles:rommel')
        self.assertEqual(untouched,next(m for m in before['mechs'] if m['id']=='vehicles:rommel'))
        patton=next(m for m in self.game.content['mechs'] if m['id']=='vehicles:patton')
        self.assertNotEqual(patton['loadout'][0]['weapon'],weapon['id'])
        self.assertEqual(next(w for w in self.game.content['weapons'] if w['id']==weapon['id']),
                         next(w for w in before['weapons'] if w['id']==weapon['id']))
        self.game.validate()

    def test_import_undo_after_save_clears_attribution_and_redo_restores(self):
        original=copy.deepcopy(self.game.content);import_units(self.game,[self.vehicle()]);self.game.save()
        self.game.undo();self.game.save();reopened=ProjectDocument(self.game.root,TOOL)
        self.assertEqual(reopened.content,original)
        self.assertEqual(json.loads(reopened.metadata['LIBRARY-SOURCES.json']),[])
        self.game.redo();self.game.save();reopened=ProjectDocument(self.game.root,TOOL)
        self.assertEqual(json.loads(reopened.metadata['LIBRARY-SOURCES.json'])[0]['definition'],'vehicles:patton')
        self.game.export(self.root/'export')
        self.assertEqual(ProjectDocument(self.root/'export',TOOL).metadata,reopened.metadata)

    def test_invalid_and_incompatible_imports_leave_document_untouched(self):
        invalid=self.vehicle();invalid['content']['mechs'][0]['movement']['walk']=99
        before=(copy.deepcopy(self.game.content),copy.deepcopy(self.game.art),copy.deepcopy(self.game.metadata))
        with self.assertRaises(EditorError):import_units(self.game,[invalid])
        self.assertEqual(before,(self.game.content,self.game.art,self.game.metadata))
        self.assertFalse(self.game.undo_stack)
        chi=ProjectDocument(ROOT/'examples/battletech-demo',TOOL);bundle=closure(chi,chi.content['mechs'][0]['id'])
        with self.assertRaisesRegex(EditorError,'CHI sprites'):import_units(self.game,[bundle],'variant')
        self.assertFalse(self.game.dirty)

    def test_infantry_variants_get_free_actor_identities(self):
        character=closure(self.game,self.game.adventure['people'][0]['id'],'Infantry')
        result=import_units(self.game,[character],'variant');self.assertEqual(result[0][0],'Infantry')
        people=self.game.adventure['people'];self.assertEqual(len(people),3)
        self.assertEqual(len({p['identity'] for p in people}),3)
        self.game.save()

    def test_independent_sprite_transfers_into_chi_project_as_owned_art(self):
        bundle=closure(self.game,self.game.content['mechs'][0]['id'])
        shutil.copytree(ROOT/'examples/battletech-demo',self.root/'chi');target=ProjectDocument(self.root/'chi',TOOL)
        import_units(target,[bundle]);target.save()
        unit=next(m for m in target.content['mechs'] if m['id']==bundle['definition'])
        presentation=next(p for p in target.content['presentations'] if p['id']==unit['presentation'])
        self.assertEqual(presentation['source'],'package:art')
        self.assertTrue(any(i['id']==presentation['image'] for i in target.art['images']))

    def test_original_blueprints_export_and_validate(self):
        result=subprocess.run([str(TOOL),'export-original-units',str(self.root/'original.json'),
                               '--combat-data',str(ROOT/'work/combat-data.bin')],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        valid=subprocess.run([str(TOOL),'validate-content',str(self.root/'original.json')],capture_output=True,text=True,timeout=20)
        self.assertEqual(valid.returncode,0,valid.stderr)
        content=json.loads((self.root/'original.json').read_text())
        self.assertIn('LOCUST',[m['name'] for m in content['mechs']])
        self.assertIn('STINGER',[m['name'] for m in content['mechs']])

    def test_launcher_resume_namespaces_and_no_original_dependency(self):
        paths=default_settings();paths['player']=str(PLAYER);paths['data']=str(self.root/'absent')
        command=game_command('My project',paths,self.root/'launch',self.game.root)
        self.assertNotIn('--data',command);self.assertNotIn('--load',command)
        self.assertNotIn('--replay',command)
        with self.assertRaisesRegex(EditorError,'No quicksave'):game_command('My project',paths,self.root/'launch',self.game.root,True)
        save=Path(command[command.index('--save-file')+1]);named=save.with_name(save.stem+'-project-last-beacon.btp')
        result=subprocess.run([*command,'--save',str(named)],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        resume=game_command('My project',paths,self.root/'launch',self.game.root,True)
        self.assertEqual(Path(resume[resume.index('--load')+1]),named)

    def test_attribution_does_not_change_game_save_namespace(self):
        paths=default_settings();paths['player']=str(PLAYER)
        before=game_command('My project',paths,self.root/'launch',self.game.root)
        self.game.replace_all(self.game.content,self.game.adventure,self.game.art,self.game.manifest,
                              {'LIBRARY-SOURCES.json':b'[]\n'})
        self.game.save()
        after=game_command('My project',paths,self.root/'launch',self.game.root)
        self.assertEqual(before,after)

    def test_builtin_expansion_seeds_without_cache_and_checks_all_presets(self):
        from library_browser import seed_library
        paths=default_settings();paths['combat-data']=str(self.root/'missing-cache')
        seed_library(self.library,paths)
        entries=self.library.entries();added=[b for b in entries if b['entry_id'].startswith('mech-library:')]
        self.assertEqual(len(added),25)
        self.assertEqual(len({b['name'].split()[-1] for b in added}),25)
        for bundle in added:
            self.library.validate(bundle)
            self.assertIn('CC-BY-NC-SA-4.0',bundle['provenance']['documents']['sources.json'])
            self.assertIn('LICENSE.md',bundle['provenance']['documents'])
        self.assertEqual(seed_library(self.library,paths),0)
        self.assertEqual(self.library.entries(),entries)
        # Import every addition together, including shared ammunition/weapons.
        shutil.copytree(ROOT/'examples/battletech-demo',self.root/'chi')
        target=ProjectDocument(self.root/'chi',TOOL)
        self.assertEqual(len(import_units(target,added)),25);target.save()
        self.assertEqual(len(ProjectDocument(target.root,TOOL).content['mechs']),44)
        # A real headless game starts with newly imported light/assault designs.
        a=copy.deepcopy(target.adventure)
        for party,identity in zip(a['start']['party'],('mech-library:king-crab-kgc-0000','mech-library:spider-sdr-5v')):
            party['mech']=identity
        target.replace_adventure(a);target.save()
        paths=default_settings();paths['player']=str(PLAYER)
        command=game_command('My project',paths,self.root/'launch-new',target.root)
        actions=self.root/'walk.actions';actions.write_text('right\nidle\nright\nidle\n')
        result=subprocess.run([*command,'--replay',str(actions),'--save',str(self.root/'new.btp')],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertTrue((self.root/'new.btp').exists())

    def test_classic_catalogue_loadouts_and_ammunition_adaptations(self):
        c=json.loads((ROOT/'content/catalogues/mechs/units.json').read_text())
        units={m['name'].split()[-1]:m for m in c['mechs']};weapons={w['id']:w['behavior'] for w in c['weapons']}
        awesome=units['AWS-8Q'];self.assertEqual(awesome['engine_heat_sinks']+sum(awesome['external_heat_sinks'].values()),28)
        self.assertEqual([weapons[m['weapon']] for m in awesome['loadout']].count('ppc'),3)
        king=units['KGC-0000'];guns=[m for m in king['loadout'] if weapons[m['weapon']]=='ac20']
        self.assertEqual([m['location'] for m in guns],['left_arm','right_arm'])
        self.assertEqual(sum(m['ammunition'] for m in guns),10)
        thug=units['THG-10E'];srms=[m for m in thug['loadout'] if weapons[m['weapon']]=='srm4']
        self.assertEqual([m['ammunition'] for m in srms],[13,12])
        self.assertEqual(units['SDR-5V']['movement'],dict(walk=8,jump=8))
        self.assertEqual(len(units['BLR-1G']['loadout']),10)
        self.assertEqual(units['FFL-4A']['presentation'],'chi:locust')
        self.assertEqual(thug['presentation'],'chi:locust')
        self.assertEqual(units['CTF-1X']['presentation'],'chi:locust')
        self.assertEqual(awesome['presentation'],'chi:red-stinger')

    def test_all_new_mechs_initialize_and_fire_in_real_combat(self):
        catalogue=json.loads((ROOT/'content/catalogues/mechs/units.json').read_text())
        source=ProjectDocument(ROOT/'examples/battletech-demo',TOOL);source.replace(catalogue)
        project=self.root/'range';actions=self.root/'combat.actions'
        # Computer Yes, default messages/graphics, then a bounded real battle.
        actions.write_text('up\naccept\naccept\naccept\n'+'idle\n'*1800)
        paths=default_settings();paths['player']=str(PLAYER)
        for mech in catalogue['mechs']:
            with self.subTest(mech=mech['name']):
                bundle=closure(source,mech['id']);stage_preview(bundle,project)
                a=json.loads((project/'adventure.json').read_text());m=a['maps'][0]
                m['rows']=['.'*len(m['rows'][0]) for _ in m['rows']]
                a['encounters']=[dict(id='library:fight',map=m['id'],party_at=[24,38],
                    enemies=[dict(kind='mech',definition=mech['id'],at=[32,38])])]
                a['events'].append(dict(id='library:battle',op='battle',encounter='library:fight',
                    win='library:end',loss='library:end',flee='library:end',failure='library:end'))
                a['start']['event']='library:battle';(project/'adventure.json').write_text(json.dumps(a))
                command=game_command('My project',paths,self.root/'combat-launch',project)
                result=subprocess.run([*command,'--trace','--replay',str(actions)],capture_output=True,text=True,timeout=20)
                self.assertEqual(result.returncode,0,result.stderr)
                states=[json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
                record=states[0]['combat']['units'][0]['record']
                self.assertEqual(record[16],mech['mass_tons'])
                self.assertEqual(record[49:51],[mech['movement']['walk'],mech['movement']['jump']])
                self.assertEqual(record[124]&1,int(mech['presentation']=='chi:red-stinger'))
                self.assertTrue(any(s['combat']['round']>0 for s in states))
                self.assertTrue(any(s['combat']['fired'] and s['combat']['attacker']==0 for s in states))

    def test_sprite_migration_preserves_stats_owned_art_and_later_choices(self):
        # Simulate a library created before this increment, with edited stats.
        chi=ProjectDocument(ROOT/'examples/battletech-demo',TOOL)
        prior=closure(chi,'chi-expanded:jenner-jr7-d')
        prior['content']['mechs'][0]['price']=12345
        prior['content']['presentations'][0]['source']='chi:red-stinger'
        migrated=apply_sprite_defaults(prior)
        self.assertEqual(migrated['content']['mechs'][0]['price'],12345)
        self.assertEqual(migrated['content']['presentations'][0]['source'],'chi:locust')
        # Explicit later choices must survive subsequent library openings.
        migrated['content']['presentations'][0]['source']='chi:red-stinger'
        self.assertEqual(apply_sprite_defaults(migrated),migrated)
        custom=self.vehicle();custom['kind']='Mechs'
        self.assertEqual(apply_sprite_defaults(custom)['content'],custom['content'])
        infant=closure(self.game,self.game.adventure['people'][0]['id'],'Infantry')
        infant['graphics']['bindings']=[dict(slot='npc',image='custom:human')]
        self.assertEqual(apply_sprite_defaults(infant).get('infantry_source'),'package')

    def test_original_infantry_dependency_preview_edit_and_import(self):
        bundle=apply_sprite_defaults(closure(self.game,self.game.adventure['people'][1]['id'],'Infantry'))
        self.assertTrue(needs_original(bundle));self.library.validate(bundle)
        files=preview_files(bundle);self.assertEqual(files['project.json']['requires'],'chi-original-dos-1.03')
        self.assertNotIn('presentation',files['project.json'])
        self.assertEqual(files['graphics.json']['images'],[])
        stage_preview(bundle,self.root/'infantry')
        edited=ProjectDocument(self.root/'infantry',TOOL)
        self.assertEqual(closure(edited,bundle['definition'],'Infantry')['infantry_source'],'chi:infantry')
        with self.assertRaisesRegex(EditorError,'CHI sprites'):import_units(self.game,[bundle],'variant')
        self.assertFalse(self.game.dirty)
        shutil.copytree(ROOT/'examples/battletech-demo',self.root/'chi')
        target=ProjectDocument(self.root/'chi',TOOL)
        from art_editing import new_image,bind
        art=copy.deepcopy(target.art);image=new_image('test',art['images'],'Custom person','sprite');art['images'].append(image)
        bind(art,'npc',image['id']);bind(art,'enemy',image['id']);target.replace_art(art)
        import_units(target,[bundle],'replace',infantry_art=True)
        self.assertFalse(any(b['slot'] in ('npc','enemy') for b in target.art['bindings']))
        target.save();self.assertEqual(closure(target,bundle['definition'],'Infantry')['infantry_source'],'chi:infantry')

    def test_preexisting_library_is_migrated_once_without_replacing_edits(self):
        from library_browser import seed_library
        chi=ProjectDocument(ROOT/'examples/battletech-demo',TOOL)
        old=closure(chi,'chi-expanded:jenner-jr7-d');old['content']['mechs'][0]['price']=34567
        old['content']['presentations'][0]['source']='chi:red-stinger';self.library.save(old)
        old_person=closure(self.game,self.game.adventure['people'][0]['id'],'Infantry');self.library.save(old_person)
        paths=default_settings();paths['combat-data']=str(self.root/'missing-cache')
        seed_library(self.library,paths);entries=self.library.entries()
        jenner=next(b for b in entries if b['entry_id']==old['entry_id'])
        self.assertEqual(jenner['revision'],2);self.assertEqual(jenner['content']['mechs'][0]['price'],34567)
        self.assertEqual(jenner['content']['presentations'][0]['source'],'chi:locust')
        person=next(b for b in entries if b['entry_id']==old_person['entry_id'])
        self.assertTrue(needs_original(person));self.assertEqual(person['revision'],2)
        self.assertEqual(seed_library(self.library,paths),0);self.assertEqual(self.library.entries(),entries)


if __name__=='__main__':unittest.main()
