"""Paired planet previews, with bounded detail jobs and explicit navigation."""
import hashlib
from pathlib import Path
import re
import tkinter as tk
from tkinter import ttk

from authoring_contract import AuthoringError
from editor_canvas import CanvasZoom
from editor_session import guard
from editor_ui import flow_toolbar,tooltip
from world_editing import all_worlds
from world_review import overlap
import authoring_review as review


class WorldReviewPane:
    def __init__(self,owner,parent):
        self.owner=owner;self.parent=parent;self.record={};self.folder=None;self.job=None;self.generation=0
        self.change=None;self.point=None;self.items=[];self.locations=[];self.photos=[];self.originals={}
        self.world=tk.StringVar();self.note=tk.StringVar(value='No changed worlds in this proposal.')
        bar=ttk.Frame(parent,padding=4);bar.pack(fill='x')
        self.choice=ttk.Combobox(bar,textvariable=self.world,state='readonly',width=22);self.choice.pack(side='left',padx=3)
        self.choice.bind('<<ComboboxSelected>>',lambda _:self.safe(self.choose))
        for title,callback in [('Overview',self.overview),('Detail',self.detail)]:
            ttk.Button(bar,text=title,width=0,command=lambda f=callback:self.safe(f)).pack(side='left',padx=3,pady=3)
        navigate=ttk.Menubutton(bar,text='Edit...',width=0);navigate.pack(side='left',padx=3,pady=3)
        menu=tk.Menu(navigate,tearoff=False);navigate.configure(menu=menu)
        menu.add_command(label='Open location in planet editor',command=lambda:self.safe(self.open_location))
        menu.add_command(label='Open selected town map',command=lambda:self.safe(self.open_town))
        flow_toolbar(bar)
        note=ttk.Label(parent,textvariable=self.note,wraplength=500,padding=(8,3));note.pack(fill='x')
        parent.bind('<Configure>',lambda event:note.configure(wraplength=max(160,event.width-20)),add='+')
        host=ttk.Frame(parent);host.pack(fill='x',padx=6,pady=4)
        self.listing=ttk.Treeview(host,columns=('change','location'),show='tree headings',height=2,selectmode='browse')
        for key,title,width in [('#0','Changed location / protected region',220),('change','Change',120),('location','World tiles',130)]:
            self.listing.heading(key,text=title);self.listing.column(key,width=width,minwidth=60)
        sy=ttk.Scrollbar(host,command=self.listing.yview);sy.pack(side='right',fill='y')
        self.listing.configure(yscrollcommand=sy.set);self.listing.pack(fill='both',expand=True)
        self.listing.bind('<<TreeviewSelect>>',lambda _:self.safe(self.select))
        self.listing.bind('<Double-1>',lambda _:self.safe(self.detail))
        self.listing.bind('<Return>',lambda _:self.safe(self.detail))
        compact=ttk.Frame(parent,padding=(6,2));self.location_choice=ttk.Combobox(compact,state='readonly')
        self.location_choice.pack(fill='x');self.location_choice.bind('<<ComboboxSelected>>',lambda _:self.choose_location())
        self.location_choice.bind('<Return>',lambda _:self.safe(self.detail))
        pair=ttk.Panedwindow(parent,orient='horizontal');pair.pack(fill='both',expand=True)
        location_host=host
        # Capture the table host before the per-side preview hosts below reuse
        # the local variable, so Configure cannot hide a preview by mistake.
        def resize_locations(event,table=location_host):
            # Reserve room for pictures in a short dock; retain the full
            # location table when a taller workspace can accommodate it.
            short=event.height<420
            if short and table.winfo_manager():table.pack_forget();compact.pack(fill='x',before=pair)
            elif not short and compact.winfo_manager():compact.pack_forget();table.pack(fill='x',padx=6,pady=4,before=pair)
        parent.bind('<Configure>',resize_locations,add='+')
        self.canvases={};self.scales={};self.controls={};self.displayed={}
        for side in ('before','after'):
            host=ttk.Frame(pair);pair.add(host,weight=1);bar=ttk.Frame(host);bar.pack(fill='x')
            ttk.Label(bar,text=side.title(),style='Section.TLabel').pack(side='left',padx=6)
            scale=self.scales[side]=tk.StringVar(value='1')
            control=self.controls[side]=CanvasZoom(bar,scale,self.redraw,base=2,steps=(1,2,3,4));control.pack(side='right')
            area=ttk.Frame(host);area.pack(fill='both',expand=True)
            canvas=self.canvases[side]=tk.Canvas(area,background='#263842',highlightthickness=0)
            sy=ttk.Scrollbar(area,command=canvas.yview);sy.pack(side='right',fill='y')
            sx=ttk.Scrollbar(area,orient='horizontal',command=canvas.xview);sx.pack(side='bottom',fill='x')
            canvas.configure(xscrollcommand=sx.set,yscrollcommand=sy.set);canvas.pack(fill='both',expand=True);control.attach(canvas)
            canvas.bind('<Button-1>',lambda event,s=side:self.safe(lambda:self.click(event,s)))
            canvas.bind('<Double-1>',lambda event,s=side:self.safe(lambda:self.click(event,s,True)))
        legend=ttk.Label(parent,text='Orange: changes   Yellow: towns   Cyan: protected',padding=(8,4));legend.pack(side='bottom',fill='x',before=pair)
        tooltip(legend,'Changed bounds may include unchanged tiles. Select a row or click a planet; Detail shows 32 × 32 full-resolution tiles. Ctrl + wheel zooms.')
        parent.bind('<Destroy>',self.destroyed,add='+')

    def safe(self,callback):return guard(self.owner,callback,publish=False)

    def cancel(self):
        self.generation+=1
        if self.job:self.job.cancelled.set();self.job=None

    def destroyed(self,event):
        if event.widget is self.parent:self.cancel()

    def load(self,record,folder):
        self.cancel();self.record=record;self.folder=Path(folder);self.originals={}
        worlds=record.get('world_changes',[]);self.identities=[w['id'] for w in worlds]
        self.choice.configure(values=[w['name']+' | '+w['id'] for w in worlds])
        selected=self.change['id'] if self.change else None
        self.choice.current(self.identities.index(selected) if selected in self.identities else 0) if worlds else self.world.set('')
        self.choose()
        if worlds:self.owner.status.set('World changes are available in Worlds. Review groups before applying.')

    def choose(self):
        self.cancel();index=self.choice.current();worlds=self.record.get('world_changes',[])
        self.change=worlds[index] if 0<=index<len(worlds) else None;self.point=None;self.locations=[]
        self.listing.delete(*self.listing.get_children())
        if self.change:
            for town in self.change['towns']:
                self.locations.append(dict(town,title=town['name'],kind='town'))
            for region in self.change['areas']:
                self.locations.append(dict(title='Terrain / tile appearance',kind='terrain',change=str(region['changed_tiles'])+' tiles',before=region['rect'],after=region['rect']))
            for rule in self.record.get('conflicts',[]):
                if rule.get('world')==self.change['id'] and rule.get('rect'):
                    self.locations.append(dict(title=rule['label'],kind='protected',change='Protected conflict',before=rule['rect'],after=rule['rect']))
            for i,location in enumerate(self.locations):
                self.listing.insert('','end',iid=str(i),text=location['title'],values=(location['change'],str(location.get('after') or location['before'])))
            if self.locations:self.listing.selection_set('0')
        self.location_choice.configure(values=[item['title']+' | '+item['change']+' | '+str(item.get('after') or item['before']) for item in self.locations])
        if self.locations:self.location_choice.current(0)
        else:self.location_choice.set('No located changes')
        self.overview()

    def overview(self):
        self.cancel();identity=self.change['id'] if self.change else None
        self.items=[a for a in self.record.get('artifacts',[]) if a['kind']=='world' and a['id']==identity]
        self.mode='overview';self.redraw()
        self.note.set(f"{self.change['name']}: {self.change['changed_tiles']:,} changed tile locations. Sampled overview; detail uses full tile pixels." if self.change else 'No changed worlds in this proposal.')

    def selected(self):
        selection=self.listing.selection()
        return self.locations[int(selection[0])] if selection else None

    def select(self):
        item=self.selected()
        if item:
            self.location_choice.current(int(self.listing.selection()[0]))
            rect=item.get('after') or item['before'];self.point=(rect[0]+rect[2]//2,rect[1]+rect[3]//2)
            self.redraw()

    def choose_location(self):
        index=self.location_choice.current()
        if index>=0:self.listing.selection_set(str(index));self.select()

    def click(self,event,side,detail=False):
        artifact=self.displayed.get(side)
        if artifact is None:return
        scale=artifact['pixels_per_tile']*int(self.scales[side].get())/2;canvas=self.canvases[side]
        x=int(canvas.canvasx(event.x)//scale)+artifact['rect'][0];y=int(canvas.canvasy(event.y)//scale)+artifact['rect'][1]
        if overlap([x,y,1,1],artifact['rect']) is None:return
        self.listing.selection_remove(*self.listing.selection());self.point=(x,y);self.redraw()
        if detail:self.detail()

    def detail(self):
        if self.change is None:raise AuthoringError('preview.unavailable','Select a changed world first.')
        if self.point is None:self.select()
        if self.point is None:raise AuthoringError('preview.location','Select a changed location or click a planet preview.')
        self.cancel();stamp=self.generation;identity=self.change['id'];folder=self.folder
        width=max((self.change.get(side) or [0,0])[0] for side in ('before','after'))
        height=max((self.change.get(side) or [0,0])[1] for side in ('before','after'))
        w,h=min(32,width),min(32,height);x,y=self.point
        rect=[max(0,min(width-w,x-w//2)),max(0,min(height-h,y-h//2)),w,h]
        settings=dict(self.owner.owner.settings);validator=self.owner.document.validator
        self.note.set('Rendering matching full-detail crops from the retained before/after snapshots…')
        def done(items):
            if stamp!=self.generation:return
            self.job=None;self.items=items;self.mode='detail';self.redraw()
            self.note.set('Detail: '+str(rect)+' world tiles. Both sides show the same location.')
        def failed(error):
            if stamp!=self.generation:return
            self.job=None;self.note.set(str(error));self.owner.show_error(error)
        # Workers receive immutable paths/settings only. Switching proposals or
        # planets cancels the job; an older completion cannot replace this view.
        self.job=self.owner.workspace.tasks.submit('Render world detail',self.owner,
            lambda cancel:review.world_crop(folder,identity,rect,validator,settings=settings,cancelled=cancel.is_set),done,failed,quiet=True)
        return self.job

    def redraw(self):
        self.photos=[];self.displayed={}
        for side,canvas in self.canvases.items():
            canvas.delete('all');canvas.configure(scrollregion=(0,0,1,1))
            found=next((a for a in self.items if a['side']==side),None)
            if not found:
                missing=self.change and not self.change.get(side)
                canvas.create_text(12,16,anchor='nw',fill='#ffffff',width=240,text='This planet is absent in this snapshot.' if missing else 'No preview for this side. See Checks for missing graphics or preview errors.');continue
            artifact=found['artifact'];key=(artifact['path'],artifact['sha256'])
            if key not in self.originals:
                payload=Path(artifact['path']).read_bytes()
                if hashlib.sha256(payload).hexdigest()!=artifact['sha256']:raise AuthoringError('review.changed','World preview changed on disk; prepare a fresh review.')
                match=re.search(rb'href="data:image/png;base64,([^"]+)"',payload)
                if not match:raise AuthoringError('preview.invalid','World preview has no tile image.')
                self.originals[key]=tk.PhotoImage(master=self.parent,data=match[1],format='png')
                # Keep only the active overview/detail pair, not every crop a
                # long editing session has opened.
                if len(self.originals)>4:self.originals.pop(next(iter(self.originals)))
            step=int(self.scales[side].get());photo=self.originals[key].zoom(step).subsample(2);self.photos.append(photo)
            canvas.create_image(0,0,anchor='nw',image=photo);canvas.configure(scrollregion=(0,0,photo.width(),photo.height()))
            self.displayed[side]=artifact;scale=artifact['pixels_per_tile']*step/2;rect=artifact['rect']
            for items,color,tag in [(artifact.get('regions',[]),'#ff8050','changes'),(artifact.get('towns',[]),'#ffff50','towns'),(artifact.get('protections',[]),'#32d5ed','protections')]:
                for item in items:
                    hit=overlap(item['rect'],rect)
                    if not hit:continue
                    x,y,w,h=hit;x=(x-rect[0])*scale;y=(y-rect[1])*scale
                    canvas.create_rectangle(x,y,x+w*scale,y+h*scale,outline=color,width=2,tags=tag)
                    if 'name' in item:canvas.create_text(x+3,y+2,anchor='nw',text=item['name'],fill=color,tags=tag)
            selected=self.selected();highlight=(selected.get(side) if selected else None)
            if highlight and (hit:=overlap(highlight,rect)):
                x,y,w,h=hit;x=(x-rect[0])*scale;y=(y-rect[1])*scale
                canvas.create_rectangle(x,y,x+w*scale,y+h*scale,outline='#ffffff',width=2,dash=(4,3),tags='selected')
            if self.point and overlap([*self.point,1,1],rect):
                x=(self.point[0]-rect[0]+.5)*scale;y=(self.point[1]-rect[1]+.5)*scale
                canvas.create_line(x-6,y,x+6,y,fill='#ffffff',width=2,tags='point');canvas.create_line(x,y-6,x,y+6,fill='#ffffff',width=2,tags='point')

    def open_location(self):
        if self.change is None:raise AuthoringError('object.missing','Select a world first.')
        if not any(w['id']==self.change['id'] for w in all_worlds(self.owner.document.adventure or {})):
            raise AuthoringError('object.missing','This planet exists only in a retained snapshot. Review it here; apply its creation before editing it.')
        if self.point is None:self.select()
        if self.point is None:raise AuthoringError('preview.location','Click a location in the planet preview first.')
        maps=self.owner.workspace.map_view();maps.edit_landscape();world=maps.world_editor
        world.show_location(self.change['id'],self.point,'Reviewed location in the current editable project. The before/after snapshots remain in Changes.','world_tile')
        return world

    def open_town(self):
        item=self.selected()
        if not item or item['kind']!='town':raise AuthoringError('object.missing','Select a town row first.')
        if not any(m['id']==item['id'] for m in self.owner.document.adventure['maps']):
            raise AuthoringError('object.missing','This town exists only in a retained snapshot; apply its creation before editing it.')
        self.owner.workspace.open_map(item['id'])
