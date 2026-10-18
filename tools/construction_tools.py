"""Draw and reshape persistent building footprints directly on the map."""
import copy
import tkinter as tk
from tkinter import ttk
from editor_model import EditorError
from tile_editing import metadata
from construction_editing import prepare_road,default_pixels
from map_construction import objects,new_object,overlay_index,paint_footprint,projection,in_bounds,commit


class MapConstructionTools:
    kinds=('Building','Wall','Road')

    def __init__(self,maps,parent):
        self.maps=maps;self.selected={};self.profiles=[];self.active_id=None;self.object_id=None
        self.stroke=self.before=None;self.start=self.last=None;self.erasing=False;self.preview_images={};self.map_id=None;self.last_kind=None
        self.kind=tk.StringVar(value='Building')
        self.frame=ttk.Frame(parent,padding=(6,0,6,6));self.frame.pack(fill='x')
        ttk.Label(self.frame,text='Construct',style='Section.TLabel').pack(side='left',padx=(4,8))
        self.kind_choice=ttk.Combobox(self.frame,textvariable=self.kind,values=self.kinds,state='readonly',width=9)
        self.kind_choice.pack(side='left',padx=3)
        self.kind_choice.bind('<<ComboboxSelected>>',lambda _:maps.guard(self.change_kind))
        self.choice=ttk.Combobox(self.frame,state='readonly',width=20);self.choice.pack(side='left',padx=3)
        self.choice.bind('<<ComboboxSelected>>',lambda _:maps.guard(self.change_design))
        self.place_button=ttk.Button(self.frame,text='Draw building',command=lambda:maps.guard(self.use))
        self.place_button.pack(side='left',padx=3)
        self.edit_button=ttk.Button(self.frame,text='Edit design...',command=lambda:maps.guard(self.edit))
        self.edit_button.pack(side='left',padx=3)
        from editor_ui import flow_toolbar,tooltip
        flow_toolbar(self.frame)
        tooltip(self.choice,'Saved tile styles. The footprint is drawn on the map; the designer demonstrates its corners and faces.')
        tooltip(self.place_button,'Draw a footprint on the map. Add strokes to reshape it; right-drag erases a courtyard. New starts another object.')
        self.detail=ttk.Frame(parent,padding=(6,0,6,6));self.detail.pack(fill='x')
        self.shape=tk.StringVar(value='Rectangle');self.stories=tk.StringVar(value='1');self.width=tk.StringVar(value='1')
        for label,variable,values,width in [('Shape',self.shape,('Brush','Line','Rectangle','Courtyard','Erase'),10),('Stories',self.stories,tuple(range(1,33)),3),('Width',self.width,tuple(range(1,9)),3)]:
            ttk.Label(self.detail,text=label).pack(side='left',padx=(4,3))
            widget=ttk.Combobox(self.detail,textvariable=variable,values=values,state='readonly',width=width);widget.pack(side='left',padx=(0,6))
            if label=='Stories':self.height_choice=widget
        self.object_choice=ttk.Combobox(self.detail,state='readonly',width=16);self.object_choice.pack(side='left',padx=3)
        self.object_choice.bind('<<ComboboxSelected>>',lambda _:maps.guard(self.select_object))
        self.new_button=ttk.Button(self.detail,text='New building',command=lambda:maps.guard(self.new));self.new_button.pack(side='left',padx=3)
        flow_toolbar(self.detail)
        tooltip(self.object_choice,'Return to a saved footprint to extend it, erase cells or paint a different height.')

    def profile(self):
        return next((p for p in self.profiles if p['id']==self.selected.get(self.kind.get())),None)

    def refresh(self):
        designs=metadata(self.maps.document).get('construction_sets',[])
        kind=self.kind.get();self.profiles=[p for p in designs if p['kind']==kind]
        self.choice.configure(values=[p['name'] for p in self.profiles])
        if self.profiles:
            current=self.profile() or self.profiles[0];self.selected[kind]=current['id']
            self.choice.current(self.profiles.index(current));self.choice.state(['!disabled'])
        else:self.choice.set('No saved designs');self.choice.state(['disabled'])
        self.place_button.configure(text='Draw roads' if kind=='Road' else 'Draw '+kind.lower(),state='normal' if self.profiles else 'disabled')
        self.edit_button.configure(text='Edit style...' if self.profiles else 'Create style...')
        if self.last_kind!=kind:
            self.shape.set('Rectangle' if kind=='Building' else 'Line' if kind=='Wall' else 'Brush');self.last_kind=kind;self.object_id=None
        maximum=3 if kind=='Wall' else 1 if kind=='Road' else 32
        self.height_choice.configure(values=tuple(range(1,maximum+1)),state='disabled' if kind=='Road' else 'readonly')
        if not 1<=int(self.stories.get())<=maximum:self.stories.set('1')
        map_id=self.maps.scene()['id']
        if self.map_id!=map_id:self.object_id=None;self.map_id=map_id
        self.drawn=objects(self.maps.document,map_id,kind)
        if self.object_id not in [o['id'] for o in self.drawn]:self.object_id=None
        self.object_choice.configure(values=['New '+kind.lower()]+[o['name'] for o in self.drawn],state='disabled' if kind=='Road' else 'readonly')
        self.object_choice.current(next((i+1 for i,o in enumerate(self.drawn) if o['id']==self.object_id),0))
        self.new_button.configure(text='New '+kind.lower(),state='disabled' if kind=='Road' else 'normal')

    def change_kind(self):
        self.maps.finish_stroke()
        self.refresh()
        if self.maps.tool.get() in self.kinds:
            if self.profile():self.use()
            else:self.maps.tool.set('Select');self.maps.draw_hover()

    def change_design(self):
        index=self.choice.current()
        if 0<=index<len(self.profiles):self.selected[self.kind.get()]=self.profiles[index]['id']
        if self.maps.tool.get() in self.kinds:self.use()

    def edit(self):
        current=self.profile();designer=self.maps.construction(self.kind.get())
        if current:designer.current=current['id'];designer.refresh()
        return designer

    def use(self):
        profile=self.profile()
        if not profile:raise EditorError('Create a tile style first, then choose Draw.')
        self.activate(profile)

    def choose_tool(self):
        kind=self.maps.tool.get()
        if kind not in self.kinds:self.maps.draw_hover();return
        self.kind.set(kind);self.refresh()
        if self.profile():self.use()
        else:self.maps.tool.set('Select');self.edit()

    def activate(self,profile):
        maps=self.maps;maps.finish_stroke();kind=profile['kind']
        self.kind.set(kind);self.selected[kind]=profile['id'];self.active_id=profile['id']
        if kind=='Road':
            profile=prepare_road(maps.document,profile)
            maps.road_profile=profile['id'];maps.road_width=int(self.width.get())
        maps.tool.set(kind);maps.refresh();maps.window.lift();maps.tabs.select(maps.map_tab);maps.canvas.focus_set()
        maps.status.set(profile['name']+(': drag connected roads; right-drag erases. Choose Shape and Width. Escape cancels.' if kind=='Road' else ': drag to draw; right-drag erases. Choose Shape and Stories; New starts another footprint. Escape cancels.'))
        self.refresh();maps.draw()

    def current_object(self):
        return next((o for o in objects(self.maps.document,self.maps.scene()['id']) if o['id']==self.object_id),None)

    def new(self):
        self.maps.finish_stroke();self.object_id=None
        if self.profile():self.activate(self.profile())

    def select_object(self):
        index=self.object_choice.current()-1;self.maps.finish_stroke()
        if index<0:self.new();return
        record=self.drawn[index];overlay_index(self.maps.scene(),record)
        self.object_id=record['id'];self.selected[self.kind.get()]=record['style'];self.stories.set(str(max(h for _,_,h in record['cells'])))
        self.refresh();self.use()

    def pointer(self,point,first,erase=False):
        if first:
            style=self.profile()
            if not style:raise EditorError('Choose a construction tile style first.')
            current=self.current_object()
            if current:overlay_index(self.maps.scene(),current)
            self.before=copy.deepcopy(current or new_object(self.maps.document,self.maps.scene_index,style,int(self.stories.get())))
            self.stroke=copy.deepcopy(self.before);self.stroke['style']=style['id']
            self.start=self.last=point;self.erasing=erase
        if self.stroke is None:return
        shape=self.shape.get()
        if shape in ('Line','Rectangle','Courtyard'):
            style=self.stroke['style'];self.stroke=copy.deepcopy(self.before);self.stroke['style']=style;start=self.start
        else:start=self.last
        paint_footprint(self.stroke,start,point,shape,int(self.stories.get()),int(self.width.get()),self.erasing)
        self.last=point;self.maps.draw()
        self.maps.status.set(f"{self.kind.get()} footprint: {len(self.stroke['cells'])} cells; release to build. Right-drag erases; New starts another.")

    def finish(self):
        if self.stroke is None:return
        self.object_id=commit(self.maps.document,self.maps.scene_index,self.stroke)
        self.stroke=self.before=None;self.maps.refresh()

    def cancel(self):self.stroke=self.before=None;self.maps.draw();self.maps.status.set('Footprint stroke cancelled.')

    def capture(self):
        return dict(stroke=copy.deepcopy(self.stroke),before=copy.deepcopy(self.before),start=self.start,last=self.last,erasing=self.erasing,
            object_id=self.object_id,kind=self.kind.get(),style=self.selected.get(self.kind.get()),shape=self.shape.get(),stories=self.stories.get(),width=self.width.get())

    def restore(self,state):
        self.kind.set(state['kind']);self.refresh();self.selected[state['kind']]=state['style'];self.object_id=state['object_id']
        self.shape.set(state['shape']);self.stories.set(state['stories']);self.width.set(state['width'])
        self.stroke=state['stroke'];self.before=state['before'];self.start=state['start'];self.last=state['last'];self.erasing=state['erasing']
        self.active_id=state['style'];self.maps.tool.set(state['kind']);self.refresh();self.maps.draw()

    def preview_scene(self,scene):
        if self.stroke is None or 'rendered' not in self.before:return scene
        result=copy.deepcopy(scene);index=overlay_index(scene,self.before)
        layer=result['overlays'][index];layer['rows']=[[' ']*len(r) for r in layer['rows']]
        return result

    def draw_preview(self):
        if self.maps.tool.get() not in ('Building','Wall'):return
        record=self.stroke or self.current_object()
        if not record:return
        canvas=self.maps.canvas;size=int(self.maps.zoom.get())
        try:at,roles=projection(record);valid=in_bounds(self.maps.scene(),record,at,roles)
        except EditorError:at,roles,valid=(0,0),[],False
        if self.stroke and record['cells']:
            style=self.profile();tiles={t['id']:t for t in self.maps.adventure['tiles']}
            details={(x,y):tile for x,y,tile in record.get('details',[])}
            for y,row in enumerate(roles):
                for x,role in enumerate(row):
                    if role==' ':continue
                    identity=details.get((at[0]+x,at[1]+y),style['parts'].get(role))
                    if identity==' ':continue
                    value=tiles.get(identity);im=self.maps.tile_image(value['sheet'],value['graphic'],size) if value else None
                    if im is None:
                        key=(role,record['kind'],size)
                        if key not in self.preview_images:
                            pixels=default_pixels(role,record['kind']);im=tk.PhotoImage(master=canvas,width=size,height=size)
                            im.put(' '.join('{'+ ' '.join('#'+pixels[yy*16//size][xx*16//size][:6] for xx in range(size))+'}' for yy in range(size)))
                            self.preview_images[key]=im
                        im=self.preview_images[key]
                    canvas.create_image((at[0]+x)*size,(at[1]+y)*size,image=im,anchor='nw',tags='brush-hover')
        for x,y,h in record['cells']:
            canvas.create_rectangle(x*size,y*size,(x+1)*size,(y+1)*size,outline='#72d9e8' if valid else '#ff6472',tags='brush-hover')
            if size>=24:canvas.create_text(x*size+size//2,y*size+size//2,text=str(h),fill='#14313e',tags='brush-hover')
