"""The same asset search used by automated authors, in the human workspace."""
import copy
import tkinter as tk
from tkinter import ttk,filedialog
from pathlib import Path

from asset_catalogue import catalogue,search,annotate,metadata
from authoring_visuals import VisualSource,png,contact_sheet,animation_strip,event_graph
from editor_model import EditorError
from editor_session import guard
from editor_workspace import view_window


class CatalogueBrowser:
    def __init__(self,owner):
        self.owner=owner;self.document=owner.document;self.timer=None;self.photos=[];self.records={}
        self.window=view_window(self,owner,'catalogue','Content catalogue');self.window.geometry('1030x740')
        self.query=tk.StringVar();self.source=tk.StringVar(value='project');self.status=tk.StringVar()
        bar=ttk.Frame(self.window,padding=10);bar.pack(fill='x')
        ttk.Label(bar,text='Content catalogue',style='Heading.TLabel').pack(side='left',padx=(0,16))
        box=ttk.Combobox(bar,textvariable=self.source,values=['project','library','atlas'],state='readonly',width=12)
        box.pack(side='left');box.bind('<<ComboboxSelected>>',lambda _:guard(self,self.reload))
        ttk.Entry(bar,textvariable=self.query).pack(side='left',fill='x',expand=True,padx=10)
        ttk.Button(bar,text='Search',command=lambda:guard(self,self.refresh)).pack(side='left')
        self.window.bind('<Return>',lambda _:guard(self,self.refresh))
        ttk.Label(self.window,text='Words or filters: kind:tile tag:industrial animated:true | kind:mech class:light weapon:lrm walk>=5',
                  style='Muted.TLabel',padding=(10,0,10,8)).pack(fill='x')
        buttons=ttk.Frame(self.window,padding=(8,0));buttons.pack(fill='x')
        for label,callback in [('Use on map',self.use),('Edit names / tags',self.edit),('Contact sheet...',self.sheet),
                               ('Animation strip...',self.strip),('Event graph...',self.graph),('Reload',self.reload)]:
            ttk.Button(buttons,text=label,width=0,command=lambda f=callback:guard(self,f)).pack(side='left',padx=3)
        from editor_ui import flow_toolbar
        flow_toolbar(bar);flow_toolbar(buttons)
        body=ttk.Panedwindow(self.window,orient='horizontal');body.pack(fill='both',expand=True,padx=10,pady=10)
        left=ttk.Frame(body);right=ttk.Frame(body);body.add(left,weight=3);body.add(right,weight=2)
        self.listing=ttk.Treeview(left,columns=('kind','dependency'),show='tree headings',selectmode='browse')
        for key,label,width in [('#0','Asset',280),('kind','Type',90),('dependency','Art dependency',110)]:
            self.listing.heading(key,text=label);self.listing.column(key,width=width,stretch=key=='#0')
        sy=ttk.Scrollbar(left,command=self.listing.yview);sy.pack(side='right',fill='y')
        self.listing.configure(yscrollcommand=sy.set);self.listing.pack(fill='both',expand=True)
        self.listing.bind('<<TreeviewSelect>>',lambda _:guard(self,self.show))
        self.canvas=tk.Canvas(right,height=210,background='#dbe3e5',highlightthickness=0);self.canvas.pack(fill='x')
        self.detail=tk.Text(right,width=32,height=10,wrap='word',font='TkDefaultFont',borderwidth=0)
        self.detail.pack(fill='both',expand=True,pady=8)
        ttk.Label(self.window,textvariable=self.status,padding=8,wraplength=950).pack(fill='x')
        self.window.bind('<Destroy>',self.destroyed,add='+');self.reload()

    def show_error(self,error):self.status.set(str(error))
    def destroyed(self,event):
        if event.widget is self.window and self.timer:self.window.after_cancel(self.timer);self.timer=None
    def reload(self):
        source=self.source.get();self.visuals=VisualSource(self.document,self.owner.settings)
        # Source-atlas discovery needs decoding. Ordinary project searches
        # still work when the original art directory is unavailable.
        self.items=catalogue(self.document,source,self.owner.settings.get('library-root',Path(__file__).resolve().parents[1]/'work/unit-library'),
                             self.visuals.tiles if source=='atlas' else None)
        self.refresh()
    def refresh(self):
        result=search(self.items,self.query.get(),0,100);self.records={r['key']:r for r in result['items']}
        self.listing.delete(*self.listing.get_children())
        for item in self.records.values():self.listing.insert('','end',iid=item['key'],text=item['name'],values=(item['kind'],item.get('dependency','')))
        if self.records:self.listing.selection_set(next(iter(self.records)))
        self.status.set(f"{result['total']} matches; showing first {len(self.records)}. Refine the search to narrow the list.")
        self.show()
    def selected(self):
        values=self.listing.selection()
        if not values:raise EditorError('Select an asset first.')
        return self.records[values[0]]
    def show(self):
        if self.timer:self.window.after_cancel(self.timer);self.timer=None
        self.canvas.delete('all');self.photos=[]
        if not self.listing.selection():return
        item=self.selected();details=item['name']+'\n'+item['key']+'\n\n'+item.get('description','')+'\n\nTags: '+', '.join(item.get('tags',[]))
        if 'weapons' in item:details+='\nWeapons: '+', '.join(w['name'] for w in item['weapons'])
        if 'derived_roles' in item:details+='\nDerived roles: '+', '.join(item['derived_roles'])+'\n'+item['role_basis']
        details+='\nArt dependency: '+item.get('dependency','project')
        self.detail.configure(state='normal');self.detail.delete('1.0','end');self.detail.insert('1.0',details);self.detail.configure(state='disabled')
        try:frames,ticks=self.visuals.frames(item)
        except EditorError as error:self.canvas.create_text(12,16,anchor='nw',text=str(error),width=260);return
        # Keep Tk images local to this tab. Preview clocks never mutate data.
        for rows in frames[:256]:
            photo=tk.PhotoImage(master=self.window,data=png(rows))
            zoom=max(1,min(6,180//max(photo.width(),photo.height())))
            photo=photo.zoom(zoom) if max(photo.width(),photo.height())<=180 else photo.subsample(max(1,(max(photo.width(),photo.height())+179)//180))
            self.photos.append(photo)
        def animate(n=0):
            self.canvas.delete('all');self.canvas.create_image(145,105,image=self.photos[n%len(self.photos)])
            if len(self.photos)>1:self.timer=self.window.after(ticks*32,lambda:animate(n+1))
        animate()
    def edit(self):
        from adventure_editor import Form
        item=self.selected()
        if item['source']=='library':
            raise EditorError('Use Edit unit in the Unit Library, then Content catalogue in that editing scope to annotate the blueprint.')
        form=Form(self,'Asset description and tags')
        form.field('name',item['name']);form.field('description',item.get('description',''))
        form.field('tags',', '.join(item.get('tags',[])))
        for side in ('north','east','south','west'):form.field(side,item.get('edges',{}).get(side,''))
        def apply(values):
            changes=dict(name=values['name'],description=values['description'],tags=[t.strip() for t in values['tags'].split(',') if t.strip()],
                edges={s:values[s] for s in ('north','east','south','west') if values[s]})
            with self.document.command('Describe asset'):annotate(self.document,item['id'],changes)
            self.reload()
        form.submit(apply);return form
    def use(self):
        from tile_editing import ensure_tile,select_tile
        item=self.selected();self.owner.edit_adventure();maps=self.owner.map_editor
        if item['kind']=='tile':
            identity=item['id'] if item['source']=='project' else ensure_tile(self.document,item['sheet'],item['graphic'])
            maps.refresh();select_tile(maps,identity);maps.tool.set('Paint');maps.window.lift()
        elif item['kind']=='pattern':
            pattern=next(v for v in __import__('event_editing').editor_data(self.document)['map_patterns'] if v['id']==item['id'])
            maps.use_pattern(pattern['rows'],pattern['name']);maps.window.lift()
        else:raise EditorError('Use a tile or pattern here. Import units through the Unit Library; draw construction sets with their map tools.')
    def output(self,title):
        value=filedialog.asksaveasfilename(parent=self.window,title=title,defaultextension='.svg',filetypes=[('SVG visual','*.svg')])
        return Path(value) if value else None
    def sheet(self):
        path=self.output('Export labelled contact sheet')
        if path:
            result=contact_sheet(self.document,list(self.records.values())[:32],path,self.owner.settings)
            self.status.set('Saved '+result['artifact']['path'])
    def strip(self):
        path=self.output('Export animation frame strip')
        if path:self.status.set('Saved '+animation_strip(self.document,self.selected(),path,self.owner.settings)['artifact']['path'])
    def graph(self):
        path=self.output('Export event graph')
        if path:self.status.set('Saved '+event_graph(self.document,path)['artifact']['path'])


def open_catalogue(owner):
    from editor_workspace import open_view
    return open_view(owner,'catalogue',lambda:CatalogueBrowser(owner))
