"""Map painting and event forms sharing the roster editor's document/history."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

from editor_model import EditorError
from adventure_editing import OPS, composite, paint, event_template, new_id, copy_adventure


def scroll_frame(parent, width=660, height=590):
    shell=ttk.Frame(parent)
    canvas=tk.Canvas(shell,highlightthickness=0,width=width,height=height)
    bar=ttk.Scrollbar(shell,orient="vertical",command=canvas.yview)
    canvas.configure(yscrollcommand=bar.set)
    bar.pack(side="right",fill="y");canvas.pack(side="left",fill="both",expand=True)
    body=ttk.Frame(canvas,padding=8);item=canvas.create_window(0,0,window=body,anchor="nw")
    body.bind("<Configure>",lambda _:canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>",lambda e:canvas.itemconfigure(item,width=e.width))
    return shell,body


class Form:
    def __init__(self, owner, title):
        self.owner = owner
        self.window = tk.Toplevel(owner.window)
        self.window.title(title)
        self.window.transient(owner.window)
        self.window.columnconfigure(1, weight=1)
        shell,self.body=scroll_frame(self.window)
        shell.pack(fill="both",expand=True)
        self.body.columnconfigure(1,weight=1)
        self.window.minsize(580,250)
        self.window.geometry("700x650")
        self.values = {}
        self.row = 0
        self.window.bind("<Escape>", lambda _: self.window.destroy())

    def field(self, key, value, choices=None, label=None):
        ttk.Label(self.body, text=label or key.replace("_", " ").title()).grid(row=self.row, column=0, sticky="w", padx=10, pady=4)
        var = tk.StringVar(value=str(value))
        widget = ttk.Combobox(self.body, textvariable=var, values=choices, state="readonly", width=48) if choices is not None else ttk.Entry(self.body, textvariable=var, width=50)
        widget.grid(row=self.row, column=1, sticky="ew", padx=10, pady=4)
        self.values[key] = var
        self.row += 1
        return widget

    def submit(self, callback):
        def apply():
            callback({k: v.get() for k, v in self.values.items()})
            self.window.destroy()
        # Keep Apply reachable while scrolling through a long party form.
        ttk.Button(self.window, text="Apply", command=lambda: self.owner.guard(apply)).pack(side="bottom",anchor="e",pady=8,padx=12)


class AdventureEditor:
    def __init__(self, parent):
        self.parent = parent
        self.document = parent.document
        if self.document.adventure is None:
            raise EditorError("This project uses the CHI campaign. Open examples/beacon-demo or examples/adventure-demo for map/event editing.")
        self.window = tk.Toplevel(parent.window)
        self.window.transient(parent.window)
        self.window.title("BtechPort maps and events")
        self.window.geometry("1000x720")
        self.window.minsize(960, 650)
        self.scene_index = 0
        self.stroke = None
        self.cursor = tuple(self.document.adventure["start"]["at"])
        self.images = {}
        bar = ttk.Frame(self.window, padding=6);bar.pack(fill="x")
        for label, action in [("Save", self.save), ("Validate", self.validate), ("Undo", self.undo), ("Redo", self.redo), ("Play", self.play), ("Play here", self.play_here), ("Export", parent.export_project)]:
            ttk.Button(bar, text=label, command=lambda cb=action: self.guard(cb)).pack(side="left", padx=3)
        self.tabs = ttk.Notebook(self.window);self.tabs.pack(fill="both", expand=True)
        self.map_tab = ttk.Frame(self.tabs);self.tabs.add(self.map_tab, text="Maps")
        self.event_tab = ttk.Frame(self.tabs);self.tabs.add(self.event_tab, text="Events")
        self.world_tab = ttk.Frame(self.tabs);self.tabs.add(self.world_tab, text="People, shops and start")
        self.status = tk.StringVar(value="Paint with the left mouse button. Select a placement tool to add entrances, NPCs, encounters or the start.")
        ttk.Label(self.window, textvariable=self.status, padding=8, wraplength=1100).pack(fill="x")
        self.build_maps();self.build_events();self.build_world();self.refresh()
        self.window.bind("<Control-s>", lambda _: self.guard(self.save))
        self.window.bind("<Control-z>", lambda _: self.guard(self.undo))
        self.window.bind("<Control-y>", lambda _: self.guard(self.redo))
        self.window.protocol("WM_DELETE_WINDOW",lambda:self.guard(self.close))
        self.tabs.bind("<<NotebookTabChanged>>",lambda _:self.guard(self.apply_pending))

    def guard(self, action):
        try:
            return action()
        except (EditorError, OSError, ValueError, KeyError, IndexError) as exc:
            self.status.set(str(exc));messagebox.showerror("Map/event editor", str(exc), parent=self.window)

    @property
    def adventure(self): return self.document.adventure

    def commit(self, adventure):
        self.document.replace_adventure(adventure)
        self.status.set("Unsaved authoring edit. Validate checks the whole game with the C player.")
        self.refresh()

    def refresh(self):
        if not self.window.winfo_exists(): return
        self.scene_index = min(self.scene_index, len(self.adventure["maps"])-1)
        scenes = [m["name"] for m in self.adventure["maps"]]
        self.map_choice.configure(values=scenes);self.map_choice.current(self.scene_index)
        self.layer_choice.configure(values=["Base"] + [f"Overlay {i+1} at {v['at']}" for i,v in enumerate(self.scene()["overlays"])])
        if self.layer_choice.current() < 0 or self.layer_choice.current() > len(self.scene()["overlays"]): self.layer_choice.current(0)
        brush = self.brush.curselection();self.brush.delete(0,"end")
        for tile in self.adventure["tiles"]: self.brush.insert("end", f"{tile['key']}   {tile['id'].split(':')[-1]} ({tile['terrain']})")
        self.brush.insert("end", "[transparent] erase overlay")
        self.brush.selection_set(min(brush[0] if brush else 0,self.brush.size()-1))
        self.draw();self.refresh_events();self.refresh_world();self.refresh_markers()

    def scene(self): return self.adventure["maps"][self.scene_index]

    def build_maps(self):
        top = ttk.Frame(self.map_tab,padding=6);top.pack(fill="x")
        self.map_choice=ttk.Combobox(top,state="readonly",width=25);self.map_choice.pack(side="left")
        self.map_choice.bind("<<ComboboxSelected>>",lambda _:self.change_map())
        for label,action in [("New map",self.new_map),("Map properties",self.map_properties),("Delete map",self.delete_map),("Add overlay",self.new_overlay),("Layer properties",self.layer_properties),("Delete layer",self.delete_layer)]:
            ttk.Button(top,text=label,command=lambda cb=action:self.guard(cb)).pack(side="left",padx=3)
        controls=ttk.Frame(self.map_tab,padding=6);controls.pack(fill="x")
        self.layer_choice=ttk.Combobox(controls,state="readonly",width=26,values=["Base"]);self.layer_choice.current(0);self.layer_choice.pack(side="left")
        self.layer_choice.bind("<<ComboboxSelected>>",lambda _:self.draw())
        self.tool=tk.StringVar(value="Paint")
        ttk.Combobox(controls,textvariable=self.tool,values=["Paint","Entrance","NPC","Encounter","Start","Play here"],state="readonly",width=16).pack(side="left",padx=6)
        self.zoom=tk.StringVar(value="24")
        z=ttk.Combobox(controls,textvariable=self.zoom,values=["16","24","32"],state="readonly",width=4);z.pack(side="left");z.bind("<<ComboboxSelected>>",lambda _:self.draw())
        self.terrain=tk.BooleanVar(value=False);ttk.Checkbutton(controls,text="Collision / terrain",variable=self.terrain,command=self.draw).pack(side="left",padx=8)
        ttk.Button(controls,text="Edit tile definition",command=lambda:self.guard(self.edit_tile)).pack(side="left")
        ttk.Button(controls,text="Duplicate tile",command=lambda:self.guard(self.duplicate_tile)).pack(side="left",padx=4)
        body=ttk.Panedwindow(self.map_tab,orient="horizontal");body.pack(fill="both",expand=True)
        side=ttk.Frame(body,width=220);view=ttk.Frame(body);body.add(side,weight=1);body.add(view,weight=5)
        self.brush=tk.Listbox(side,exportselection=False,height=12);self.brush.pack(fill="both",expand=True,padx=5,pady=5)
        ttk.Label(side,text="Markers: double-click to edit",padding=4).pack(anchor="w")
        self.markers=tk.Listbox(side,exportselection=False,height=10);self.markers.pack(fill="both",expand=True,padx=5)
        self.markers.bind("<Double-Button-1>",lambda _:self.guard(self.edit_marker))
        ttk.Button(side,text="Delete selected marker",command=lambda:self.guard(self.delete_marker)).pack(fill="x",padx=5,pady=5)
        self.canvas=tk.Canvas(view,background="#101925",highlightthickness=0)
        sx=ttk.Scrollbar(view,orient="horizontal",command=self.canvas.xview);sy=ttk.Scrollbar(view,orient="vertical",command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=sx.set,yscrollcommand=sy.set)
        view.rowconfigure(0,weight=1);view.columnconfigure(0,weight=1)
        self.canvas.grid(row=0,column=0,sticky="nsew");sx.grid(row=1,column=0,sticky="ew");sy.grid(row=0,column=1,sticky="ns")
        self.canvas.bind("<Button-1>",lambda e:self.guard(lambda:self.pointer(e,True)))
        self.canvas.bind("<B1-Motion>",lambda e:self.guard(lambda:self.pointer(e,False)))
        self.canvas.bind("<ButtonRelease-1>",lambda _:self.guard(self.finish_stroke))

    def change_map(self):
        self.finish_stroke();self.scene_index=self.map_choice.current();self.layer_choice.current(0);self.refresh()

    def draw(self):
        scene=(self.stroke or self.adventure)["maps"][self.scene_index];grid=composite(scene);size=int(self.zoom.get())
        self.canvas.delete("all");self.canvas.configure(scrollregion=(0,0,len(grid[0])*size,len(grid)*size))
        tiles={t["key"]:t for t in self.adventure["tiles"]}
        art=None
        if "presentation" in self.document.manifest:
            art=json.loads(self.document.snapshot[self.document.manifest["presentation"]])
        terrain_colors={"clear":"#28574d","rough":"#947b64","water":"#457caa","woods":"#397557","wall":"#b45a60"}
        for y,row in enumerate(grid):
            for x,key in enumerate(row):
                tile=tiles.get(key);color=terrain_colors.get(tile["terrain"],"#f00") if tile else "#f00"
                if art and tile and tile["graphic"]<len(art["tiles"]) and not self.terrain.get():
                    cache=(tile["graphic"],size)
                    if cache not in self.images:
                        source=art["tiles"][tile["graphic"]];palette=art["palette"]
                        im=tk.PhotoImage(width=size,height=size)
                        for py in range(size):
                            im.put("{"+" ".join("#"+palette[int(source[py*16//size][px*16//size],16)] for px in range(size))+"}",to=(0,py))
                        self.images[cache]=im
                    self.canvas.create_image(x*size,y*size,image=self.images[cache],anchor="nw")
                else:
                    self.canvas.create_rectangle(x*size,y*size,(x+1)*size,(y+1)*size,fill=color,outline="#20303b")
                    if not art: self.canvas.create_text(x*size+size/2,y*size+size/2,text=key,fill="white")
        if self.layer_choice.current()>0:
            layer=scene["overlays"][self.layer_choice.current()-1];ox,oy=layer["at"]
            self.canvas.create_rectangle(ox*size,oy*size,(ox+len(layer["rows"][0]))*size,(oy+len(layer["rows"]))*size,outline="#edcc75",width=3)
        def marker(at,label,color):
            x,y=at[0]*size/2,at[1]*size/2
            self.canvas.create_oval(x-5,y-5,x+5,y+5,fill=color,outline="black")
            self.canvas.create_text(x+8,y-8,text=label,fill="white",anchor="sw",font=("TkDefaultFont",9,"bold"))
        for door in scene["entrances"]: marker(door["at"],door["name"],"#6abec0" if "person" in door else "#edcc75")
        for encounter in self.adventure["encounters"]:
            if encounter["map"]==scene["id"]:
                marker(encounter["party_at"],encounter["id"].split(":")[-1]+" / party","#a9bb70")
                for e in encounter["enemies"]: marker(e["at"],e["definition"].split(":")[-1],"#db7974")
        if self.adventure["start"]["map"]==scene["id"]: marker(self.adventure["start"]["at"],"START","#f4f1de")
        marker(self.cursor,"preview","#bf91d5")

    def pointer(self,event,first):
        size=int(self.zoom.get());px=self.canvas.canvasx(event.x);py=self.canvas.canvasy(event.y)
        x,y=int(px//size),int(py//size)
        scene=self.scene()
        if not 0<=y<len(scene["rows"]) or not 0<=x<len(scene["rows"][0]): return
        half=(int(px*2//size),int(py*2//size));self.cursor=half
        tool=self.tool.get()
        if tool=="Paint":
            if first: self.stroke=copy_adventure(self.document)
            if self.stroke is None: return
            index=self.brush.curselection()[0] if self.brush.curselection() else 0
            key=self.adventure["tiles"][index]["key"] if index<len(self.adventure["tiles"]) else " "
            paint(self.stroke["maps"][self.scene_index],max(0,self.layer_choice.current()),x,y,key);self.draw()
        elif first:
            if tool in ("Entrance","NPC"): self.entrance_dialog(at=half,npc=tool=="NPC")
            elif tool=="Encounter": self.encounter_dialog(at=half)
            elif tool=="Start":
                a=copy_adventure(self.document);a["start"].update(map=scene["id"],at=list(half));self.commit(a)
            elif tool=="Play here": self.play_here()
        self.status.set(f"Tile {x},{y} | half-tile {half[0]},{half[1]} | {tool}")

    def finish_stroke(self):
        if self.stroke is not None:
            a=self.stroke;self.stroke=None;self.commit(a)

    def new_map(self):
        form=Form(self,"New map")
        for key,value in dict(id=new_id(self.document,"maps","map"),name="New map",width=32,height=24,origin_x=160,origin_y=64).items():form.field(key,value)
        def apply(v):
            w,h=int(v["width"]),int(v["height"])
            if not 16<=w<=64 or not 16<=h<=64: raise EditorError("Map dimensions are 16..64 tiles.")
            a=copy_adventure(self.document);a["maps"].append(dict(id=v["id"],name=v["name"],origin=[int(v["origin_x"]),int(v["origin_y"])],rows=[a["tiles"][0]["key"]*w for _ in range(h)],overlays=[],entrances=[]))
            self.scene_index=len(a["maps"])-1;self.commit(a)
        form.submit(apply)

    def map_properties(self):
        m=self.scene();form=Form(self,"Map properties")
        for key,value in dict(name=m["name"],origin_x=m["origin"][0],origin_y=m["origin"][1],width=len(m["rows"][0]),height=len(m["rows"])).items():form.field(key,value)
        def apply(v):
            w,h=int(v["width"]),int(v["height"])
            if not 16<=w<=64 or not 16<=h<=64: raise EditorError("Map dimensions are 16..64 tiles.")
            a=copy_adventure(self.document);m=a["maps"][self.scene_index]
            if any(o["at"][0]+len(o["rows"][0])>w or o["at"][1]+len(o["rows"])>h for o in m["overlays"]):raise EditorError("Resize or remove overlays before shrinking across them.")
            key=a["tiles"][0]["key"];m.update(name=v["name"],origin=[int(v["origin_x"]),int(v["origin_y"])],rows=[(m["rows"][y]+key*w)[:w] if y<len(m["rows"]) else key*w for y in range(h)])
            self.commit(a)
        form.submit(apply)

    def delete_map(self):
        if len(self.adventure["maps"])==1:raise EditorError("Keep at least one map.")
        a=copy_adventure(self.document);a["maps"].pop(self.scene_index);self.commit(a)

    def duplicate_tile(self):
        selected=self.brush.curselection()
        if not selected or selected[0]>=len(self.adventure["tiles"]):return
        a=copy_adventure(self.document);tile=copy.deepcopy(a["tiles"][selected[0]])
        used={t["key"] for t in a["tiles"]};key=next((chr(c) for c in range(33,127) if chr(c) not in used),None)
        if key is None:raise EditorError("No unused tile key remains.")
        tile.update(id=new_id(self.document,"tiles","tile"),key=key);a["tiles"].append(tile);self.commit(a)
        self.brush.selection_clear(0,"end");self.brush.selection_set(len(a["tiles"])-1);self.edit_tile()

    def new_overlay(self): self.overlay_dialog()
    def layer_properties(self):
        if self.layer_choice.current()<1: return self.map_properties()
        self.overlay_dialog(self.layer_choice.current()-1)

    def overlay_dialog(self,index=None):
        old=self.scene()["overlays"][index] if index is not None else dict(at=[0,0],rows=[" "*4]*4)
        form=Form(self,"Overlay bounds")
        for key,value in dict(x=old["at"][0],y=old["at"][1],width=len(old["rows"][0]),height=len(old["rows"])).items():form.field(key,value)
        def apply(v):
            x,y,w,h=(int(v[k]) for k in ("x","y","width","height"));scene=self.scene()
            if min(x,y)<0 or min(w,h)<1 or x+w>len(scene["rows"][0]) or y+h>len(scene["rows"]): raise EditorError("Overlay must fit within the map.")
            layer=dict(at=[x,y],rows=[(old["rows"][row]+" "*w)[:w] if row<len(old["rows"]) else " "*w for row in range(h)])
            a=copy_adventure(self.document);layers=a["maps"][self.scene_index]["overlays"]
            if index is None:layers.append(layer)
            else:layers[index]=layer
            self.commit(a);self.layer_choice.current(len(layers) if index is None else index+1);self.draw()
        form.submit(apply)

    def delete_layer(self):
        index=self.layer_choice.current()-1
        if index>=0:
            a=copy_adventure(self.document);a["maps"][self.scene_index]["overlays"].pop(index);self.layer_choice.current(0);self.commit(a)

    def edit_tile(self):
        if not self.brush.curselection() or self.brush.curselection()[0]>=len(self.adventure["tiles"]):return
        index=self.brush.curselection()[0];tile=self.adventure["tiles"][index];form=Form(self,"Tile definition")
        form.field("id",tile["id"]);form.field("key",tile["key"]);form.field("graphic",tile["graphic"])
        form.field("sheet",tile["sheet"],["package:tiles"] if self.document.manifest["requires"]=="none" else ["chi:land","chi:destroyed"])
        form.field("terrain",tile["terrain"],["clear","rough","water","woods","wall"]);form.field("mini_color",tile["mini_color"])
        def apply(v):
            if len(v["key"])!=1 or v["key"]==" ":raise EditorError("A tile key is one non-space character.")
            a=copy_adventure(self.document);old=a["tiles"][index]["key"]
            if any(t["key"]==v["key"] for i,t in enumerate(a["tiles"]) if i!=index):raise EditorError("Tile key already exists.")
            for m in a["maps"]:
                for layer in [m,*m["overlays"]]:layer["rows"]=[row.replace(old,v["key"]) for row in layer["rows"]]
            v["graphic"],v["mini_color"]=int(v["graphic"]),int(v["mini_color"]);a["tiles"][index]=v;self.images.clear();self.commit(a)
        form.submit(apply)

    def refresh_markers(self):
        self.marker_ids=[];self.markers.delete(0,"end")
        for i,d in enumerate(self.scene()["entrances"]):self.marker_ids.append(("entrance",i));self.markers.insert("end",("NPC " if "person" in d else "Door ")+d["name"])
        for i,e in enumerate(self.adventure["encounters"]):
            if e["map"]==self.scene()["id"]:self.marker_ids.append(("encounter",i));self.markers.insert("end","Fight "+e["id"].split(":")[-1])

    def edit_marker(self):
        if self.markers.curselection():
            kind,index=self.marker_ids[self.markers.curselection()[0]]
            self.entrance_dialog(index) if kind=="entrance" else self.encounter_dialog(index)

    def delete_marker(self):
        if self.markers.curselection():
            kind,index=self.marker_ids[self.markers.curselection()[0]];a=copy_adventure(self.document)
            (a["maps"][self.scene_index]["entrances"] if kind=="entrance" else a["encounters"]).pop(index);self.commit(a)

    def entrance_dialog(self,index=None,at=None,npc=False):
        doors=self.scene()["entrances"]
        old=doors[index] if index is not None else dict(id=f"{self.document.manifest['package_id']}:door-{self.scene_index+1}-{len(doors)+1}",name="Talk" if npc else "New entrance",at=list(at),event=self.adventure["events"][0]["id"])
        form=Form(self,"NPC / entrance")
        for key,value in dict(id=old["id"],name=old["name"],x=old["at"][0],y=old["at"][1]).items():form.field(key,value)
        form.field("event",old["event"],[e["id"] for e in self.adventure["events"]])
        form.field("person",old.get("person",self.adventure["people"][0]["id"] if npc else "none"),["none"]+[p["id"] for p in self.adventure["people"]])
        def apply(v):
            d=dict(id=v["id"],name=v["name"],at=[int(v["x"]),int(v["y"])],event=v["event"])
            if v["person"]!="none":d["person"]=v["person"]
            a=copy_adventure(self.document);dest=a["maps"][self.scene_index]["entrances"]
            if index is None:dest.append(d)
            else:dest[index]=d
            self.commit(a)
        form.submit(apply)

    def encounter_dialog(self,index=None,at=None):
        old=copy.deepcopy(self.adventure["encounters"][index]) if index is not None else dict(id=new_id(self.document,"encounters","encounter"),map=self.scene()["id"],party_at=list(at),enemies=[])
        form=Form(self,"Encounter and enemy spawns")
        form.field("id",old["id"]);form.field("map",old["map"],[m["id"] for m in self.adventure["maps"]]);form.field("party_x",old["party_at"][0]);form.field("party_y",old["party_at"][1])
        listing=tk.Listbox(form.body,height=6,width=60,exportselection=False);listing.grid(row=form.row,column=0,columnspan=2,padx=10,sticky="ew");form.row+=1
        def refresh():
            listing.delete(0,"end")
            for enemy in old["enemies"]:listing.insert("end",f"{enemy['kind']} {enemy['definition']} at {enemy['at']}")
        def enemy_dialog(edit=False):
            selected=listing.curselection()
            if edit and not selected:return
            at_index=selected[0] if edit else None
            enemy=old["enemies"][at_index] if edit else dict(kind="mech",definition=self.document.content["mechs"][0]["id"],at=[min(120,old["party_at"][0]+8),old["party_at"][1]])
            dialog=Form(self,"Enemy placement");kind=dialog.field("kind",enemy["kind"],["mech","person"])
            def choices():return [m["id"] for m in (self.document.content["mechs"] if dialog.values["kind"].get()=="mech" else self.adventure["people"])]
            definition=dialog.field("definition",enemy["definition"],choices())
            kind.bind("<<ComboboxSelected>>",lambda _: (definition.configure(values=choices()),dialog.values["definition"].set(choices()[0])))
            dialog.field("x",enemy["at"][0]);dialog.field("y",enemy["at"][1])
            def apply(v):
                enemy=dict(kind=v["kind"],definition=v["definition"],at=[int(v["x"]),int(v["y"])])
                if at_index is None:old["enemies"].append(enemy)
                else:old["enemies"][at_index]=enemy
                refresh()
            dialog.submit(apply)
        buttons=ttk.Frame(form.body);buttons.grid(row=form.row,column=0,columnspan=2);form.row+=1
        ttk.Button(buttons,text="Add enemy",command=lambda:self.guard(enemy_dialog)).pack(side="left")
        ttk.Button(buttons,text="Edit enemy",command=lambda:self.guard(lambda:enemy_dialog(True))).pack(side="left")
        def remove():
            if listing.curselection():old["enemies"].pop(listing.curselection()[0]);refresh()
        ttk.Button(buttons,text="Remove",command=remove).pack(side="left");refresh()
        def apply(v):
            old.update(id=v["id"],map=v["map"],party_at=[int(v["party_x"]),int(v["party_y"])])
            a=copy_adventure(self.document)
            if index is None:a["encounters"].append(old)
            else:a["encounters"][index]=old
            self.commit(a)
        form.submit(apply)

    def build_events(self):
        body=ttk.Panedwindow(self.event_tab,orient="horizontal");body.pack(fill="both",expand=True)
        left=ttk.Frame(body,width=280);event_shell,self.event_form=scroll_frame(body);body.add(left,weight=1);body.add(event_shell,weight=3)
        self.event_listing=tk.Listbox(left,exportselection=False);self.event_listing.pack(fill="both",expand=True,padx=6,pady=6)
        self.event_listing.bind("<<ListboxSelect>>",lambda _:self.guard(self.populate_event))
        buttons=ttk.Frame(left);buttons.pack(fill="x")
        for label,callback in [("New",self.new_event),("Duplicate",self.duplicate_event),("Delete",self.delete_event)]:ttk.Button(buttons,text=label,command=lambda cb=callback:self.guard(cb)).pack(side="left")
        self.event_id=None;self.event_vars={};self.event_text=None;self.event_pending=False

    def refresh_events(self):
        self.event_listing.delete(0,"end")
        for e in self.adventure["events"]:self.event_listing.insert("end",f"{e['op']:8} {e['id']}")
        if self.event_id:
            at=next((i for i,e in enumerate(self.adventure["events"]) if e["id"]==self.event_id),None)
            if at is not None:self.event_listing.selection_set(at)

    def populate_event(self):
        if not self.event_listing.curselection():return
        index=self.event_listing.curselection()[0];identity=self.adventure["events"][index]["id"]
        if self.event_pending:
            self.apply_event()
            index=next(i for i,e in enumerate(self.adventure["events"]) if e["id"]==identity)
            self.event_listing.selection_clear(0,"end");self.event_listing.selection_set(index)
        e=self.adventure["events"][index];self.event_id=e["id"]
        self.render_event_form(copy.deepcopy(e))

    def render_event_form(self,e):
        for child in self.event_form.winfo_children():child.destroy()
        self.event_vars={};self.event_text=None;self.event_draft=e;self.event_pending=False;row=0
        events=[v["id"] for v in self.adventure["events"]]
        self.event_form.columnconfigure(1,weight=1)
        def field(key,value,choices=None):
            nonlocal row
            ttk.Label(self.event_form,text=key.replace("_"," ").title()).grid(row=row,column=0,sticky="w",pady=4,padx=4)
            var=tk.StringVar(value=str(value));self.event_vars[key]=var
            var.trace_add("write",lambda *_:setattr(self,"event_pending",True))
            control=ttk.Combobox(self.event_form,textvariable=var,values=choices,state="readonly",width=50) if choices is not None else ttk.Entry(self.event_form,textvariable=var,width=52)
            control.grid(row=row,column=1,sticky="ew",pady=4);row+=1;return control
        field("id",e["id"]);op=field("op",e["op"],list(OPS))
        def change(_):self.render_event_form(event_template(self.document,self.event_vars["op"].get(),self.event_id))
        op.bind("<<ComboboxSelected>>",lambda event:self.guard(lambda:change(event)))
        if "text" in e:
            ttk.Label(self.event_form,text="Dialogue").grid(row=row,column=0,sticky="nw",pady=5)
            self.event_text=tk.Text(self.event_form,height=7,width=48,wrap="word");self.event_text.grid(row=row,column=1,sticky="ew");self.event_text.insert("1.0",e["text"]);row+=1
            self.event_text.edit_modified(False)
            def modified(_):
                if self.event_text and self.event_text.edit_modified():self.event_pending=True;self.event_text.edit_modified(False)
            self.event_text.bind("<<Modified>>",modified)
            field("portrait",e.get("portrait","none"),["none","broker","training"] if self.document.manifest["requires"]=="none" else ["none","broker","training","lounge","prison","inventor","cinema","hospital","comstar","clothes","video-hut","mayor"])
        for key in ("next","failure","then","else","cancel","win","loss","flee"):
            if key in e:field(key,e[key],events)
        for key,collection in [("flag","flags"),("person","people"),("map","maps"),("shop","shops"),("encounter","encounters")]:
            if key in e:field(key,e[key],[v if isinstance(v,str) else v["id"] for v in self.adventure[collection]])
        for key in ("value","credits"):
            if key in e:field(key,e[key])
        if "at" in e:field("x",e["at"][0]);field("y",e["at"][1])
        if e["op"]=="choice":
            field("choice_count",len(e["options"]),[str(i) for i in range(1,6)])
            for i in range(5):
                value=e["options"][i] if i<len(e["options"]) else dict(label="Choice",next=events[0])
                field(f"label_{i+1}",value["label"]);field(f"choice_{i+1}",value["next"],events)
        if e["op"]=="lua":
            field("script",e["script"],[v["id"] for v in self.document.manifest.get("scripts",[])])
            field("route_count",len(e["routes"]),[str(i) for i in range(1,6)])
            for i in range(5):field(f"route_{i+1}",e["routes"][i] if i<len(e["routes"]) else events[0],events)
        ttk.Button(self.event_form,text="Apply event",command=lambda:self.guard(self.apply_event)).grid(row=row,column=1,sticky="e",pady=10)
        ttk.Label(self.event_form,text="Apply adds an undo step. Save/Validate checks every reference and dialogue bound.",wraplength=540).grid(row=row+1,column=0,columnspan=2,sticky="w",pady=6)

    def apply_event(self):
        if not self.event_id:return
        e=copy.deepcopy(self.event_draft);values={k:v.get() for k,v in self.event_vars.items()}
        e.update({k:values[k] for k in e if k not in ("text","options","routes","at") and k in values})
        for key in ("value","credits"):
            if key in e:e[key]=int(values[key])
        if self.event_text:e["text"]=" ".join(self.event_text.get("1.0","end-1c").split())
        if "at" in e:e["at"]=[int(values["x"]),int(values["y"])]
        if e["op"]=="choice":e["options"]=[dict(label=values[f"label_{i+1}"],next=values[f"choice_{i+1}"]) for i in range(int(values["choice_count"]))]
        if e["op"]=="lua":e["routes"]=[values[f"route_{i+1}"] for i in range(int(values["route_count"]))]
        a=copy_adventure(self.document);index=next(i for i,v in enumerate(a["events"]) if v["id"]==self.event_id)
        if e["id"]!=self.event_id:raise EditorError("Existing event IDs stay stable. Duplicate to create a new identity.")
        a["events"][index]=e;self.event_pending=False;self.commit(a)

    def new_event(self):
        a=copy_adventure(self.document);e=event_template(self.document,"say");a["events"].append(e);self.event_id=e["id"];self.commit(a);self.populate_event()
    def duplicate_event(self):
        if not self.event_id:return
        a=copy_adventure(self.document);e=copy.deepcopy(next(v for v in a["events"] if v["id"]==self.event_id));e["id"]=new_id(self.document,"events","event");a["events"].append(e);self.event_id=e["id"];self.commit(a);self.populate_event()
    def delete_event(self):
        if not self.event_id:return
        a=copy_adventure(self.document)
        if len(a["events"])==1:raise EditorError("Keep at least one event.")
        a["events"]=[v for v in a["events"] if v["id"]!=self.event_id];self.event_id=None;self.commit(a)
        for child in self.event_form.winfo_children():child.destroy()

    def build_world(self):
        bar=ttk.Frame(self.world_tab,padding=8);bar.pack(fill="x")
        for label,callback in [("Start / party",self.start_dialog),("New person",self.person_dialog),("New shop",self.shop_dialog),("Add flag",self.flag_dialog)]:ttk.Button(bar,text=label,command=lambda cb=callback:self.guard(cb)).pack(side="left",padx=4)
        self.world_listing=tk.Listbox(self.world_tab,exportselection=False);self.world_listing.pack(fill="both",expand=True,padx=8,pady=8)
        self.world_listing.bind("<Double-Button-1>",lambda _:self.guard(self.edit_world))
        ttk.Button(self.world_tab,text="Delete selected",command=lambda:self.guard(self.delete_world)).pack(anchor="e",padx=8,pady=8)

    def refresh_world(self):
        self.world_ids=[];self.world_listing.delete(0,"end")
        for key in ("people","shops","flags"):
            for i,value in enumerate(self.adventure[key]):
                self.world_ids.append((key,i));self.world_listing.insert("end",f"{key:8} {value if isinstance(value,str) else value['id']}"+(f"  {value.get('name','')}" if isinstance(value,dict) else ""))

    def edit_world(self):
        if self.world_listing.curselection():
            key,index=self.world_ids[self.world_listing.curselection()[0]]
            if key=="people":self.person_dialog(index)
            elif key=="shops":self.shop_dialog(index)
    def delete_world(self):
        if self.world_listing.curselection():
            key,index=self.world_ids[self.world_listing.curselection()[0]];a=copy_adventure(self.document);a[key].pop(index);self.commit(a)

    def person_dialog(self,index=None):
        old=copy.deepcopy(self.adventure["people"][index]) if index is not None else dict(id=new_id(self.document,"people","person"),identity="actor:2" if self.document.manifest["requires"]=="none" else "chi:edward",name="New companion",attributes=[8,8,8],skills=[1,1,1,1,1,1,1],weapon=0,armor=0)
        form=Form(self,"Character template")
        form.field("id",old["id"]);form.field("name",old.get("name",""))
        form.field("identity",old["identity"],[f"actor:{i}" for i in range(10)] if self.document.manifest["requires"]=="none" else ["chi:jason","chi:rex","chi:edward","chi:russ","chi:rick","chi:zeke","chi:possum","chi:marco","chi:rusty","chi:hunter"])
        for i,label in enumerate(["strength","dexterity","intelligence"]):form.field(label,old["attributes"][i])
        for i,label in enumerate(["sidearms","rifles","heavy_arms","gunnery","piloting","technical","medical"]):form.field(label,old["skills"][i])
        form.field("weapon",old["weapon"]);form.field("armor",old["armor"])
        def apply(v):
            value=dict(id=v["id"],identity=v["identity"],attributes=[int(v[k]) for k in ("strength","dexterity","intelligence")],skills=[int(v[k]) for k in ("sidearms","rifles","heavy_arms","gunnery","piloting","technical","medical")],weapon=int(v["weapon"]),armor=int(v["armor"]))
            if v["name"]:value["name"]=v["name"]
            a=copy_adventure(self.document)
            if index is None:a["people"].append(value)
            else:a["people"][index]=value
            self.commit(a)
        form.submit(apply)

    def shop_dialog(self,index=None):
        old=self.adventure["shops"][index] if index is not None else dict(id=new_id(self.document,"shops","shop"),stock=[])
        form=Form(self,"Shop stock");form.field("id",old["id"])
        selected=tk.Listbox(form.body,selectmode="multiple",exportselection=False,height=14,width=60)
        selected.grid(row=form.row,column=0,columnspan=2,padx=10);form.row+=1
        for i,m in enumerate(self.document.content["mechs"]):
            selected.insert("end",m["name"])
            if m["id"] in old["stock"]:selected.selection_set(i)
        def apply(v):
            value=dict(id=v["id"],stock=[self.document.content["mechs"][i]["id"] for i in selected.curselection()]);a=copy_adventure(self.document)
            if index is None:a["shops"].append(value)
            else:a["shops"][index]=value
            self.commit(a)
        form.submit(apply)

    def flag_dialog(self):
        form=Form(self,"New flag");form.field("id",new_id(self.document,"flags","flag"))
        def apply(v):a=copy_adventure(self.document);a["flags"].append(v["id"]);self.commit(a)
        form.submit(apply)

    def start_dialog(self):
        old=self.adventure["start"];form=Form(self,"Start and initial party")
        form.field("map",old["map"],[m["id"] for m in self.adventure["maps"]]);form.field("x",old["at"][0]);form.field("y",old["at"][1]);form.field("credits",old["credits"]);form.field("event",old["event"],[e["id"] for e in self.adventure["events"]])
        form.field("party_count",len(old["party"]),[str(i) for i in range(1,9)])
        for i in range(8):
            member=old["party"][i] if i<len(old["party"]) else dict(person=self.adventure["people"][0]["id"],mech="none")
            form.field(f"person_{i+1}",member["person"],[p["id"] for p in self.adventure["people"]]);form.field(f"mech_{i+1}",member["mech"],["none"]+[m["id"] for m in self.document.content["mechs"]])
        def apply(v):
            a=copy_adventure(self.document);a["start"]=dict(map=v["map"],at=[int(v["x"]),int(v["y"])],credits=int(v["credits"]),event=v["event"],party=[dict(person=v[f"person_{i+1}"],mech=v[f"mech_{i+1}"]) for i in range(int(v["party_count"]))]);self.commit(a)
        form.submit(apply)

    def apply_pending(self):
        self.finish_stroke()
        if self.event_pending:self.apply_event()
    def save(self):self.apply_pending();self.parent.apply_form();self.status.set(self.document.save());self.parent.refresh_list()
    def validate(self):self.apply_pending();self.parent.apply_form();self.status.set(self.document.validate())
    def undo(self):
        self.stroke=None
        if self.event_pending:
            self.event_pending=False;self.populate_event();return
        self.parent.apply_form();self.document.undo();self.refresh();self.parent.refresh_list();self.populate_event()
    def redo(self):self.apply_pending();self.parent.apply_form();self.document.redo();self.refresh();self.parent.refresh_list();self.populate_event()
    def play(self):self.save();self.parent.launch_player()
    def play_here(self):self.save();self.parent.launch_player((self.scene()["id"],*self.cursor))
    def close(self):
        # Shared document edits remain in the parent even if this window closes.
        self.apply_pending();self.window.destroy();self.parent.map_editor=None
