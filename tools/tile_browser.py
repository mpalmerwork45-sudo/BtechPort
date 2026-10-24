"""Visual tile management, shared by painting and construction part pickers."""
import copy
import hashlib
import json
import tkinter as tk
from tkinter import ttk
from editor_model import EditorError,ProjectDocument,encoded
from editor_session import guard,visible_parent,scope_of,apply_draft,modal
from tile_editing import create_tile,clone_sheet,ensure_tile,tile,select_tile,edit_pixels,metadata,sheet_graphics
from tile_animation import tile_loop,loop_label


class TileBrowser:
    def __init__(self,maps,form=None,choose=None,selected=None):
        self.owner=maps;self.document=maps.document;self.form=form;self.choose=choose;self.timer=None;self.position_job=None
        # Browsing position is an editor preference, not game data or an Undo
        # operation. Keep it per project, including across editor restarts.
        key=hashlib.sha256(str(self.document.root.resolve()).encode()).hexdigest()[:20]
        self.memory_path=maps.parent.state_dir/'tile-browsers'/(key+'.json')
        try:self.memory=json.loads(self.memory_path.read_text())
        except (OSError,ValueError):self.memory={}
        if not isinstance(self.memory,dict):self.memory={}
        if not isinstance(self.memory.get('views'),dict):self.memory['views']={}
        self.window=tk.Toplevel(visible_parent(form or maps));self.window.title('Choose tile graphic')
        self.window.transient(visible_parent(form or maps));self.window.geometry('760x650');self.window.minsize(560,410)
        modal(self.window)
        self.window.protocol('WM_DELETE_WINDOW',self.close);self.window.bind('<Escape>',lambda _:self.close())
        self.window.bind('<Destroy>',self.destroyed,add='+')
        self.status=tk.StringVar();self.selected=None;self.keys=[];self.columns=12;self.cell=54
        header=ttk.Frame(self.window,padding=10);header.pack(fill='x')
        ttk.Label(header,text='Choose a map tile',style='Heading.TLabel').pack(anchor='w')
        initial=self.memory.get('collection') or (form.values['sheet'].get() if form else ('Project tiles' if selected else 'All tiles'))
        if initial not in ('Project tiles','All tiles') and initial not in maps.graphics:initial='All tiles'
        self.sheet=tk.StringVar(value=initial)
        self.active_sheet=initial
        self.animated_only=tk.BooleanVar(value=self.memory.get('animated_only') is True)
        self.active_filter=self.animated_only.get()
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
        ttk.Checkbutton(source_bar,text='Animated only',variable=self.animated_only,command=self.refresh).pack(side='left',padx=8)
        ttk.Checkbutton(source_bar,text='Animate tiles',variable=maps.tile_animation.enabled,command=maps.tile_animation.refresh).pack(side='left',padx=8)
        search_bar=ttk.Frame(header);search_bar.pack(fill='x',pady=(6,0))
        ttk.Label(search_bar,text='Search names / tags / terrain').pack(side='left')
        self.query=tk.StringVar();search_entry=ttk.Entry(search_bar,textvariable=self.query);search_entry.pack(side='left',fill='x',expand=True,padx=8)
        search_entry.bind('<Return>',lambda _:guard(self,self.refresh))
        ttk.Button(search_bar,text='Search',command=lambda:guard(self,self.refresh)).pack(side='left')
        bar=ttk.Frame(self.window,padding=(8,0));bar.pack(fill='x')
        for label,callback in [('Add tile',self.new),('Clone',self.clone),('Edit pixels',self.edit),('Properties',self.properties),('Remove',self.remove)]:
            ttk.Button(bar,text=label,width=0,command=lambda f=callback:guard(self,f)).pack(side='left',padx=3)
        more=ttk.Menubutton(bar,text='More');menu=tk.Menu(more,tearoff=False);more.configure(menu=menu);more.pack(side='left',padx=3)
        menu.add_command(label='Clone ALL tiles in this view to project tiles',command=lambda:guard(self,self.clone_all))
        menu.add_command(label='Restore hidden source graphics',command=lambda:guard(self,self.unhide))
        menu.add_separator();menu.add_command(label='Save tile to shared library...',command=lambda:guard(self,self.save_library))
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
        source=next((t for t in self.document.adventure['tiles'] if t['id']==selected),None)
        if form:
            graphic=form.values['graphic'].get();bank=form.values['sheet'].get()
            if bank!='package:art':
                try:graphic=int(graphic)
                except ValueError:graphic=None
            source=dict(sheet=bank,graphic=graphic)
        remembered=self.view_memory(initial)
        self.selected=self.remembered_key(remembered) if remembered else self.key_for(source)
        self.refresh();self.restore_position(remembered)
        self.revision=self.document.revision;self.timer=self.window.after(250,self.poll)

    def show_error(self,error):self.status.set(str(error));self.window.lift()
    def destroyed(self,event):
        if event.widget is self.window:
            if self.timer:self.window.after_cancel(self.timer);self.timer=None
            if self.position_job:self.window.after_cancel(self.position_job);self.position_job=None
    def close(self):
        if self.window.winfo_exists():
            self.remember_view()
            try:
                self.memory_path.parent.mkdir(parents=True,exist_ok=True)
                ProjectDocument.atomic_file(self.memory_path,encoded(self.memory))
            except OSError as error:self.owner.status.set('Could not remember tile chooser position: '+str(error))
            self.window.destroy()
    def poll(self):
        self.timer=None
        if self.document.revision!=self.revision:self.revision=self.document.revision;self.refresh()
        self.timer=self.window.after(250,self.poll)
    def show_collection(self,name):
        if name=='All tiles' and self.active_sheet!='Project tiles':return
        self.sheet.set(self.memory.get('all_sheet','All tiles') if name=='All tiles' else name)
        if self.sheet.get() not in ('Project tiles','All tiles') and self.sheet.get() not in self.owner.graphics:self.sheet.set('All tiles')
        self.refresh()
    def view_memory(self,sheet):
        value=self.memory['views'].get(sheet+('|animated' if self.active_filter else ''))
        return value if isinstance(value,dict) else {}
    def remembered_key(self,state):
        value=state.get('selected')
        return tuple(value) if self.active_sheet=='All tiles' and isinstance(value,list) else value
    def key_for(self,source):
        if not source:return None
        if self.active_sheet=='Project tiles':return source.get('id') or next((t['id'] for t in self.document.adventure['tiles'] if t['sheet']==source['sheet'] and t['graphic']==source['graphic']),None)
        if self.active_sheet=='All tiles':return source['sheet'],source['graphic']
        return source['graphic'] if source['sheet']==self.active_sheet else None
    def remember_view(self):
        self.memory['collection']=self.active_sheet
        self.memory['animated_only']=self.active_filter
        if self.active_sheet!='Project tiles':self.memory['all_sheet']=self.active_sheet
        self.memory['views'][self.active_sheet+('|animated' if self.active_filter else '')]=dict(selected=self.selected,x=self.canvas.xview()[0],y=self.canvas.yview()[0])
    def restore_position(self,state):
        # Wait for the actual viewport size; restoring before Tk lays it out
        # would clamp the saved offset against a one-pixel canvas.
        def restore():
            self.position_job=None
            if not self.window.winfo_exists():return
            if state:
                for axis in ('x','y'):
                    value=state.get(axis,0)
                    getattr(self.canvas,axis+'view_moveto')(max(0,min(1,value)) if isinstance(value,(int,float)) else 0)
            else:
                row=self.keys.index(self.selected)//self.columns if self.selected is not None else 0
                self.canvas.yview_moveto(row/max(1,(len(self.keys)+self.columns-1)//self.columns))
        if self.position_job:self.window.after_cancel(self.position_job)
        self.position_job=self.window.after_idle(restore)
    def value(self,key):
        if self.active_sheet=='Project tiles':return tile(self.document,key)
        bank,graphic=key if self.active_sheet=='All tiles' else (self.active_sheet,key)
        return dict(sheet=bank,graphic=graphic)
    def refresh(self,selected=None):
        self.owner.refresh();self.choices.configure(values=['All tiles',*self.owner.graphics])
        changed=self.active_sheet!=self.sheet.get() or self.active_filter!=self.animated_only.get();remembered=None
        if changed:
            previous=self.source() if self.selected in self.keys else None
            self.remember_view();self.active_sheet=self.sheet.get();self.active_filter=self.animated_only.get()
            if self.active_sheet!='Project tiles':self.memory['all_sheet']=self.active_sheet
            remembered=self.view_memory(self.active_sheet)
            self.selected=self.remembered_key(remembered) if remembered else self.key_for(previous)
        if selected is not None:self.selected=selected;remembered=None
        self.canvas.delete('all');sheet=self.sheet.get();data=metadata(self.document)
        self.mode.set('Project tiles' if sheet=='Project tiles' else 'All tiles')
        self.choices.configure(state='disabled' if sheet=='Project tiles' else 'readonly')
        hidden=data.get('hidden_tile_graphics',[])
        if sheet=='Project tiles':self.keys=[t['id'] for t in self.document.adventure['tiles']]
        elif sheet=='All tiles':self.keys=[(bank,key) for bank,key in sheet_graphics(self.owner.graphics) if [bank,str(key)] not in hidden]
        else:
            source=self.owner.graphics.get(sheet,{})
            self.keys=[k for k in (source if isinstance(source,dict) else range(len(source))) if [sheet,str(k)] not in hidden]
        if self.active_filter:
            self.keys=[key for key in self.keys if tile_loop(self.owner.graphics,self.value(key)['sheet'],self.value(key)['graphic'])]
        if self.query.get():
            from asset_catalogue import catalogue,matches,parse_query
            query=parse_query(self.query.get())
            records=catalogue(self.document,'project' if sheet=='Project tiles' else 'atlas',decoded=self.owner.graphics)
            matches_by_id={r['id'] for r in records if matches(r,query)}
            matches_by_source={(r.get('sheet'),r.get('graphic')) for r in records if matches(r,query)}
            self.keys=[k for k in self.keys if (k in matches_by_id if sheet=='Project tiles' else
                (self.value(k)['sheet'],self.value(k)['graphic']) in matches_by_source)]
        names=data.get('tile_names',{})
        for index,key in enumerate(self.keys):
            value=self.value(key)
            x,y=index%self.columns*self.cell,index//self.columns*self.cell
            image=self.owner.tile_image(value['sheet'],value['graphic'],32)
            if image:self.canvas.create_image(x+27,y+20,image=image)
            if tile_loop(self.owner.graphics,value['sheet'],value['graphic']):
                self.canvas.create_rectangle(x+36,y+1,x+53,y+14,fill='#286c80',outline='')
                self.canvas.create_text(x+44,y+7,text='A',fill='white',font='TkSmallCaptionFont',tags='animated-badge')
            label=(value['sheet'].split(':')[-1][:4]+' '+str(value['graphic']).split(':')[-1]) if sheet=='All tiles' else names.get(key,key.split(':')[-1] if isinstance(key,str) else str(key))
            self.canvas.create_text(x+27,y+45,text=label[:8],fill='#31434b',font='TkSmallCaptionFont')
        self.canvas.configure(scrollregion=(0,0,self.columns*self.cell,((len(self.keys)+self.columns-1)//self.columns)*self.cell))
        self.select(self.selected if self.selected in self.keys else (self.keys[0] if self.keys else None))
        if changed or selected is not None:self.restore_position(remembered)
    def select(self,key):
        self.selected=key;self.canvas.delete('selection')
        if key is None:
            self.status.set('No animated tiles here. Choose All tiles or turn off Animated only.' if self.active_filter else 'No tiles here. Add a tile or restore hidden source graphics.');return
        index=self.keys.index(key);x,y=index%self.columns*self.cell,index//self.columns*self.cell
        self.canvas.create_rectangle(x+1,y+1,x+self.cell-1,y+self.cell-1,outline='#286c80',width=3,tags='selection')
        value=self.value(key)
        registered='id' in value or any(t['sheet']==value['sheet'] and t['graphic']==value['graphic'] for t in self.document.adventure['tiles'])
        action='Uses an existing project tile.' if registered else 'Automatically adds this graphic to project tiles when chosen.'
        self.status.set(f"{value['sheet']} | {value['graphic']} | {loop_label(self.owner.graphics,value['sheet'],value['graphic'])} | {action} Double-click to use.")
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
        value=create_tile(self.document,name='New map tile');self.animated_only.set(False);self.sheet.set('Project tiles');self.refresh(selected=value);self.edit()
    def clone(self):
        value=create_tile(self.document,self.owner.graphics,self.source(),'Map tile copy')
        self.sheet.set('Project tiles');self.refresh(selected=value)
    def clone_all(self):
        values=clone_sheet(self.document,self.owner.graphics,self.sheet.get(),[self.value(key) for key in self.keys])
        self.sheet.set('Project tiles');self.refresh(selected=values[0]);self.status.set(f'Cloned {len(values)} editable tiles into project tiles. Undo removes this whole batch.')
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
    def save_library(self):
        # Export an atlas tile through a detached copy: sharing a reference
        # need not add anything to the game's paint palette or Undo history.
        source=copy.deepcopy(self.source());self.close()
        return self.owner.construction_library().export_tile_dialog(source)
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
        for label,callback in [('Use tile',self.use),('Add new tile',self.new),('Clone tile',self.clone),('Edit pixels',self.edit),('Tile properties',self.properties),('Save tile to shared library...',self.save_library),('Remove',self.remove)]:menu.add_command(label=label,command=lambda f=callback:guard(self,f))
        from editor_ui import popup_menu
        popup_menu(menu,event)
