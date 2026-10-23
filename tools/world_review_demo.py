"""A two-planet proposal: preserve a painted pond, move a port, revise terrain."""
import copy
import json
from pathlib import Path
from world_route_demo import create as create_worlds,journey
from authoring_protection import edit_rule
from authoring_service import revision
from editor_model import encoded,ProjectDocument
from world_editing import get_world
import authoring_review as review

ROOT=Path(__file__).resolve().parents[1]


def create(folder,validator):
    doc=create_worlds(folder,validator);a=copy.deepcopy(doc.adventure)
    get_world(a,'survey:aster')['patches'].append(dict(at=[44,12],rows=[['beacon:water']*2 for _ in range(2)]))
    doc.replace_adventure(a)
    edit_rule(doc,dict(id='painted-pond',label='Hand-painted pond',kind='world_region',world='survey:aster',rect=[44,12,2,2]))
    doc.save();return doc


def request(doc):
    return dict(api_version=1,request_id='world-review-demo',project_id=doc.manifest['package_id'],expected_revision=revision(doc),
        label='Move the shuttle port and revise both planets',scope=['adventure.maps','adventure.worlds'],
        operations=[dict(op='city.place',world='survey:aster',map='survey:port',at=[62,16]),
            dict(op='map.paint',map='survey:port',tile='beacon:wall',start=[1,1]),
            dict(op='world.patch',world='survey:boreal',at=[94,8],rows=[['beacon:water']*4 for _ in range(2)]),
            dict(op='world.paint',world='survey:boreal',jigsaw='survey:lake',start=[12,3]),
            dict(op='world.patch',world='survey:aster',at=[44,12],rows=[['beacon:grass']*2 for _ in range(2)])],
        groups=[dict(id='port',label='Move and detail the port',operations=[0,1]),dict(id='boreal',label='Boreal lakes',operations=[2,3]),
            dict(id='pond',label='Replace the protected pond',operations=[4])])


def main():
    import argparse
    from authoring_scenarios import run
    from authoring_contract import AuthoringError
    from world_route_demo import windows_check
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--windows',action='store_true')
    p.add_argument('--large',action='store_true',help='Measure a 1024-square world overview and full-world protection; no gameplay coverage is claimed.')
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    if args.large:
        doc=create(out/'game',ROOT/'build/btp-project');a=copy.deepcopy(doc.adventure);a['worlds']=a['worlds'][:1]
        a['worlds'][0]['pieces']=[['survey:plain']*128 for _ in range(128)]
        # A maximum planet consumes every discovery sector. Place the third
        # source map on it too, rather than silently exceeding that capacity.
        a['maps'][2]['origin']=[128,16];a['worlds'][0]['cities'].append('survey:landing');doc.replace_adventure(a)
        edit_rule(doc,dict(id='planet',label='Whole planet terrain',kind='world_region',world='survey:aster',rect=[0,0,1024,1024]));doc.save()
        command=request(doc);command.pop('groups');command['scope']=['adventure.worlds']
        command['operations']=[dict(op='world.patch',world='survey:aster',at=[1023,1023],rows=[['beacon:water']])]
        result=review.prepare(doc,command,out/'review');assert result['status']=='conflicts',result
        assert result['world_changes'][0]['changed_tiles']==1
        assert result['conflicts'][0]['rule']=='planet'
        previews=[p for p in result['artifacts'] if p['kind']=='world'];assert len(previews)==2
        assert all(p['artifact']['pixels_per_tile']==1 for p in previews)
        review.world_crop(out/'review','survey:aster',[992,992,32,32],doc.validator)
        summary=dict(status='passed',world_tiles=1024*1024,changed_tiles=1,overviews=2,pixels_per_tile=1,
            protected_rect=[0,0,1024,1024],review=str(out/'review'),coverage='Bounded review/protection, not gameplay traversal')
        (out/'report.json').write_bytes(encoded(summary));print(json.dumps(summary,indent=2));return
    doc=create(out/'game',ROOT/'build/btp-project');before=revision(doc);command=request(doc)
    (out/'request.json').write_bytes(encoded(command));(out/'journey.json').write_bytes(encoded(journey()))
    blocked=review.prepare(doc,command,out/'blocked');assert blocked['status']=='conflicts',blocked
    try:review.apply(doc,out/'blocked')
    except AuthoringError as error:assert error.diagnostic['code']=='protection.conflict'
    else:raise AssertionError('Protected pond was not blocked')
    narrowed=review.recheck(doc,out/'blocked',out/'narrowed',['port','boreal']);assert narrowed['status']=='ready',narrowed
    for world in narrowed['world_changes']:
        location=(world['towns'][0]['after'] if world['towns'] else world['areas'][0]['rect'])
        review.world_crop(out/'narrowed',world['id'],[*location[:2],32,32],doc.validator)
    original=run(doc,journey(),out/'original-route',ROOT/'build/btp-author-playtest');assert original['status']=='passed',original
    review.apply(doc,out/'narrowed');accepted=revision(doc)
    doc.undo();assert revision(doc)==before
    doc.redo();assert revision(doc)==accepted
    doc.save();reopened=ProjectDocument(doc.root,doc.validator);assert reopened.files()==doc.files()
    revised=run(reopened,journey(),out/'revised-route',ROOT/'build/btp-author-playtest');assert revised['status']=='passed',revised
    result=dict(status='passed',protected_rule=blocked['conflicts'][0]['rule'],worlds=len(narrowed['world_changes']),
        original_route=original['report'],revised_route=revised['report'],review=str(out/'narrowed'),undo_redo_reopen=True)
    if args.windows:result['windows']=windows_check(reopened,journey(),out/'windows',revised)
    (out/'report.json').write_bytes(encoded(result));print(json.dumps(result,indent=2))


if __name__=='__main__':main()
