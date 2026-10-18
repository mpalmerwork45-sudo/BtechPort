"""Graph and quest authoring; every edge remains an ordinary event reference."""
from editor_session import guard,register
from editor_workspace import view_window,open_view
import copy
import json
import tkinter as tk
from tkinter import ttk
from editor_recovery import recoverable_forms
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


def graph_arrangement(events):
    """Place branching flows in columns; cycles and disconnected nodes terminate."""
    identifiers={e['id'] for e in events};incoming={i:0 for i in identifiers}
    by_id={e['id']:e for e in events}
    for event in events:
        for _,target in edges(event):
            if target in incoming:incoming[target]+=1
    roots=[e['id'] for e in events if not incoming[e['id']]]
    levels={};queue=[(i,0) for i in roots]
    for fallback in [None,*by_id]:
        if fallback and fallback not in levels:queue.append((fallback,0))
        while queue:
            current,level=queue.pop(0)
            if current in levels:continue
            levels[current]=level
            queue.extend((target,level+1) for _,target in edges(by_id[current]) if target in by_id and target not in levels)
    counts={};result={}
    for identity,level in levels.items():
        row=counts.get(level,0);counts[level]=row+1;result[identity]=[35+level*330,35+row*200]
    return result


def graph_neighbours(events,selected,depth=2):
    by_id={e['id']:e for e in events}
    if selected not in by_id:return set(by_id)
    visible={selected};frontier={selected}
    for _ in range(depth):
        following={target for identity in frontier for _,target in edges(by_id[identity]) if target in by_id}
        frontier=following-visible;visible.update(following)
    visible.update(e['id'] for e in events if any(target==selected for _,target in edges(e)))
    return visible


class EventProperties:
    """Reuse the event fields in the shared inspector, with their own draft."""
    def __init__(self,graph,parent):
        from adventure_editor import AdventureEditor,scroll_frame
        self.owner=graph;self.window=graph.window;self.document=graph.document;self.stroke=None
        self.event_id=None;self.event_vars={};self.event_text=None;self.event_pending=False
        self.status=tk.StringVar()
        self.shell,self.event_form=scroll_frame(parent,width=245,height=470);self.shell.pack(fill='both',expand=True)
        self.render_event_form=AdventureEditor.render_event_form.__get__(self)
        self.apply_event=AdventureEditor.apply_event.__get__(self)
        self.capture_draft=AdventureEditor.capture_draft.__get__(self)
        def restore(state):
            AdventureEditor.restore_draft(self,state);self.layout_form()
        self.restore_draft=restore
        self.error=tk.StringVar();ttk.Label(parent,textvariable=self.error,foreground='#a03030',wraplength=220,padding=6).pack(fill='x')
        self.draft=register(self,pending=lambda:self.event_pending,apply=self.apply_pending,
            capture=self.capture_draft,restore=self.restore_draft,priority=20)
    @property
    def adventure(self):return self.document.adventure
    def guard(self,method):return guard(self,method)
    def apply_pending(self):
        if self.event_pending:self.apply_event()
    def commit(self,adventure):
        self.document.replace_adventure(adventure);self.owner.owner.refresh();self.owner.draw()
    def select(self,identity):
        if identity!=self.event_id or not self.event_pending:
            self.apply_pending();self.event_id=identity
            event=next((e for e in self.adventure['events'] if e['id']==identity),None)
            if event:
                self.render_event_form(copy.deepcopy(event))
                self.layout_form()
    def layout_form(self):
        for child in self.event_form.winfo_children():
            if isinstance(child,(ttk.Entry,ttk.Combobox,tk.Text)):child.configure(width=20)
            elif isinstance(child,ttk.Label):child.configure(wraplength=200)
            info=child.grid_info()
            if info:
                row=int(info['row']);column=int(info.get('column',0))
                child.grid_configure(row=row*2+min(column,1),column=0,columnspan=1,sticky='ew')
    def show_error(self,error):
        self.error.set(str(error));self.window.lift()
        key=getattr(error,'field',None);variable=self.event_vars.get(key)
        if variable:
            for widget in self.event_form.winfo_children():
                if isinstance(widget,ttk.Entry) and str(widget.cget('textvariable'))==str(variable):widget.focus_set();break


@recoverable_forms
class EventGraph:
    def __init__(self,owner):
        self.owner=owner;self.document=owner.document;self.selected=owner.event_id;self.drag=None;self.connection=None
        self.window=view_window(self,owner,'events','Event graph');self.window.geometry('1000x700')
        bar=ttk.Frame(self.window,padding=8);bar.pack(fill='x')
        for label,method in [('Edit',self.edit),('Connect',self.link),('Dialogue',self.branch),('Arrange',self.arrange),('Fit',self.fit)]:
            ttk.Button(bar,text=label,width=0,command=lambda f=method:guard(self,f)).pack(side='left',padx=3)
        more=ttk.Menubutton(bar,text='More');menu=tk.Menu(more,tearoff=False)
        for label,method in [('Objectives',self.objectives),('Playtest / checkpoints',self.debug)]:menu.add_command(label=label,command=lambda f=method:guard(self,f))
        more.configure(menu=menu);more.pack(side='left',padx=3)
        controls=ttk.Frame(self.window,padding=(8,0,8,5));controls.pack(fill='x')
        self.view_mode=tk.StringVar(value='Nearby events' if hasattr(self.window,'workspace') else 'All events')
        chooser=ttk.Combobox(controls,textvariable=self.view_mode,values=('Nearby events','All events'),width=16,state='readonly');chooser.pack(side='left');chooser.bind('<<ComboboxSelected>>',lambda _:self.draw())
        self.zoom=tk.StringVar(value='1');zoom=ttk.Combobox(controls,textvariable=self.zoom,values=('0.35','0.5','0.75','1','1.25','1.5'),width=5,state='readonly');zoom.pack(side='left',padx=8);zoom.bind('<<ComboboxSelected>>',lambda _:self.draw())
        ttk.Label(controls,text='Drag a named output to a node to connect it.',wraplength=320).pack(side='left')
        from editor_ui import flow_toolbar
        flow_toolbar(bar);flow_toolbar(controls)
        body=ttk.Frame(self.window);body.pack(fill='both',expand=True)
        self.canvas=tk.Canvas(body,background='#edf0f4',highlightthickness=0)
        y=ttk.Scrollbar(body,command=self.canvas.yview);x=ttk.Scrollbar(body,orient='horizontal',command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=y.set,xscrollcommand=x.set)
        y.pack(side='right',fill='y');x.pack(side='bottom',fill='x');self.canvas.pack(fill='both',expand=True)
        self.canvas.bind('<Button-1>',lambda e:guard(self,lambda:self.press(e)));self.canvas.bind('<B1-Motion>',self.motion);self.canvas.bind('<ButtonRelease-1>',lambda e:guard(self,lambda:self.release(e)))
        self.canvas.bind('<Double-1>',lambda e:guard(self,self.edit));self.properties=None
        if hasattr(self.window,'workspace'):
            workspace=self.window.workspace;panel=ttk.Frame(workspace.inspector)
            workspace.custom_inspectors[self.window.key]=panel;self.properties=EventProperties(self,panel)
            self.properties.select(self.selected);workspace.update_inspector()
        self.draw()

    def draw(self):
        self.canvas.delete('all');all_events=self.document.adventure['events'];saved=editor_data(self.document).get('event_layout',{})
        defaults=graph_arrangement(all_events);z=float(self.zoom.get())
        from tkinter import font as tkfont
        if not hasattr(self,'graph_font'):
            self.graph_font=tkfont.Font(family=tkfont.nametofont('TkDefaultFont').actual('family'))
        # Node geometry uses canvas pixels. Scale its labels with the graph,
        # so zooming out cannot leave full-size text overlapping other nodes.
        self.graph_font.configure(size=-max(6,round(13*z)))
        def label_text(value):
            if self.graph_font.measure(value)<=210*z:return value
            while value and self.graph_font.measure(value+'...')>210*z:value=value[:-1]
            return value+'...'
        self.positions={e['id']:saved.get(e['id'],defaults[e['id']]) for e in all_events}
        visible=graph_neighbours(all_events,self.selected) if self.view_mode.get()=='Nearby events' else set(self.positions)
        events=[e for e in all_events if e['id'] in visible]
        if self.drag:self.positions[self.drag[0]]=self.drag[3]
        for e in events:
            x,y=self.positions[e['id']]
            for index,(label,target) in enumerate(edges(e)):
                if target not in visible:continue
                tx,ty=self.positions[target];color='#407a95' if label not in ('failure','loss','flee') else '#ac655c'
                sy=y+65+index*18;mid=x+260 if tx>x+230 else x+275
                points=(x+230,sy,mid,sy,mid,ty+25,tx,ty+25)
                self.canvas.create_line(*[v*z for v in points],arrow='last',fill=color,width=2 if e['id']==self.selected else 1)
        for e in events:
            x,y=self.positions[e['id']];tag='node:'+e['id']
            height=max(85,70+len(edges(e))*18)
            self.canvas.create_rectangle(x*z,y*z,(x+230)*z,(y+height)*z,fill='#fff3cd' if e['id']==self.selected else '#ffffff',outline='#346b93',width=2,tags=tag)
            self.canvas.create_text((x+10)*z,(y+12)*z,anchor='nw',text=e['op'].upper(),font=self.graph_font,fill='#306383',tags=tag)
            self.canvas.create_text((x+10)*z,(y+34)*z,anchor='nw',text=label_text(e['id']),font=self.graph_font,fill='#273747',tags=tag)
            for index,(label,_) in enumerate(edges(e)):
                py=(y+65+index*18)*z;port='port|'+e['id']+'|'+label
                self.canvas.create_text((x+218)*z,py,anchor='e',text=label,font=self.graph_font,fill='#436477',tags=port)
                self.canvas.create_oval((x+226)*z,py-4,(x+234)*z,py+4,fill='#39748b',outline='',tags=port)
        bounds=self.canvas.bbox('all') or (0,0,900,600);self.canvas.configure(scrollregion=(0,0,max(bounds[2]+40,900),max(bounds[3]+40,600)))

    def press(self,event):
        x,y=self.canvas.canvasx(event.x),self.canvas.canvasy(event.y)
        if self.properties:self.properties.apply_pending()
        for item in reversed(self.canvas.find_overlapping(x,y,x,y)):
            port=next((t for t in self.canvas.gettags(item) if t.startswith('port|')),None)
            if port:self.connection=port.split('|')[1:];return
            tag=next((t[5:] for t in self.canvas.gettags(item) if t.startswith('node:')),None)
            if tag:
                self.selected=tag;p=list(self.positions[tag]);z=float(self.zoom.get());self.drag=(tag,x/z-p[0],y/z-p[1],p)
                if self.properties:self.properties.select(tag)
                self.draw();return

    def motion(self,event):
        if self.connection:
            self.canvas.delete('connecting');x,y=self.positions[self.connection[0]];z=float(self.zoom.get())
            self.canvas.create_line((x+230)*z,(y+65)*z,self.canvas.canvasx(event.x),self.canvas.canvasy(event.y),fill='#286c80',dash=(4,2),tags='connecting')
        if self.drag:
            z=float(self.zoom.get());key,dx,dy,_=self.drag;self.drag=(key,dx,dy,[max(0,self.canvas.canvasx(event.x)/z-dx),max(0,self.canvas.canvasy(event.y)/z-dy)]);self.draw()

    def release(self,_):
        if self.connection:
            source,branch=self.connection;self.connection=None;x,y=self.canvas.canvasx(_.x),self.canvas.canvasy(_.y)
            for item in reversed(self.canvas.find_overlapping(x,y,x,y)):
                target=next((t[5:] for t in self.canvas.gettags(item) if t.startswith('node:')),None)
                if target:connect(self.document,source,branch,target);break
            if self.properties:self.properties.select(self.selected)
            self.draw();return
        if self.drag:
            data=editor_data(self.document);data.setdefault('event_layout',{})[self.drag[0]]=self.drag[3]
            self.drag=None;editor_commit(self.document,data);self.draw()

    def edit(self):
        if not self.selected:return
        if self.properties:
            self.owner.event_id=self.selected;self.properties.select(self.selected);self.draw();return
        self.owner.apply_pending();self.owner.event_id=self.selected;self.owner.refresh_events();self.owner.populate_event()
        self.owner.tabs.select(self.owner.event_tab);self.owner.window.lift()

    def arrange(self):
        data=editor_data(self.document);data['event_layout']=graph_arrangement(self.document.adventure['events']);editor_commit(self.document,data);self.draw();self.fit()
    def fit(self):
        visible=graph_neighbours(self.document.adventure['events'],self.selected) if self.view_mode.get()=='Nearby events' else set(self.positions)
        points=[self.positions[i] for i in visible]
        if not points:return
        x0=min(p[0] for p in points);y0=min(p[1] for p in points)
        width=max(p[0] for p in points)+270;height=max(p[1] for p in points)+180
        z=max(.2,min(1.5,self.canvas.winfo_width()/max(1,width-x0),self.canvas.winfo_height()/max(1,height-y0)))
        self.zoom.set(str(round(z,2)));self.draw()
        sx,sy,ex,ey=map(float,self.canvas.cget('scrollregion').split())
        self.canvas.xview_moveto(max(0,(x0*z-20-sx)/max(1,ex-sx)));self.canvas.yview_moveto(max(0,(y0*z-20-sy)/max(1,ey-sy)))

    def link(self):
        from adventure_editor import Form
        if not self.selected:return
        e=next(e for e in self.document.adventure['events'] if e['id']==self.selected);branches=dict(edges(e))
        if not branches:raise EditorError('This event has no outgoing branches. Change its operation in Edit node first.')
        f=Form(self,'Connect event branch');key=next(iter(branches));f.field('branch',key,list(branches))
        f.field('destination',branches[key],[e['id'] for e in self.document.adventure['events']])
        def apply(v):connect(self.document,self.selected,v['branch'],v['destination']);self.owner.refresh();self.draw()
        f.submit(apply)

    def branch(self):
        from adventure_editor import Form
        if not self.selected:return
        f=Form(self,'New dialogue branch');f.field('label','Ask a question');f.field('text','The conversation continues.')
        def apply(v):dialogue_branch(self.document,self.selected,v['label'],v['text']);self.owner.refresh();self.draw()
        f.submit(apply)

    def objectives(self):return open_view(self.owner,'objectives',lambda:ObjectiveEditor(self.owner))
    def debug(self):
        from playtest_workbench import PlaytestWindow
        return open_view(self.owner,'playtest',lambda:PlaytestWindow(self.owner))

@recoverable_forms
class ObjectiveEditor:
    def __init__(self,owner):
        self.owner=owner;self.document=owner.document
        self.window=view_window(self,owner,'objectives','Objectives and journal');self.window.geometry('680x440')
        ttk.Label(self.window,text='Objectives appear when their Active flag is set; Complete flags retain finished entries.',padding=12,wraplength=640).pack(fill='x')
        self.listing=tk.Listbox(self.window,exportselection=False);self.listing.pack(fill='both',expand=True,padx=12)
        bar=ttk.Frame(self.window,padding=12);bar.pack(fill='x')
        for text,method in [('New',lambda:self.edit(True)),('Edit',lambda:self.edit(False)),('Delete',self.delete)]:ttk.Button(bar,text=text,command=lambda f=method:guard(self,f)).pack(side='left',padx=4)
        self.listing.bind('<Double-1>',lambda _:guard(self,lambda:self.edit(False)));self.refresh()
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
        f=Form(self,'Objective')
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
