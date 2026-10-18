"""Searchable named references; stable IDs remain the stored values."""
import tkinter as tk
from tkinter import ttk
from editor_session import scope_of,visible_parent,guard


def reference_names(owner):
    scope=scope_of(owner)
    if not scope or not scope.document:return {}
    doc=scope.document;result={}
    for source in (doc.content,doc.adventure or {},doc.art):
        for values in source.values():
            if isinstance(values,list):
                for value in values:
                    if isinstance(value,dict) and 'id' in value:
                        result[value['id']]=value.get('name',value.get('title',value['id'].split(':')[-1]))
    return result


class ReferenceBox(ttk.Combobox):
    def __init__(self,parent,owner,variable,values,**kwargs):
        self.stored=variable;self.names=reference_names(owner);self.display=tk.StringVar();self.syncing=False
        self.ids=[];self.labels=[]
        super().__init__(parent,textvariable=self.display,state='readonly',**kwargs)
        self.configure(values=values)
        self.display.trace_add('write',self.chosen);self.stored.trace_add('write',self.updated);self.updated()
    def configure(self,cnf=None,**kw):
        if 'values' in kw:
            self.ids=list(kw['values']);self.labels=[f'{self.names[v]} [{v}]' if v in self.names else str(v) for v in self.ids]
            kw['values']=self.labels
        return super().configure(cnf,**kw)
    config=configure
    def updated(self,*_):
        if self.syncing or not self.winfo_exists():return
        self.syncing=True
        try:self.display.set(self.labels[self.ids.index(self.stored.get())] if self.stored.get() in self.ids else self.stored.get())
        finally:self.syncing=False
    def chosen(self,*_):
        if self.syncing:return
        if self.display.get() in self.labels:self.stored.set(self.ids[self.labels.index(self.display.get())])
        elif self.display.get() in self.ids:self.stored.set(self.display.get())


def pick_reference(owner,values,variable,title='Choose an asset'):
    window=tk.Toplevel(owner.window);window.title(title);window.transient(visible_parent(owner));window.geometry('650x470')
    previous=window.grab_current();names=reference_names(owner)
    search=tk.StringVar();entry=ttk.Entry(window,textvariable=search);entry.pack(fill='x',padx=12,pady=12)
    body=ttk.Panedwindow(window,orient='horizontal');body.pack(fill='both',expand=True,padx=12)
    left=ttk.Frame(body);right=ttk.Frame(body);body.add(left,weight=3);body.add(right,weight=2)
    listing=ttk.Treeview(left,show='tree',selectmode='browse');listing.pack(side='left',fill='both',expand=True)
    scroll=ttk.Scrollbar(left,command=listing.yview);scroll.pack(side='right',fill='y');listing.configure(yscrollcommand=scroll.set)
    canvas=tk.Canvas(right,width=180,height=190,highlightthickness=0,background='#e2e6e9');canvas.pack(fill='x')
    detail=tk.StringVar();ttk.Label(right,textvariable=detail,wraplength=190,padding=8).pack(fill='x')
    scope=scope_of(owner);images={i['id']:i for i in scope.document.art['images']} if scope and scope.document else {}
    if scope and scope.document:
        presentations={p['id']:p.get('image') for p in scope.document.content.get('presentations',[])}
        for unit in scope.document.content.get('mechs',[]):
            source=images.get(presentations.get(unit.get('presentation')))
            if source:images[unit['id']]=source
    from types import SimpleNamespace
    picker=SimpleNamespace(window=window,owner=owner,show_error=lambda error:detail.set(str(error)))
    photos={};timer=None;phase=0
    def show(*_):
        nonlocal phase,timer
        if timer is not None:window.after_cancel(timer);timer=None
        phase=0;canvas.delete('all');selected=listing.selection()
        if not selected:return
        identity=selected[0];detail.set(names.get(identity,identity)+'\n\n'+identity)
        image=images.get(identity)
        if image:
            from graphics_editor import photo
            zoom=max(1,min(5,160//max(image['width'],image['height'])))
            frames=[photo(window,image,i,zoom) for i in range(min(len(image['frames']),32))]
            photos['preview']=frames
            def animate():
                nonlocal phase,timer
                if not window.winfo_exists():return
                canvas.delete('all');canvas.create_image(90,85,image=frames[phase%len(frames)]);phase+=1
                if len(frames)>1:timer=window.after(140,animate)
            animate()
    def refresh(*_):
        listing.delete(*listing.get_children());query=search.get().casefold()
        for value in values:
            if not query or query in (names.get(value,'')+' '+str(value)).casefold():
                picture=images.get(value);thumbnail=None
                if picture:
                    if value not in photos:
                        from graphics_editor import photo
                        raw=photo(window,picture);factor=max(1,(max(picture['width'],picture['height'])+23)//24)
                        photos[value]=raw.subsample(factor)
                    thumbnail=photos[value]
                listing.insert('','end',iid=str(value),text=names.get(value,str(value)),image=thumbnail or '')
        if listing.exists(variable.get()):listing.selection_set(variable.get())
        elif listing.get_children():listing.selection_set(listing.get_children()[0])
    def close():
        if timer is not None:window.after_cancel(timer)
        window.destroy()
        if previous is not None and previous.winfo_exists():previous.grab_set()
    def accept(*_):
        if listing.selection():variable.set(listing.selection()[0]);close()
    search.trace_add('write',refresh);listing.bind('<<TreeviewSelect>>',lambda _:guard(picker,show))
    listing.bind('<Double-1>',accept);listing.bind('<Return>',accept)
    buttons=ttk.Frame(window,padding=12);buttons.pack(side='bottom',fill='x',before=body)
    ttk.Button(buttons,text='Cancel',command=close).pack(side='right')
    ttk.Button(buttons,text='Choose',command=accept).pack(side='right',padx=8)
    window.protocol('WM_DELETE_WINDOW',close);window.bind('<Escape>',lambda _:close());refresh();window.grab_set();entry.focus_set()
    return window


def named_choice(owner,title,message,choices):
    """Use action names instead of asking users to decode Yes/No meanings."""
    window=tk.Toplevel(owner.window);window.title(title);window.transient(visible_parent(owner))
    previous=window.grab_current();result=[]
    ttk.Label(window,text=message,wraplength=470,padding=18).pack(fill='x')
    actions=ttk.Frame(window,padding=12);actions.pack(fill='x')
    def finish(value=None):
        result.append(value);window.destroy()
        if previous is not None and previous.winfo_exists():previous.grab_set()
    for label in choices:ttk.Button(actions,text=label,command=lambda choice=label:finish(choice)).pack(side='left',padx=4)
    ttk.Button(actions,text='Cancel',command=finish).pack(side='right',padx=4)
    window.protocol('WM_DELETE_WINDOW',finish);window.bind('<Escape>',lambda _:finish());window.grab_set();window.wait_window()
    return result[0] if result else None
