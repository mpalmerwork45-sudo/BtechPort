"""Acceptance evidence must fail closed without replaying whole campaigns."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import chi_bridge_evidence as bridge
import chi_enhanced_acceptance as enhanced
from editor_model import EditorError


class StopProbe(Exception):
    pass


class ChiEvidenceGuards(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(prefix='chi-evidence-guards-')
        self.root=Path(self.temporary.name)
    def tearDown(self):
        self.temporary.cleanup()
    def native_bridge(self,command,**unused):
        suffix='-nested' if command[-1]=='nested' else ''
        prefix=Path(command[-2] if suffix else command[-1])
        for name in bridge.artifacts(suffix):
            Path(str(prefix)+'-'+name).write_bytes(('synthetic '+name).encode())
        return SimpleNamespace(returncode=0,stdout='Synthetic native artifacts',stderr='')
    def linux_bridge(self):
        with patch.object(bridge.subprocess,'run',side_effect=self.native_bridge):
            return bridge.verify(self.root)
    def test_windows_requires_linux_report_before_running(self):
        with patch.object(bridge.subprocess,'run') as execute:
            with self.assertRaisesRegex(RuntimeError,'Linux bridge acceptance'):
                bridge.verify(self.root,True)
            execute.assert_not_called()
        self.assertEqual(json.loads((self.root/'windows-evidence.json').read_bytes())['status'],'failed')
    def test_windows_rejects_empty_or_incomplete_linux_artifact_set(self):
        report=dict(status='passed',journeys=[dict(project=e+s,exit_code=0) for e in ('original','updated') for s in ('','-nested')])
        (self.root/'linux-evidence.json').write_text(json.dumps(report))
        with patch.object(bridge.subprocess,'run') as execute:
            with self.assertRaisesRegex(RuntimeError,'Missing Linux bridge artifact'):
                bridge.verify(self.root,True)
            execute.assert_not_called()
    def test_all_58_holds_are_compared_and_manifested(self):
        linux=self.linux_bridge()
        with patch.object(bridge.subprocess,'run',side_effect=self.native_bridge):
            windows=bridge.verify(self.root,True)
        self.assertEqual(linux['status'],'passed');self.assertEqual(windows['status'],'passed')
        self.assertEqual(len(linux['artifacts']),58*3)
        self.assertEqual(len(windows['comparisons']),58*3)
        self.assertEqual(len(windows['artifacts']),58*3)
    def test_stale_files_cannot_hide_missing_new_artifacts(self):
        self.linux_bridge()
        with patch.object(bridge.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='',stderr='')):
            with self.assertRaisesRegex(RuntimeError,'Missing generated bridge artifact'):
                bridge.verify(self.root)
        self.assertEqual(json.loads((self.root/'linux-evidence.json').read_bytes())['status'],'failed')
    def test_changed_baseline_rejected_before_windows(self):
        self.linux_bridge()
        (self.root/'linux-original-dialogue.btp').write_bytes(b'changed')
        with patch.object(bridge.subprocess,'run') as execute:
            with self.assertRaisesRegex(RuntimeError,'Linux bridge artifact changed'):
                bridge.verify(self.root,True)
            execute.assert_not_called()
    def test_platform_mismatch_is_recorded_as_failed(self):
        self.linux_bridge()
        def mismatch(command,**kwargs):
            result=self.native_bridge(command,**kwargs)
            Path(command[-1]+'-dialogue.btp').write_bytes(b'wrong platform')
            return result
        with patch.object(bridge.subprocess,'run',side_effect=mismatch):
            with self.assertRaisesRegex(RuntimeError,'Platform continuation differs'):
                bridge.verify(self.root,True)
        self.assertEqual(json.loads((self.root/'windows-evidence.json').read_bytes())['status'],'failed')
    def enhanced_report(self):
        route=self.root/'route.actions';route.write_text('idle\n')
        source=self.root/'custom DOS'
        report=dict(route=str(route),sha256=hashlib.sha256(route.read_bytes()).hexdigest(),source=str(source),linux=dict(status='passed'))
        (self.root/'evidence.json').write_text(json.dumps(report))
        return source,route
    def test_enhanced_parity_uses_recorded_source(self):
        source,unused=self.enhanced_report()
        with patch.object(enhanced,'execute',side_effect=StopProbe) as execute:
            with self.assertRaises(StopProbe):enhanced.verify(self.root,True)
        self.assertEqual(execute.call_args.args[1][2],source)
    def test_changed_route_rejected_before_native_verification(self):
        unused,route=self.enhanced_report();route.write_text('accept\n')
        with patch.object(enhanced,'execute') as execute:
            with self.assertRaisesRegex(EditorError,'route changed'):enhanced.verify(self.root,True)
            execute.assert_not_called()
    def test_import_and_planner_receive_the_same_source(self):
        import chi_enhanced_route
        source=self.root/'custom DOS';output=self.root/'proof'
        def planned(project,folder,source=None):
            folder.mkdir();route=folder/'complete.actions';route.write_text('idle\n');return route
        with patch.object(enhanced,'import_campaigns') as importer,patch.object(chi_enhanced_route,'generate',side_effect=planned) as planner,patch.object(enhanced,'verify',return_value={}):
            enhanced.run(output,source)
        self.assertEqual(importer.call_args.args[0],source)
        self.assertEqual(planner.call_args.kwargs['source'],source)
        self.assertEqual(json.loads((output/'evidence.json').read_bytes())['source'],str(source))
    def test_inherited_training_and_cache_planners_use_selected_source(self):
        from make_campaign_replay import Session
        from make_cache_replay import finish
        source=self.root/'custom DOS'
        session=SimpleNamespace(original_data=source,state=dict(map=1))
        with patch.object(Path,'read_bytes',autospec=True,side_effect=StopProbe) as read:
            with self.assertRaises(StopProbe):Session.route(session,0)
            self.assertEqual(read.call_args.args[0],source/'MAP1.MTP')
            with self.assertRaises(StopProbe):finish(session)
            self.assertEqual(read.call_args.args[0],source/'BTECH.EXE')
    def test_enhanced_rejects_faults_and_unresolved_trace_records(self):
        import chi_coverage
        unused,route=self.enhanced_report()
        labels=('training-combat-start','training-victory','invasion-start','rex-crest','hospital-companion-pause','door-1-opening','map-room','ending-start')
        route.with_suffix('.json').write_text(json.dumps(dict(checkpoints=[dict(label=label,tick=0) for label in labels])))
        state=dict(mode='ending',combat_rules='enhanced',people=[[0] for unused in range(5)])
        def execute(binary,args,windows=False):
            if binary=='btp-chi-import-tests':return 'Synthetic parity'
            for flag in ('--save','--frame','--bld-trace'):
                if flag in args:Path(args[args.index(flag)+1]).write_bytes(b'synthetic artifact')
            return json.dumps(state)
        for measured in (dict(faults=[{}],unresolved_observations={}),dict(faults=[],unresolved_observations={'undeclared-branch':1})):
            with self.subTest(measured=measured),patch.object(enhanced,'execute',side_effect=execute),patch.object(enhanced,'ProjectDocument'),patch.object(chi_coverage,'coverage',return_value=measured):
                with self.assertRaisesRegex(EditorError,'faults or unresolved'):enhanced.verify(self.root)


if __name__=='__main__':unittest.main()
