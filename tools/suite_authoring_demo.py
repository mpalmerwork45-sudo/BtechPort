"""Retained demonstration of authoring, source save, coverage and native parity."""
import argparse
import json
from pathlib import Path
from campaign_source import convert
from editor_model import ProjectDocument,encoded
from review_selection_demo import create
import suite_authoring as model

ROOT=Path(__file__).resolve().parents[1]


def build(output,windows=False):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False);tool=ROOT/'build/btp-project'
    doc,path=create(output/'fixture',tool);value=model.import_suite(path,'regression','Independent regression suite')
    model.put(doc,value);doc.save();source=convert(doc,output/'source');source=ProjectDocument(source.root,tool)
    assert model.suites(source)==[value]
    inventory=model.inspect(source,value,output/'inventory')
    assert all(c['status']=='not_run' for c in inventory['inventory']['cases'])
    full=model.run(source,value,output/'full',ROOT/'build/btp-author-playtest')
    selected=model.run(source,value,output/'selected',ROOT/'build/btp-author-playtest',case_ids=['yard'])
    assert full['status']==selected['status']=='passed'
    assert [c['status'] for c in selected['inventory']['cases']]==['passed','not_run','not_run']
    report=dict(status='passed',full=full['report'],selected=selected['report'],coverage=selected['coverage'],source=str(source.root),windows=None)
    if windows:
        from world_route_demo import windows_check
        reference=json.loads(Path(selected['report']).read_bytes())['runs'][0];path=Path(reference['report']).parent
        report['windows']=windows_check(ProjectDocument(path/'game',tool),json.loads((path/'scenario.json').read_bytes()),output/'windows',reference)
    (output/'report.json').write_bytes(encoded(report));return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--windows',action='store_true')
    args=parser.parse_args();print(json.dumps(build(args.output,args.windows),indent=2))
