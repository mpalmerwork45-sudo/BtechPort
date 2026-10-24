"""Delivery checks must catch regressions rather than merely report success."""
import copy,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from chi_delivery_probe import check_dialogue_recipe,check_saved_games


class DialogueDeliveryGateTests(unittest.TestCase):
    def setUp(self):
        self.text='Synthetic source speech with quoted "words" and a newline\nthat must remain local to the recipient.'
        self.recipe={'change':{'$chi_text':[{'source':{'file':'chi/talk-data.bin','path':['texts',373]},'at':0,'length':len(self.text)},'!']}}

    def test_references_are_accepted_but_copied_and_partial_literals_fail(self):
        check_dialogue_recipe(self.recipe,[self.text])
        for text in (self.text+'!',self.text[16:48]):
            bad=copy.deepcopy(self.recipe);bad['other']=text
            with self.subTest(text=text),self.assertRaisesRegex(ValueError,'original dialogue span'):
                check_dialogue_recipe(bad,[self.text])

    def test_missing_native_references_fail(self):
        with self.assertRaisesRegex(ValueError,'omitted original text references'):
            check_dialogue_recipe({'change':'A newly written sentence.'},[self.text])


@unittest.skipUnless((ROOT/'build/btp-project').is_file() and (ROOT/'build/btech-headless').is_file(),'Requires native validator and player')
class SaveDeliveryGateTests(unittest.TestCase):
    def test_packaged_journey_preserves_source_and_recovers_numeric_id_slots(self):
        from editor_model import create_project
        with tempfile.TemporaryDirectory(prefix='chi-delivery-save-') as temporary:
            root=Path(temporary)
            doc=create_project(ROOT/'examples/beacon-demo',root/'Source','delivery-2','Delivery Two',ROOT/'build/btp-project')
            before=doc.files()
            report=check_saved_games(doc,root/'Proof',ROOT/'build/btech-headless')
            self.assertEqual(report['status'],'passed');self.assertEqual(report['slots'],6)
            self.assertEqual(doc.files(),before);doc.unchanged_on_disk()
            saves=list((root/'Proof/Private settings/games/delivery-2').glob('*/*.btp'))
            self.assertEqual(len(saves),6)
            self.assertEqual(len({p.read_bytes() for p in saves}),1)


if __name__=='__main__':unittest.main()
