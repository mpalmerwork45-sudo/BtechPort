"""Recorded recipe replay, branch lifecycle, dependency and parameter contracts."""
import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from authoring_contract import AuthoringError,check
from authoring_service import apply_batch,revision
from authoring_scenarios import run,SCHEMA as SCENARIO,SUITE_SCHEMA
from authoring_analysis import graph_checks
from campaign_recipe import DEFAULT,SCHEMA,build
from campaign_source import convert,build as compile_source
from campaign_demo import dependencies,run as demonstration
from editor_model import ProjectDocument,create_project

TOOL=ROOT/'build/btp-project';RUNNER=ROOT/'build/btp-author-playtest'
SETTINGS={k:str(ROOT/p) for k,p in [('data','Original DOS'),('dialogue-data','work/talk-data.bin'),('combat-data','work/combat-data.bin'),('world-data','work/world-data.bin')]}


class CampaignRecipe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='recipe tests ');cls.root=Path(cls.tmp.name)
        cls.params=json.loads(DEFAULT.read_bytes());cls.doc,cls.report=build(cls.params,cls.root/'recorded campaign',TOOL)

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def test_expansion_and_recorded_replay(self):
        self.doc.validate();self.assertEqual(len(self.doc.adventure['maps']),5)
        self.assertEqual(graph_checks(self.doc)['diagnostics'],[])
        output=self.root/'recorded campaign';inputs=output/'inputs'
        replay=create_project(inputs/'template',self.root/'replay',self.params['package_id'],self.params['title'],TOOL)
        apply_batch(replay,json.loads((inputs/'creation.commands.json').read_bytes()),base_dir=inputs,save=True)
        modules=convert(replay,self.root/'replay source');report=compile_source(modules,self.root/'replay game')
        self.assertEqual(report['fingerprint'],self.report['package_fingerprint'])
        for file in (output/'scenarios').glob('*.json'):
            check(json.loads(file.read_bytes()),SUITE_SCHEMA if file.name=='suite.json' else SCENARIO)

    def test_parameters_reach_gameplay_and_reject_invalid_inputs(self):
        p=dict(self.params,package_id='dispatch-variant',title='Modified campaign',starting_credits=7000,repair_cost=50,
               assault_reward=1234,recovery_reward=2345,defence_reward=3456,escort_reward=4567,defence_rounds=3,seeds=[11223583])
        doc,report=build(p,self.root/'variant',TOOL)
        hooks={h['id']:h for h in doc.adventure['combat_hooks']};self.assertEqual(hooks['cairn:relay-timer']['round'],3)
        scenario=json.loads((self.root/'variant/scenarios/recovery.json').read_bytes())
        result=run(doc,scenario,self.root/'variant-route',RUNNER,SETTINGS)
        self.assertEqual(result['status'],'passed',result)
        for change in ({'defence_rounds':0},{'repair_cost':False},{'package_id':'../escape'},{'seeds':[]},{'unknown':5}):
            with self.subTest(change=change),self.assertRaises(AuthoringError):check(dict(p,**change),SCHEMA)
        with self.assertRaisesRegex(AuthoringError,'new directory'):build(p,self.root/'variant',TOOL)

    def test_both_branches_services_and_checkpoints(self):
        folder=self.root/'recorded campaign/scenarios'
        for name in ('assault','recovery','defer','retreat','abandon','defence-failure'):
            with self.subTest(route=name):
                result=run(self.doc,json.loads((folder/(name+'.json')).read_bytes()),self.root/('route-'+name),RUNNER,SETTINGS)
                self.assertEqual(result['status'],'passed',result)

    def test_missing_assets_leave_an_editable_game_and_report(self):
        result=demonstration(self.params,self.root/'no assets',TOOL,RUNNER,ROOT/'build/btp-author-analyze',{},checks=True)
        self.assertEqual(result['status'],'failed');self.assertEqual(len(result['checks']['diagnostics']),4)
        self.assertTrue(all(d['code']=='dependency.missing' for d in result['checks']['diagnostics']))
        ProjectDocument(Path(result['source']),TOOL).validate()
        self.assertTrue((self.root/'no assets/demo-report.json').is_file())
        with self.assertRaisesRegex(AuthoringError,'cancelled'):
            demonstration(self.params,self.root/'cancelled',TOOL,RUNNER,ROOT/'build/btp-author-analyze',{},cancelled=lambda:True)
        self.assertFalse((self.root/'cancelled').exists())

    def test_provider_independent_discovery_from_outside_checkout(self):
        result=subprocess.run([sys.executable,str(ROOT/'tools/author.py'),'recipe','list'],cwd=self.root,capture_output=True,text=True,check=True)
        recipe=json.loads(result.stdout)['recipes'][0];self.assertEqual(recipe['schema'],SCHEMA)
        self.assertEqual(recipe['format'],self.params['format'])
        self.assertEqual(dependencies(SETTINGS),[])


if __name__=='__main__':unittest.main()
