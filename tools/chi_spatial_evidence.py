#!/usr/bin/env python3
"""Retain private C3 edit examples and native proofs without committing assets."""
import argparse
import copy
import json
from pathlib import Path
import shutil
import subprocess
from chi_import import import_campaigns,plain_path,ROOT
from chi_spatial import change,find,move_town
from chi_resources import detach,settings,put_settings
from editor_model import ProjectDocument,EditorError,encoded


def generate(source,target):
    target=plain_path(target);source=plain_path(source)
    if target.exists() or target.is_relative_to(source) or target.is_relative_to(ROOT/'UnBattletech'):
        raise EditorError('Choose a new evidence folder outside the reference/source directories.')
    target.mkdir();tool=ROOT/'build/btp-project';proof=ROOT/'build/btp-chi-spatial-tests'
    import_campaigns(source,target/'base',validator=tool);records=[]
    def native(arguments):
        result=subprocess.run([str(proof),*map(str,arguments)],capture_output=True,text=True,timeout=30)
        if result.returncode:raise EditorError(result.stdout+result.stderr)
        return result.stdout.strip()
    def retain(name,edit,profile='original',kind=None):
        folder=target/name;shutil.copytree(target/'base'/profile,folder);doc=ProjectDocument(folder,tool);before=doc.files()
        edit(doc);changed=doc.files();doc.undo();assert doc.files()==before;doc.redo();assert doc.files()==changed
        doc.save();reopened=ProjectDocument(folder,tool);assert reopened.files()==doc.files()
        result=native(['--proof',target/'base'/profile,folder,kind or name])
        records.append(dict(kind=kind or name,project=str(folder),base=str(target/'base'/profile),native=result))
        return doc
    def paint(doc):
        a=copy.deepcopy(doc.adventure);a['maps'][0]['rows'][12][34]='chi:land-85';doc.replace_adventure(a)
    retain('block',paint)
    retain('door',lambda d:change(d,lambda v:v['maps'][0]['entrances'][3].update(half=[34,44])))
    retain('routes',lambda d:change(d,lambda v:v['maps'][0]['npcs'][0].update(route=1)))
    retain('town',lambda d:change(d,lambda v:move_town(v,'chi:map-03',832,512)))
    retain('citadel',lambda d:change(d,lambda v:move_town(v,'chi:map-01',704,768)))
    retain('starport',lambda d:change(d,lambda v:move_town(v,'chi:map-02',576,512)))
    def broker(doc):
        value=doc.adventure['chi_native'];m=value['maps'][1];tiles={t['id']:t for t in value['tiles']}
        point=next([x,y] for x,y in ((52,50),(54,52),(56,50),(54,48)) if tiles[m['rows'][y//2][(x+1)//2]]['rule']<85)
        change(doc,lambda v:v['services']['broker'].update(half=point))
    retain('broker',broker,'updated')
    def jigsaw(doc):
        a=copy.deepcopy(doc.adventure)
        from art_editing import new_image
        art=copy.deepcopy(doc.art);im=new_image('c3',art['images'],'C3 wall');art['images'].append(im)
        a['tiles'].append(dict(id='c3:wall',sheet='package:art',graphic=im['id'],terrain='wall',mini_color=7))
        a['jigsaws'].append(dict(id='c3:join',name='C3 terrain piece',rows=[['c3:wall']*8 for _ in range(8)]));a['chi_native']['world']['joins']=['c3:join']*17
        doc.replace_art(art,a)
    retain('jigsaw',jigsaw)
    def image(doc,kind,resource,index=0,count=1,color='ffffffff'):
        with doc.command('C3 resource edit'):
            im=detach(doc,kind,resource,index,count);art=copy.deepcopy(doc.art)
            next(i for i in art['images'] if i['id']==im['id'])['frames'][0][0]=color+im['frames'][0][0][8:];doc.replace_art(art)
            if kind=='animation':
                value=settings(doc);value['bindings'][0]['units'][0]+=7;put_settings(doc,value)
    retain('sprite',lambda d:image(d,'sprite','MECHSHAP.CMP',0,16))
    retain('film',lambda d:image(d,'animation','O.ANM'))
    retain('screen',lambda d:image(d,'screen','BTTITLE.CMP'))
    retain('portrait',lambda d:image(d,'portrait','PORTRAITS',6,color='ff55ffff'),'updated')
    def font(doc):
        with doc.command('C3 font edit'):
            im=detach(doc,'font','BTTA.FONT');art=copy.deepcopy(doc.art);row=im['frames'][0][32]
            next(i for i in art['images'] if i['id']==im['id'])['frames'][0][32]=row[:64]+'ffffffff'*8+row[128:];doc.replace_art(art)
    retain('font',font)
    def audio(doc):
        value=settings(doc);value['sounds'][0]=2;value['sound_speed']=125;put_settings(doc,value)
    retain('audio',audio)
    def field(doc):
        from editor_tiles import load_tiles
        from art_editing import editable_tile
        from tile_editing import metadata,source_origin
        art=copy.deepcopy(doc.art);a=copy.deepcopy(doc.adventure);index=next(i for i,t in enumerate(a['tiles']) if t['id']=='chi:land-106');source=copy.deepcopy(a['tiles'][index])
        im=editable_tile(art,a,index,doc.manifest['package_id'],load_tiles(doc,{}));im['frames'][0]=['ffffffff'*16]*16
        editing=metadata(doc);editing.setdefault('tile_sources',{})[im['id']]=source_origin(editing,source)
        meta=dict(doc.metadata);meta['EDITOR.json']=encoded(editing);doc.replace_art(art,a,meta)
    retain('forcefield',field)
    held=native(['--held-film',target/'film',ROOT/'tests/fixtures/ordinary-training-combat.actions',target/'film-held.btp'])
    moved=native(['--moved-route',target/'base/original',target/'citadel',ROOT/'tests/fixtures/ordinary-training-combat.actions'])
    report=dict(status='passed',examples=records,held_film=held,moved_citadel=moved)
    (target/'evidence.json').write_bytes(encoded(report));return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data',type=Path,default=ROOT/'Original DOS');parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();result=generate(args.data,args.output)
    print(json.dumps(dict(status=result['status'],examples=len(result['examples']),evidence=str(args.output/'evidence.json'))))
