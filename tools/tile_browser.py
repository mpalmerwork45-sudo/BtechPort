"""Visual tile management, shared by painting and construction part pickers."""
import copy
import tkinter as tk
from tkinter import ttk
from editor_model import EditorError,encoded
from editor_session import guard,visible_parent,scope_of,apply_draft
from tile_editing import create_tile,clone_sheet,ensure_tile,tile,select_tile,edit_pixels,metadata,sheet_graphics


class TileBrowser:
    def __init__(self,maps,form=None,choose=None,selected=None):
        self.owner=maps;self.document=maps.document;self.form=form;self.choose=choose;self.timer=None
        self.window=tk.Toplevel(visible_parent(form or maps));self.window.title('Choose tile graphic')
        self.window.transient(visible_parent(form or maps));self.window.geometry('760x650');self.window.minsize(560,410)
        self.previous_grab=self.window.grab_current();self.window.grab_set()
        self.window.protocol('WM_DELETE_WINDOW',self.close);self.window.bind('<Escape>',lambda _:self.close())
        self.window.bind('<Destroy>',self.destroyed,add='+')
        self.status=tk.StringVar();self.selected=None;self.keys=[];self.columns=12;self.cell=54
        header=ttk.Frame(self.window,padding=10);header.pack(fill='x')
        ttk.Label(header,text='Choose a map tile',style='Heading.TLabel').pack(anchor='w')
        initial=form.values['sheet'].get() if form else ('Project tiles' if selected else 'All tiles')
        self.sheet=tk.StringVar(value=initial)
        # Construction parts start on the project's paint palette, but the
        # complete source atlas must be an obvious, separate browsing option.
        source_bar=ttk.Frame(header);source_bar.pack(fill='x',pady=(8,0))
        self.mode=tk.StringVar();self.mode_buttons={}
        for name in ('Project tiles','All tiles'):
            button=ttk.Radiobutton(source_bar,text=name,variable=self.mode,value=name,command=lambda name=name:self.show_collection(name))
            button.pack(side='left',padx=(0,10));self.mode_buttons[name]=button
        ttk.Label(source_bar,text='Sheet').pack(side='left',padx=(8,4))
        self.choices=ttk.Combobox(source_bar,textvariable=self.sheet,state='readonly',width=22);self.choices.pack(side='left')
        self.choices.bind('<<ComboboxSelected>>',lambda _:self.refresh())
        bar=ttk.Frame(self.window,padding=(8,0));bar.pack(fill='x')
        for label,callback in [('Add tile',self.new),('Clone',self.clone),('Edit pixels',self.edit),('Properties',self.properties),('Remove',self.remove)]:
            ttk.Button(bar,text=label,width=0,command=lambda f=callback:guard(self,f)).pack(side='left',padx=3)
        more=ttk.Menubutton(bar,text='More');menu=tk.Menu(more,tearoff=False);more.configure(menu=menu);more.pack(side='left',padx=3)
        menu.add_command(label='Clone ALL tiles in this view to project tiles',command=lambda:guard(self,self.clone_all))
        menu.add_command(label='Restore hidden source graphics',command=lambda:guard(self,self.unhide))
        from editor_ui import flow_toolbar
        flow_toolbar(source_bar);flow_toolbar(bar)
        footer=ttk.Frame(self.window,padding=10);footer.pack(side='bottom',fill='x')
        ttk.Button(footer,text='Use graphic',style='Accent.TButton',command=lambda:guard(self,self.use)).pack(side='right')
        ttk.Button(footer,text='Cancel',command=self.close).pack(side='right',padx=8)
        ttk.Label(self.window,textvariable=self.status,wraplength=700,padding=8).pack(side='bottom',fill='x')
        shell=ttk.Frame(self.window,padding=(10,4));shell.pack(fill='both',expand=True)
        self.canvas=tk.Canvas(shell,background='#edf1f2',highlightthickness=0)
        sx=ttk.Scrollbar(shell,orient='horizontal',command=self.canvas.xview);sy=ttk.Scrollbar(shell,command=self.canvas.yview)
        sx.pack(side='bottom',fill='x');sy.pack(side='right',fill='y');self.canvas.pack(fill='both',expand=True)
        self.canvas.configure(xscrollcommand=sx.set,yscrollcommand=sy.set)
        self.canvas.bind('<Button-1>',self.click);self.canvas.bind('<Double-1>',lambda e:(self.click(e),guard(self,self.use)))
        self.canvas.bind('<Button-3>',self.context)
        for sequence,delta in [('<Button-4>',-3),('<Button-5>',3)]:self.canvas.bind(sequence,lambda _,n=delta:self.canvas.yview_scroll(n,'units'))
        self.canvas.bind('<MouseWheel>',lambda e:self.canvas.yview_scroll(-3 if e.delta>0 else 3,'units'))
        self.window.bind('<Return>',lambda _:guard(self,self.use))
        self.selected=selected if selected else (form.values['graphic'].get() if form else None)
        if form and initial!='package:art':
            try:self.selected=int(self.selected)
            except ValueError:self.selected=None
        self.refresh();self.revision=self.document.revision;self.timer=self.window.after(250,self.poll)

    def show_error(self,error):self.status.set(str(error));self.window.lift()
    def destroyed(self,event):
        if event.widget is self.window:
            if self.timer:self.window.after_cancel(self.timer);self.timer=None
            if self.previous_grab is not None and self.previous_grab.winfo_exists():self.previous_grab.grab_set()
    def close(self):
        if self.window.winfo_exists():self.window.destroy()
    def poll(self):
        self.timer=None
        if self.document.revision!=self.revision:self.revision=self.document.revision;self.refresh()
        self.timer=self.window.after(250,self.poll)
    def show_collection(self,name):
        previous=self.source() if self.selected is not None else None
        self.sheet.set(name)
        if previous:
            self.selected=(previous['sheet'],previous['graphic']) if name=='All tiles' else next((t['id'] for t in self.document.adventure['tiles'] if t['sheet']==previous['sheet'] and t['graphic']==previous['graphic']),None)
        self.refresh()
        row=self.keys.index(self.selected)//self.columns if self.selected is not None else 0
        self.canvas.yview_moveto(row/max(1,(len(self.keys)+self.columns-1)//self.columns))
    def value(self,key):
        if self.sheet.get()=='Project tiles':return tile(self.document,key)
        bank,graphic=key if self.sheet.get()=='All tiles' else (self.sheet.get(),key)
        return dict(sheet=bank,graphic=graphic)
    def refresh(self):
        self.owner.refresh();self.choices.configure(values=['All tiles',*self.owner.graphics])
        self.canvas.delete('all');sheet=self.sheet.get();data=metadata(self.document)
        self.mode.set('Project tiles' if sheet=='Project tiles' else 'All tiles')
        self.choices.configure(state='disabled' if sheet=='Project tiles' else 'readonly')
        hidden=data.get('hidden_tile_graphics',[])
        if sheet=='Project tiles':self.keys=[t['id'] for t in self.document.adventure['tiles']]
        elif sheet=='All tiles':self.keys=[(bank,key) for bank,key in sheet_graphics(self.owner.graphics) if [bank,str(key)] not in hidden]
        else:
            source=self.owner.graphics.get(sheet,{})
            self.keys=[k for k in (source if isinstance(source,dict) else range(len(source))) if [sheet,str(k)] not in hidden]
        names=data.get('tile_names',{})
        for index,key in enumerate(self.keys):
            value=self.value(key)
            x,y=index%self.columns*self.cell,index//self.columns*self.cell
            image=self.owner.tile_image(value['sheet'],value['graphic'],32)
            if image:self.canvas.create_image(x+27,y+20,image=image)
            label=(value['sheet'].split(':')[-1][:4]+' '+str(value['graphic']).split(':')[-1]) if sheet=='All tiles' else names.get(key,key.split(':')[-1] if isinstance(key,str) else str(key))
            self.canvas.create_text(x+27,y+45,text=label[:8],fill='#31434b',font='TkSmallCaptionFont')
        self.canvas.configure(scrollregion=(0,0,self.columns*self.cell,((len(self.keys)+self.columns-1)//self.columns)*self.cell))
        self.select(self.selected if self.selected in self.keys else (self.keys[0] if self.keys else None))
    def select(self,key):
        self.selected=key;self.canvas.delete('selection')
        if key is None:self.status.set('No tiles here. Add a tile or restore hidden source graphics.');return
        index=self.keys.index(key);x,y=index%self.columns*self.cell,index//self.columns*self.cell
        self.canvas.create_rectangle(x+1,y+1,x+self.cell-1,y+self.cell-1,outline='#286c80',width=3,tags='selection')
        value=self.value(key)
        registered='id' in value or any(t['sheet']==value['sheet'] and t['graphic']==value['graphic'] for t in self.document.adventure['tiles'])
        action='Uses an existing project tile.' if registered else 'Automatically adds this graphic to project tiles when chosen.'
        self.status.set(f"{value['sheet']} | {value['graphic']} | {action} Double-click to use.")
    def click(self,event):
        x,y=self.canvas.canvasx(event.x),self.canvas.canvasy(event.y);index=int(y//self.cell)*self.columns+int(x//self.cell)
        if 0<=x<self.columns*self.cell and 0<=index<len(self.keys):self.select(self.keys[index])
    def source(self):
        if self.selected is None:raise EditorError('Select a tile first.')
        return self.value(self.selected)
    def definition(self):
        source=self.source()
        return source['id'] if 'id' in source else ensure_tile(self.document,source['sheet'],source['graphic'])
    def new(self):
        value=create_tile(self.document,name='New map tile');self.sheet.set('Project tiles');self.selected=value;self.refresh();self.edit()
    def clone(self):
        value=create_tile(self.document,self.owner.graphics,self.source(),'Map tile copy')
        self.sheet.set('Project tiles');self.selected=value;self.refresh()
    def clone_all(self):
        values=clone_sheet(self.document,self.owner.graphics,self.sheet.get())
        self.sheet.set('Project tiles');self.selected=values[0];self.refresh();self.status.set(f'Cloned {len(values)} editable tiles into project tiles. Undo removes this whole batch.')
    def use(self):
        source=self.source()
        if self.form:self.form.values['sheet'].set(source['sheet']);self.form.values['graphic'].set(str(source['graphic']))
        else:
            value=self.definition();select_tile(self.owner,value);self.owner.tool.set('Paint')
            if self.choose:self.choose(value)
        self.close()
    def prepare_edit(self):
        value=self.definition()
        if self.form:
            source=tile(self.document,value);self.form.values['sheet'].set(source['sheet']);self.form.values['graphic'].set(str(source['graphic']))
            apply_draft(self.form)
        if self.choose:self.choose(value)
        self.close();return value
    def edit(self):edit_pixels(self.owner,self.prepare_edit())
    def properties(self):
        value=self.prepare_edit();select_tile(self.owner,value);self.owner.edit_tile()
    def remove(self):
        if self.sheet.get()=='Project tiles':
            from editor_dependencies import dialog
            identity=self.definition();self.close();return dialog(self.owner,identity,delete=True)
        source=self.source()
        if source['sheet']=='package:art':
            from editor_dependencies import dialog
            self.close();return dialog(self.owner,source['graphic'],delete=True)
        data=metadata(self.document);data.setdefault('hidden_tile_graphics',[]).append([source['sheet'],str(source['graphic'])])
        from event_workbench import editor_commit
        editor_commit(self.document,data);self.refresh();self.status.set('Source graphic hidden from this project’s chooser. More > Restore hidden source graphics brings it back.')
    def unhide(self):
        from event_workbench import editor_commit
        data=metadata(self.document);data.pop('hidden_tile_graphics',None);editor_commit(self.document,data);self.refresh()
    def context(self,event):
        self.click(event);menu=tk.Menu(self.window,tearoff=False)
        for label,callback in [('Use tile',self.use),('Add new tile',self.new),('Clone tile',self.clone),('Edit pixels',self.edit),('Tile properties',self.properties),('Remove',self.remove)]:menu.add_command(label=label,command=lambda f=callback:guard(self,f))
        try:menu.tk_popup(event.x_root,event.y_root)
        finally:
            if self.window.winfo_exists():menu.grab_release();self.window.grab_set()
