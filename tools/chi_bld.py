"""Lossless labelled BLD sources; the C loader is the authoritative compiler.

Original payloads and unreachable regions stay private. This module decodes
verified formats and edits the same document used by the player, not a second
story VM. Native action/service parameters remain the subsequent C4 increments.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
from pathlib import Path
from audit_bld_flow import decrypt,graph,COUNTS
from chi_audit import BUILDINGS
from editor_model import EditorError,encoded

FILE='chi-scripts.json'
FORMAT='btp-chi-scripts-v1'
OPS={0xfe:'font',0xfd:'clear',0xfa:'scene',0xfc:'text',0xf1:'add',0xf4:'set',
     0xf3:'dispatch',0xf7:'if',0xf0:'cursor',0xf6:'confirm',0xf5:'native',
     0xf2:'delay',0xea:'animation',0xfb:'wait',0xf8:'jump',0xf9:'menu',0xff:'end',
     0xe4:'sound',0xe9:'recruit',0xe8:'if_person_absent',0xed:'if_skill',
     0xeb:'if_advanced_kit',0xec:'if_medical_kit',0xe6:'position',
     0xe5:'add_money',0xee:'spend_money',0xef:'if_money',0xe3:'event'}
NATIVE_NAMES=dict(enumerate(('', 'Start training mission','Insert mission result','Return from training',
    'Show class prices','Attend class','Show accounts','Buy shares','Sell shares','Buy armour','Insert credits','Buy weapon','Talk',
    'Select service recipient','Count party members','Technician apprenticeship','Check technician apprenticeship','Count active mechs',
    'Repair mech','Refit mech','Technician service payment','Medical apprenticeship','Check medical apprenticeship','Check party injuries',
    'Heal party','Give medical kit','Give advanced kit','Allocate arena crew','Store mechs','Count stored mechs','Recruit Rex encounter',
    'Read selected armour','Repair armour','Prepare arena party','Select arena mech','Start arena combat','Insert selected character name',
    'Apply prison party loss','Insert next recruit name','Allocate crew after theft','Begin prison yard','Give laser rifles',
    'Place party outside cinema','Return cadet from training','Rearm ammunition','View Phoenix Hawk LAM','Check out mechs and allocate crew','Apply mayor meal')))
DESCRIPTIONS={
 'event':'Suspend this building for an authored quest; return to success, failure or cancellation labels.',
 'font':'Select the native font/presentation mode.', 'clear':'Clear the text panel and its inserted values.',
 'scene':'Select native scene zero.', 'text':'Append dialogue at the current native text cursor.',
 'set':'Write one story byte.', 'add':'Add to a story byte, wrapping modulo 256 (255 means minus one).',
 'dispatch':'Jump through the ordered table using the signed story byte (CBW).',
 'if':'Jump when the story byte is nonzero; otherwise continue.',
 'cursor':'Set the native text column and row.', 'confirm':'Ask Yes/No; Yes branches, No continues.',
 'native':'Call a compatibility action in this building context. It can yield.',
 'delay':'Record the original delay/keyboard-flush request.',
 'animation':'Play a native film, then resume this program.', 'wait':'Wait for acknowledgement, then continue.',
 'jump':'Jump to a stable label.', 'menu':'Use the existing native menu selector/layout and ordered destinations.',
 'end':'End this building program.', 'sound':'Play a verified speaker program, waiting for it to finish.',
 'recruit':'Run native recruitment for the selected skill.',
 'if_person_absent':'Branch when the party lacks this character identity.',
 'if_skill':'Branch when a party member has at least the specified skill.',
 'if_advanced_kit':'Branch when the party owns an advanced kit.',
 'if_medical_kit':'Branch when the party owns a medical kit.',
 'position':'Set the packed native outdoor destination (rebased by the spatial adapter).',
 'add_money':'Add a signed 16-bit amount to credits; native unsigned wrapping is retained.',
 'spend_money':'Subtract credits, clamping at zero.', 'if_money':'Branch if credits cover the amount.',
 'data':'Preserved unreachable original bytes. Branches/fall-through cannot execute these bytes.'}

# Field types also drive the editor; numeric values retain the original byte
# representation, including signed ADD/MONEY operands and packed coordinates.
FIELDS={
 'event':{'event':'event','next':'target','failure':'target','cancel':'target'},
 'font':{'value':(3,4,6)},'scene':{'value':(0,)},'text':{'text':'text'},
 'add':{'index':(0,99),'value':(0,255)},'set':{'index':(0,99),'value':(0,255)},
 'dispatch':{'index':(0,99),'targets':'targets'},'if':{'index':(0,99),'target':'target'},
 'cursor':{'column':(0,26),'row':(0,24)},'confirm':{'target':'target'},'native':{'action':(1,47)},
 'animation':{'kind':(0,21),'flags':(0,2)},'jump':{'target':'target'},'menu':{'menu':tuple(COUNTS),'targets':'targets'},
 'sound':{'program':(1,18)},'recruit':{'skill':(0,6)},'if_person_absent':{'person':(0,255),'target':'target'},
 'if_skill':{'skill':(0,6),'minimum':(0,255),'target':'target'},'if_advanced_kit':{'target':'target'},
 'if_medical_kit':{'target':'target'},'position':{'x':(0,65535),'y':(0,65535)},
 'add_money':{'amount':(0,65535)},'spend_money':{'amount':(0,65535)},'if_money':{'amount':(0,65535),'target':'target'},'data':{'bytes':'bytes'},
 'clear':{},'delay':{},'wait':{},'end':{}}


def schema():
    from authoring_contract import obj,array,integer,ID
    common=dict(id=ID,origin=integer(0,8999),original_size=integer(1,9000),note=dict(type='string',maxLength=240))
    variants=[]
    for name,fields in FIELDS.items():
        properties=dict(common,op={'const':name})
        for key,kind in fields.items():
            properties[key]=(dict(type='string',maxLength=4096) if kind=='text' else
                dict(type='string',pattern='^(?:[0-9a-f]{2})+$',maxLength=18000) if kind=='bytes' else ID if kind in ('target','event') else
                array(ID,1,128) if kind=='targets' else integer(*kind) if len(kind)==2 and name not in ('font','scene','menu') else dict(enum=list(kind)))

        if name in ('add_money','spend_money','if_money'):properties['amount']={'oneOf':[integer(0,65535),dict(type='string',pattern=r'^\{(?:service|mission):[a-z0-9._]+\}$')]}
        if name=='native':properties['action']={'oneOf':[integer(1,47),dict(type='string',pattern=r'^native\.[a-z0-9-]+$')]}
        v=obj(properties,['id','op',*fields]);v['dependentRequired']={'origin':['original_size'],'original_size':['origin']};variants.append(v)
    p=obj(dict(id=ID,name=dict(type='string',maxLength=95),resource=dict(enum=[n+'.BLD' for n in BUILDINGS]),
        building=integer(0,25),baseline_sha256=dict(type='string',pattern='^[0-9a-f]{64}$'),entry=ID,
        nodes=array(dict(oneOf=variants),1,2048)),['id','name','resource','building','baseline_sha256','entry','nodes'])
    return obj(dict(format={'const':FORMAT},schema_version={'const':1},programs=array(p,26,26)),['format','schema_version','programs'])


def identity(name,offset=None):
    return 'chi:bld-'+name.lower() if offset is None else 'chi:'+name.lower()+'-'+format(offset,'04x')


def decode(raw,name):
    """Walk reachable instructions and explicitly retain every uncovered byte."""
    payload=decrypt(raw)
    if not 0<len(payload)<=9000:raise EditorError('BLD payload must fit 1..9000 bytes.')
    nodes=graph(payload);covered=set();records=[]
    def word(at):return int.from_bytes(payload[at:at+2],'little')
    def label(at):return identity(name,at)
    for pc,node in sorted(nodes.items()):
        size=1+len(bytes.fromhex(node['operands']));span=set(range(pc,pc+size))
        if span&covered:raise EditorError(f'{name}: overlapping instruction at {pc:04x}.')
        covered.update(span);code=payload[pc]
        if code not in OPS:raise EditorError(f'{name}: unsupported opcode {code:02x} at {pc:04x}.')
        item=dict(id=label(pc),origin=pc,original_size=size,op=OPS[code]);at=pc+1
        if code in (0xfe,0xfa):item['value']=payload[at]
        elif code==0xfc:item['text']=payload[at:pc+size-1].decode('ascii')
        elif code in (0xf1,0xf4):item.update(index=payload[at],value=payload[at+1])
        elif code==0xf3:item.update(index=payload[at],targets=[label(t) for t in node['targets']])
        elif code==0xf7:item.update(index=payload[at],target=label(word(at+1)))
        elif code==0xf0:item.update(column=payload[at],row=payload[at+1])
        elif code in (0xf6,0xf8,0xeb,0xec):item['target']=label(word(at))
        elif code==0xf5:item['action']=payload[at]
        elif code==0xea:item.update(kind=payload[at],flags=payload[at+1])
        elif code==0xf9:item.update(menu=payload[at],targets=[label(t) for t in node['targets']])
        elif code==0xe4:item['program']=payload[at]
        elif code==0xe9:item['skill']=payload[at]
        elif code==0xe8:item.update(person=payload[at],target=label(word(at+1)))
        elif code==0xed:item.update(skill=payload[at],minimum=payload[at+1],target=label(word(at+2)))
        elif code==0xe6:item.update(x=word(at),y=word(at+2))
        elif code in (0xe5,0xee,0xef):
            item['amount']=word(at)
            if code==0xef:item['target']=label(word(at+2))
        records.append(item)
    at=0
    while at<len(payload):
        if at in covered:at+=1;continue
        end=at+1
        while end<len(payload) and end not in covered:end+=1
        records.append(dict(id=label(at),origin=at,original_size=end-at,op='data',bytes=payload[at:end].hex()));at=end
    records.sort(key=lambda item:item['origin'])
    return dict(id=identity(name),resource=name+'.BLD',building=BUILDINGS.index(name),name=name.title(),
        baseline_sha256=hashlib.sha256(payload).hexdigest(),entry=label(0),nodes=records)


def extract(files):
    return dict(format=FORMAT,schema_version=1,programs=[decode(files['chi/'+name+'.BLD'],name) for name in BUILDINGS])


def data(document):
    if document.manifest.get('requires')!='chi-local-dos-1.03':raise EditorError('BLD authoring requires an imported CHI project.')
    name=document.manifest.get('chi_scripts')
    return json.loads(document.metadata[name]) if name else extract(document.files())


def put(document,value,label='Edit BLD source'):
    with document.command(label):
        manifest=copy.deepcopy(document.manifest);manifest['chi_scripts']=FILE
        metadata=dict(document.metadata);metadata[FILE]=encoded(value)
        document.replace_all(document.content,document.adventure,document.art,manifest,metadata);document.validate()


def enable(document):
    if not document.manifest.get('chi_scripts'):put(document,data(document),'Enable BLD source editing')


def find(value,program,node=None):
    result=next((p for p in value['programs'] if p['id']==program),None)
    if result is None:raise EditorError('Unknown BLD program: '+str(program))
    if node is None:return result
    result=next((n for n in result['nodes'] if n['id']==node),None)
    if result is None:raise EditorError('Unknown BLD label: '+str(node))
    return result


def update(document,program,node,changes):
    value=data(document);record=find(value,program,node)
    if set(changes)&{'id','origin','original_size','baseline_sha256','building','resource'}:
        raise EditorError('Stable IDs and original provenance/byte ranges cannot be changed. Clone/insert a new label instead.')
    record.update(copy.deepcopy(changes));put(document,value)


def insert(document,program,after,node):
    value=data(document);p=find(value,program);index=next((i for i,n in enumerate(p['nodes']) if n['id']==after),None)
    if index is None:raise EditorError('Choose an existing label to insert after.')
    if set(node)&{'origin','original_size'}:raise EditorError('New instructions cannot claim original byte ranges.')
    p['nodes'].insert(index+1,copy.deepcopy(node));put(document,value,'Insert BLD instruction')


def remove(document,program,node):
    value=data(document);p=find(value,program);record=find(value,program,node)
    if 'origin' in record:raise EditorError('Original labelled records preserve byte ranges. Redirect around them; remove only newly inserted instructions.')
    p['nodes'].remove(record);put(document,value,'Remove inserted BLD instruction')


def compiled(document,program):
    from chi_resources import tool
    return tool(document,['chi-program',program])


def describe(node):
    op=node['op']
    if op=='text':return node['text'].replace('\r',' / ').translate({6:None,14:None,15:None})[:150]
    if op=='native':return str(node['action'])+': '+NATIVE_NAMES.get(node['action'],'Compatibility operation')+' (native building context)'
    fields={k:v for k,v in node.items() if k not in ('id','op','origin','original_size','note','bytes')}
    return DESCRIPTIONS.get(op,'Unsupported operation')+' '+', '.join(k+'='+str(v) for k,v in fields.items())


def main():
    from app_runtime import binary
    from editor_model import ProjectDocument
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--project',type=Path,required=True)
    commands=parser.add_subparsers(dest='command',required=True)
    commands.add_parser('enable');commands.add_parser('list')
    for name in ('show','compile'):
        sub=commands.add_parser(name);sub.add_argument('program')
        if name=='compile':sub.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        doc=ProjectDocument(args.project,binary('btp-project'))
        if args.command=='enable':enable(doc);print(doc.save())
        elif args.command=='list':print(json.dumps([dict(id=p['id'],name=p['name'],instructions=len(p['nodes'])) for p in data(doc)['programs']],indent=2))
        elif args.command=='show':print(json.dumps(find(data(doc),args.program),indent=2))
        else:
            result=compiled(doc,args.program)
            if args.output:
                destination=args.output.resolve()
                if destination.is_relative_to(doc.root) or any(destination.is_relative_to(Path(__file__).resolve().parents[1]/p) for p in ('Original DOS','UnBattletech')):
                    raise EditorError('Write compiled verification output outside the project/reference directories.')
                with destination.open('xb') as out:out.write(bytes.fromhex(result['encrypted']))
                print('Wrote compiled BLD: '+str(destination))
            else:print(json.dumps(result,indent=2))
    except (EditorError,OSError,ValueError) as error:parser.exit(1,str(error)+'\n')


if __name__=='__main__':main()
