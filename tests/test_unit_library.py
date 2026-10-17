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
from unit_library import UnitLibrary,closure,import_units,stage_preview
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
        with self.assertRaisesRegex(EditorError,'CHI sprites'):import_units(self.game,[bundle])
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


if __name__=='__main__':unittest.main()
