"""Canvas-first artwork layout for embedded pixel and sprite views."""
import tkinter as tk
from tkinter import ttk
from art_editing import DEFAULT_COLORS


class LayerList(tk.Listbox):
    def configure(self,cnf=None,**kw):
        values=kw.pop('values',None)
        if values is not None:
            self.delete(0,'end')
            for value in values:self.insert('end',value)
        return super().configure(cnf,**kw)
    config=configure
    def current(self,index=None):
        if index is None:return self.curselection()[0] if self.curselection() else 0
        self.selection_clear(0,'end');self.selection_set(index);self.see(index)


def build_pixel(editor):
    from adventure_editor import scroll_frame
    window=editor.window;workspace=window.workspace
    panel=ttk.Frame(workspace.inspector);workspace.custom_inspectors[window.key]=panel
    shell,editor.inspector_host=scroll_frame(panel,width=220,height=560);shell.pack(fill='both',expand=True)
    side=editor.inspector_host
    ttk.Label(side,text='Artwork',font='TkHeadingFont').pack(anchor='w',pady=6)
    editor.color=tk.StringVar(value='ffffffff')
    color_row=ttk.Frame(side);color_row.pack(fill='x')
    ttk.Entry(color_row,textvariable=editor.color,width=10).pack(side='left')
    ttk.Button(color_row,text='Color...',width=0,command=editor.choose_color).pack(side='left',padx=5)
    swatches=tk.Canvas(side,width=192,height=48,highlightthickness=0);swatches.pack(anchor='w',pady=8)
    for i,color in enumerate(DEFAULT_COLORS):
        x=(i%8)*24;y=(i//8)*24;swatches.create_rectangle(x,y,x+23,y+23,fill='#'+color,outline='#777777')
    swatches.bind('<Button-1>',lambda e:editor.color.set(DEFAULT_COLORS[max(0,min(15,e.x//24+(e.y//24)*8))]+'ff'))
    ttk.Label(side,text='Layers',font='TkHeadingFont').pack(anchor='w',pady=(6,4))
    editor.layer=LayerList(side,height=5,width=22,exportselection=False);editor.layer.pack(fill='x')
    editor.layer.bind('<<ListboxSelect>>',lambda _:editor.change_layer())
    layer_actions=ttk.Frame(side);layer_actions.pack(fill='x',pady=4)
    actions=[('New',editor.new_layer),('Rename',editor.rename_layer),('Show / hide',editor.toggle_layer),('Up',lambda:editor.reorder_layer(1)),('Down',lambda:editor.reorder_layer(-1)),('Delete',editor.delete_layer)]
    for i,(label,method) in enumerate(actions):
        ttk.Button(layer_actions,text=label,width=0,command=lambda f=method:editor.guard(f)).grid(row=i//2,column=i%2,sticky='ew',padx=1,pady=1)
    editor.all_frames=tk.BooleanVar(value=False);editor.wrap=tk.BooleanVar(value=False);editor.grid=tk.BooleanVar(value=True)
    for label,variable in [('Transform all frames',editor.all_frames),('Wrap nudged pixels',editor.wrap),('Pixel grid',editor.grid)]:ttk.Checkbutton(side,text=label,variable=variable,command=editor.draw).pack(anchor='w')
    tools=ttk.Frame(window,padding=(6,5));tools.pack(fill='x')
    editor.tool=tk.StringVar(value='Pencil')
    ttk.Combobox(tools,textvariable=editor.tool,values=('Pencil','Line','Rectangle','Fill','Erase','Eyedropper','Select','Paste selection'),state='readonly',width=15).pack(side='left')
    editor.zoom=tk.StringVar(value=str(min(16,max(2,512//max(editor.image['width'],editor.image['height'])))))
    ttk.Label(tools,text=' Zoom').pack(side='left')
    zoom=ttk.Combobox(tools,textvariable=editor.zoom,values=('1','2','4','8','16','24','32'),width=4,state='readonly');zoom.pack(side='left',padx=4);zoom.bind('<<ComboboxSelected>>',lambda _:editor.draw())
    transforms=ttk.Menubutton(tools,text='Transform');menu=tk.Menu(transforms,tearoff=False)
    for title in ('Flip X','Flip Y','Rotate right','Rotate left','Nudge left','Nudge right','Nudge up','Nudge down','Clear'):
        menu.add_command(label=title,command=lambda op=title:editor.guard(lambda:editor.transform(op)))
    transforms.configure(menu=menu);transforms.pack(side='left',padx=4)
    selection=ttk.Menubutton(tools,text='Selection / canvas');menu=tk.Menu(selection,tearoff=False)
    for title,method in [('Copy selection',editor.copy_pixels),('Cut selection',lambda:editor.copy_pixels(True)),('Crop to selection',editor.crop),('Resize canvas',editor.resize_dialog),('Export PNG sheet',editor.export_dialog)]:menu.add_command(label=title,command=lambda f=method:editor.guard(f))
    selection.configure(menu=menu);selection.pack(side='left',padx=4)
    split=ttk.Panedwindow(window,orient='vertical');split.pack(fill='both',expand=True)
    view=ttk.Frame(split);view.columnconfigure(0,weight=1);view.rowconfigure(0,weight=1);split.add(view,weight=5)
    editor.frame_host=ttk.Frame(split);split.add(editor.frame_host,weight=1)
    editor.canvas=tk.Canvas(view,highlightthickness=0,background='#d8dcdf')
    sx=ttk.Scrollbar(view,orient='horizontal',command=editor.canvas.xview);sy=ttk.Scrollbar(view,command=editor.canvas.yview)
    editor.canvas.configure(xscrollcommand=sx.set,yscrollcommand=sy.set);editor.canvas.grid(row=0,column=0,sticky='nsew');sx.grid(row=1,column=0,sticky='ew');sy.grid(row=0,column=1,sticky='ns')
    editor.build_frames()
    # Reserve the full frame controls; a canvas may scroll, but the timeline's
    # Next/Copy/Paste controls must not fall beneath its pane by default.
    window.after_idle(lambda:split.sashpos(0,max(120,split.winfo_height()-editor.frame_host.winfo_reqheight())))
    workspace.update_inspector()


def build_sprite(editor):
    from sprite_editing import DIRECTIONS,VIEWS,default_view
    from action_tracks import edit_track
    panel=ttk.Frame(editor.frame_host,padding=5);panel.pack(fill='both',expand=True)
    top=ttk.Frame(panel);top.pack(fill='x')
    editor.view=tk.StringVar(value=default_view(editor.owner.document,editor.image))
    chooser=ttk.Combobox(top,textvariable=editor.view,values=VIEWS,state='readonly',width=17);chooser.pack(side='left');chooser.bind('<<ComboboxSelected>>',lambda _:editor.change_view())
    editor.direction_choice=ttk.Combobox(top,values=DIRECTIONS,state='readonly',width=13);editor.direction_choice.current(editor.direction);editor.direction_choice.pack(side='left',padx=6)
    editor.direction_choice.bind('<<ComboboxSelected>>',lambda _:editor.face(editor.direction_choice.current()))
    editor.directions={};editor.description=tk.StringVar();editor.note=tk.StringVar()
    ttk.Label(top,textvariable=editor.description,wraplength=310).pack(side='left',padx=4)
    editor.strip=tk.Canvas(panel,height=106,background='#e5e8ec',highlightthickness=0);editor.strip.pack(fill='x',pady=(4,0))
    scroll=ttk.Scrollbar(panel,orient='horizontal',command=editor.strip.xview);scroll.pack(fill='x');editor.strip.configure(xscrollcommand=scroll.set);editor.strip.bind('<Button-1>',editor.pick_thumbnail)
    controls=ttk.Frame(panel);controls.pack(fill='x',pady=(4,0))
    editor.previous=ttk.Button(controls,text='Previous',width=0,command=lambda:editor.step(-1));editor.previous.pack(side='left')
    editor.next=ttk.Button(controls,text='Next',width=0,command=lambda:editor.step(1));editor.next.pack(side='left',padx=3)
    ttk.Button(controls,text='Copy',width=0,command=editor.copy_frame).pack(side='left')
    editor.paste_button=ttk.Button(controls,text='Paste',width=0,command=lambda:editor.guard(editor.paste),state='disabled');editor.paste_button.pack(side='left',padx=3)
    ttk.Button(controls,text='Clone',width=0,command=lambda:editor.guard(editor.clone_pose)).pack(side='left')
    editor.onion=tk.BooleanVar(value=False);ttk.Checkbutton(controls,text='Onion skin',variable=editor.onion,command=editor.draw).pack(side='left',padx=6)
    editor.frame=ttk.Combobox(panel,state='readonly')
    side=editor.inspector_host
    ttk.Button(side,text='Edit animation action...',command=lambda:editor.guard(lambda:edit_track(editor))).pack(fill='x',pady=8)
    editor.animation=tk.Canvas(side,width=180,height=96,background='#d6d6d6',highlightthickness=0);editor.animation.pack(fill='x')
    editor.play_button=ttk.Button(side,text='Play preview',command=editor.play);editor.play_button.pack(fill='x',pady=4)
    row=ttk.Frame(side);row.pack(fill='x');editor.fps=tk.StringVar(value='8')
    ttk.Combobox(row,textvariable=editor.fps,values=('4','6','8','12'),state='readonly',width=4).pack(side='left');ttk.Label(row,text='fps preview').pack(side='left',padx=6)
    ttk.Label(side,textvariable=editor.note,wraplength=215,style='Muted.TLabel').pack(fill='x',pady=8)
