"""Small desktop interaction helpers shared by Construction Kit views."""
import tkinter as tk
from tkinter import ttk


def tooltip(widget,text):
    state={'timer':None,'window':None}
    def hide(_=None):
        if state['timer']:widget.after_cancel(state['timer']);state['timer']=None
        if state['window']:state['window'].destroy();state['window']=None
    def show():
        state['timer']=None
        if not widget.winfo_exists():return
        tip=tk.Toplevel(widget);tip.overrideredirect(True)
        ttk.Label(tip,text=text() if callable(text) else text,padding=7,wraplength=400,relief='solid').pack()
        tip.geometry(f'+{max(0,min(widget.winfo_rootx(),widget.winfo_screenwidth()-410))}+{min(widget.winfo_rooty()+widget.winfo_height()+4,widget.winfo_screenheight()-80)}')
        state['window']=tip
    def enter(_):hide();state['timer']=widget.after(650,show)
    widget.bind('<Enter>',enter,add='+');widget.bind('<Leave>',hide,add='+');widget.bind('<ButtonPress>',hide,add='+');widget.bind('<Destroy>',hide,add='+')


class TextHistory:
    """ttk.Entry has no built-in Undo; leave Text's native undo stack intact."""
    def __init__(self,window):
        self.states={}
        window.bind('<FocusIn>',self.remember,add='+');window.bind('<KeyRelease>',self.remember,add='+')
    def remember(self,event):
        widget=event.widget
        if not isinstance(widget,ttk.Entry) or isinstance(widget,ttk.Combobox):return
        value=widget.get()
        if len(value)>65536:return
        state=self.states.setdefault(widget,[[],[],False])
        if state[2]:return
        if not state[0] or state[0][-1]!=value:state[0].append(value);state[0][:]=state[0][-80:];state[1].clear()
        for key in list(self.states):
            if not key.winfo_exists():self.states.pop(key,None)
    def undo(self,widget,redo=False):
        state=self.states.get(widget)
        if not state:return False
        self.remember(type('Event',(),{'widget':widget}))
        past,future,_=state
        if redo:
            if not future:return False
            past.append(future.pop())
        else:
            if len(past)<2:return False
            future.append(past.pop())
        state[2]=True
        try:widget.delete(0,'end');widget.insert(0,past[-1]);widget.icursor('end')
        finally:state[2]=False
        return True


def size_form(form):
    window=form.window
    if not window.winfo_exists():return
    window.update_idletasks()
    width=min(max(620,form.body.winfo_reqwidth()+40),window.winfo_screenwidth()-60)
    height=min(max(230,form.body.winfo_reqheight()+105),window.winfo_screenheight()-100)
    owner=form.owner.window.winfo_toplevel()
    x=max(0,min(owner.winfo_rootx()+(owner.winfo_width()-width)//2,window.winfo_screenwidth()-width))
    y=max(0,min(owner.winfo_rooty()+(owner.winfo_height()-height)//2,window.winfo_screenheight()-height))
    window.minsize(min(480,width),200);window.geometry(f'{width}x{height}+{x}+{y}')


def flow_toolbar(frame):
    """Wrap labelled controls when DPI or a narrow dock runs out of width."""
    children=list(frame.pack_slaves())
    for child in children:child.pack_forget()
    state={'job':None,'layout':None}
    def arrange():
        state['job']=None
        if not frame.winfo_exists():return
        available=max(120,frame.winfo_width()-12);x=y=row_height=0;layout=[]
        for child in children:
            width=min(available,child.winfo_reqwidth());height=child.winfo_reqheight()
            if x and x+width>available:y+=row_height+4;x=row_height=0
            layout.append((child,x,y,width,height));x+=width+6;row_height=max(row_height,height)
        signature=[(str(child),x,y,w,h) for child,x,y,w,h in layout]
        if signature==state['layout']:return
        state['layout']=signature
        for child,x,y,w,h in layout:child.place(x=x+3,y=y+2,width=w,height=h)
        frame.configure(height=y+row_height+12)
    def changed(_=None):
        if state['job'] is None:state['job']=frame.after_idle(arrange)
    def destroy(event):
        if event.widget is frame and state['job']:frame.after_cancel(state['job']);state['job']=None
    frame.bind('<Configure>',changed,add='+');frame.bind('<Destroy>',destroy,add='+');changed()
