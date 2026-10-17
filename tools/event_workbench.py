"""Graph and quest authoring; every edge remains an ordinary event reference."""
import copy
import json
import tkinter as tk
from tkinter import ttk
from editor_model import EditorError,encoded
from world_editing import identity

def editor_data(document):return json.loads(document.metadata.get('EDITOR.json',b'{}'))
def editor_commit(document,data):
    metadata=dict(document.metadata);metadata['EDITOR.json']=encoded(data)
    document.replace_all(document.content,document.adventure,document.art,document.manifest,metadata)

def edges(event):
    result=[(key,event[key]) for key in ('next','failure','unchanged','then','else','cancel','win','loss','flee') if key in event]
    result.extend((f'choice {i+1}',o['next']) for i,o in enumerate(event.get('options',[])))
    result.extend((f'route {i+1}',v) for i,v in enumerate(event.get('routes',[])))
    return result

def connect(document,source,branch,target):
    a=copy.deepcopy(document.adventure);events={e['id']:e for e in a['events']}
    if source not in events or target not in events:raise EditorError('Choose existing source and destination events.')
    e=events[source]
    if branch not in dict(edges(e)):raise EditorError('Choose an existing output branch.')
    if branch.startswith('choice '):e['options'][int(branch.split()[1])-1]['next']=target
    elif branch.startswith('route '):e['routes'][int(branch.split()[1])-1]=target
    else:e[branch]=target
    document.replace_adventure(a)

def dialogue_branch(document,source,label,text):
    a=copy.deepcopy(document.adventure);e=next(e for e in a['events'] if e['id']==source)
    if e['op']!='choice' or len(e['options'])>=5:raise EditorError('Choose a choice event with fewer than five options.')
    if not label or len(label)>24:raise EditorError('A choice label uses 1..24 characters.')
    new=identity(document.manifest['package_id'],a['events'],'dialogue')
    a['events'].append(dict(id=new,op='say',text=text,next=source))
    e['options'].append(dict(label=label,next=new));document.replace_adventure(a);return new

class EventGraph:
    def __init__(self,owner):
        self.owner=owner;self.document=owner.document;self.selected=owner.event_id;self.drag=None
        self.window=tk.Toplevel(owner.window);self.window.title('Event graph');self.window.geometry('1000x700')
        bar=ttk.Frame(self.window,padding=8);bar.pack(fill='x')
        for label,method in [('Edit node',self.edit),('Connect branch',self.link),('Add dialogue branch',self.branch),('Objectives',self.objectives),('Playtest / checkpoints',self.debug),('Refresh',self.draw)]:
            ttk.Button(bar,text=label,command=lambda f=method:owner.guard(f)).pack(side='left',padx=3)
        ttk.Label(self.window,text='Drag nodes to arrange them. Double-click to edit. Arrows show named success, failure and dialogue branches.',padding=(10,0,10,8)).pack(fill='x')
        body=ttk.Frame(self.window);body.pack(fill='both',expand=True)
        self.canvas=tk.Canvas(body,background='#edf0f4',highlightthickness=0)
        y=ttk.Scrollbar(body,command=self.canvas.yview);x=ttk.Scrollbar(body,orient='horizontal',command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=y.set,xscrollcommand=x.set)
        y.pack(side='right',fill='y');x.pack(side='bottom',fill='x');self.canvas.pack(fill='both',expand=True)
        self.canvas.bind('<Button-1>',self.press);self.canvas.bind('<B1-Motion>',self.motion);self.canvas.bind('<ButtonRelease-1>',lambda e:owner.guard(lambda:self.release(e)))
        self.canvas.bind('<Double-1>',lambda e:owner.guard(self.edit));self.draw()

    def draw(self):
        self.canvas.delete('all');events=self.document.adventure['events'];saved=editor_data(self.document).get('event_layout',{})
        self.positions={e['id']:saved.get(e['id'],[30+(i%4)*280,30+(i//4)*130]) for i,e in enumerate(events)}
        if self.drag:self.positions[self.drag[0]]=self.drag[3]
        for e in events:
            x,y=self.positions[e['id']]
            for label,target in edges(e):
                if target not in self.positions:continue
                tx,ty=self.positions[target];color='#7891a2' if label not in ('failure','loss','flee') else '#bb7d73'
                self.canvas.create_line(x+115,y+70,tx+115,ty,arrow='last',fill=color,width=2)
                self.canvas.create_text((x+tx)/2+115,(y+ty)/2+35,text=label,fill='#536877',font='TkSmallCaptionFont')
        for e in events:
            x,y=self.positions[e['id']];tag='node:'+e['id']
            self.canvas.create_rectangle(x,y,x+230,y+70,fill='#fff3cd' if e['id']==self.selected else '#ffffff',outline='#346b93',width=2,tags=tag)
            self.canvas.create_text(x+10,y+12,anchor='nw',text=e['op'].upper(),fill='#306383',tags=tag)
            self.canvas.create_text(x+10,y+34,anchor='nw',text=e['id'],width=210,fill='#273747',tags=tag)
        bounds=self.canvas.bbox('all') or (0,0,900,600);self.canvas.configure(scrollregion=(0,0,max(bounds[2]+40,900),max(bounds[3]+40,600)))

    def press(self,event):
        x,y=self.canvas.canvasx(event.x),self.canvas.canvasy(event.y)
        for item in reversed(self.canvas.find_overlapping(x,y,x,y)):
            tag=next((t[5:] for t in self.canvas.gettags(item) if t.startswith('node:')),None)
            if tag:
                self.selected=tag;p=list(self.positions[tag]);self.drag=(tag,x-p[0],y-p[1],p);self.draw();return

    def motion(self,event):
        if self.drag:
            key,dx,dy,_=self.drag;self.drag=(key,dx,dy,[max(0,self.canvas.canvasx(event.x)-dx),max(0,self.canvas.canvasy(event.y)-dy)]);self.draw()

    def release(self,_):
        if self.drag:
            data=editor_data(self.document);data.setdefault('event_layout',{})[self.drag[0]]=self.drag[3]
            self.drag=None;editor_commit(self.document,data);self.draw()

    def edit(self):
        if not self.selected:return
        self.owner.apply_pending();self.owner.event_id=self.selected;self.owner.refresh_events();self.owner.populate_event()
        self.owner.tabs.select(self.owner.event_tab);self.owner.window.lift()

    def link(self):
        from adventure_editor import Form
        if not self.selected:return
        e=next(e for e in self.document.adventure['events'] if e['id']==self.selected);branches=dict(edges(e))
        if not branches:raise EditorError('This event has no outgoing branches. Change its operation in Edit node first.')
        f=Form(self.owner,'Connect event branch');key=next(iter(branches));f.field('branch',key,list(branches))
        f.field('destination',branches[key],[e['id'] for e in self.document.adventure['events']])
        def apply(v):connect(self.document,self.selected,v['branch'],v['destination']);self.owner.refresh();self.draw()
        f.submit(apply)

    def branch(self):
        from adventure_editor import Form
        if not self.selected:return
        f=Form(self.owner,'New dialogue branch');f.field('label','Ask a question');f.field('text','The conversation continues.')
        def apply(v):dialogue_branch(self.document,self.selected,v['label'],v['text']);self.owner.refresh();self.draw()
        f.submit(apply)

    def objectives(self):ObjectiveEditor(self.owner)
    def debug(self):
        from playtest_workbench import PlaytestWindow
        PlaytestWindow(self.owner)

class ObjectiveEditor:
    def __init__(self,owner):
        self.owner=owner;self.document=owner.document
        self.window=tk.Toplevel(owner.window);self.window.title('Objectives and journal');self.window.geometry('680x440')
        ttk.Label(self.window,text='Objectives appear when their Active flag is set; Complete flags retain finished entries.',padding=12,wraplength=640).pack(fill='x')
        self.listing=tk.Listbox(self.window,exportselection=False);self.listing.pack(fill='both',expand=True,padx=12)
        bar=ttk.Frame(self.window,padding=12);bar.pack(fill='x')
        for text,method in [('New',lambda:self.edit(True)),('Edit',lambda:self.edit(False)),('Delete',self.delete)]:ttk.Button(bar,text=text,command=lambda f=method:owner.guard(f)).pack(side='left',padx=4)
        self.listing.bind('<Double-1>',lambda _:owner.guard(lambda:self.edit(False)));self.refresh()
    def refresh(self):
        self.listing.delete(0,'end')
        for o in self.document.adventure.get('objectives',[]):self.listing.insert('end',o['title'])
    def edit(self,new):
        from adventure_editor import Form
        a=self.document.adventure;flags=a['flags']
        if len(flags)<2:raise EditorError('Add Active and Complete flags under People, shops and start first.')
        if not new and not self.listing.curselection():return
        index=None if new else self.listing.curselection()[0]
        old=dict(id=identity(self.document.manifest['package_id'],a.get('objectives',[]),'objective'),title='New objective',text='Describe the objective.',active=flags[0],complete=flags[1]) if new else a['objectives'][index]
        f=Form(self.owner,'Objective')
        for k in ('id','title','text','active','complete'):f.field(k,old[k],flags if k in ('active','complete') else None)
        def apply(v):
            a=copy.deepcopy(self.document.adventure);values=a.setdefault('objectives',[])
            if index is None:values.append(v)
            else:values[index]=v
            self.document.replace_adventure(a);self.owner.refresh();self.refresh()
        f.submit(apply)
    def delete(self):
        if self.listing.curselection():
            a=copy.deepcopy(self.document.adventure);a['objectives'].pop(self.listing.curselection()[0]);self.document.replace_adventure(a);self.refresh()
