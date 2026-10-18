"""Consistent canvas zoom and visible drawing tools for editor views."""
import math
import tkinter as tk
from tkinter import ttk

from editor_ui import flow_toolbar, tooltip


class CanvasZoom(ttk.Frame):
    """Keep editable percentages separate from the renderer's committed scale.

    A half-typed value must never reach drawing, animation or pointer handlers.
    Existing views and saved navigation retain their native numeric zoom units.
    """
    def __init__(self, parent, variable, redraw, *, base=16, steps=(4, 8, 12, 16, 24, 32, 48, 64, 96),
                 integer=True, fit=None, label='Zoom'):
        super().__init__(parent)
        self.variable=variable;self.redraw=redraw;self.base=base;self.steps=steps
        self.integer=integer;self.fit=fit;self.canvas=None;self.after_scroll=None;self.remainder=0
        self.entry_value=tk.StringVar(self)
        ttk.Label(self,text=label).pack(side='left',padx=(0,4))
        values=(['Fit'] if fit else [])+[self.format(v) for v in steps]
        self.combo=ttk.Combobox(self,textvariable=self.entry_value,values=values,width=8,state='normal')
        self.combo.pack(side='left')
        self.combo.bind('<<ComboboxSelected>>',self.commit)
        for key in ('<Return>','<KP_Enter>','<FocusOut>'):self.combo.bind(key,self.commit)
        self.combo.bind('<Escape>',lambda _:self.reset())
        self.trace=variable.trace_add('write',self.sync)
        self.bind('<Destroy>',self.destroyed,add='+');self.sync()
        tooltip(self.combo,'Ctrl + mouse wheel over the canvas zooms at the pointer. Type a percentage and press Enter. '
                +('Pixel art scales to whole pixels. ' if integer else '')
                +f'Range: {self.format(steps[0])} to {self.format(steps[-1])}.')

    def format(self, value):return f'{value/self.base*100:g}%'

    def sync(self,*_):
        value=self.variable.get()
        self.entry_value.set('Fit' if value=='Fit' else self.format(float(value)))

    def reset(self):self.sync();return 'break'

    def scale(self):
        return self.fit() if self.variable.get()=='Fit' else float(self.variable.get())

    def attach(self, canvas, after_scroll=None):
        self.canvas=canvas;self.after_scroll=after_scroll
        # Tk sends Button-4/5 on X11 and MouseWheel on Windows/macOS. Binding
        # the modified event on the canvas avoids stealing ordinary scrolling.
        for sequence in ('<Control-MouseWheel>','<Control-Button-4>','<Control-Button-5>'):
            canvas.bind(sequence,self.wheel,add='+')

    def commit(self,_=None):
        value=self.entry_value.get().strip()
        if value.lower()=='fit' and self.fit:self.set('Fit');return 'break'
        try:
            value=float(value.rstrip('%').strip())*self.base/100
            if not math.isfinite(value) or value<=0:raise ValueError()
        except ValueError:
            # Reject incomplete/invalid text locally, without an error dialog
            # or a broken animation timer in the canvas behind the entry.
            return self.reset()
        self.set(value);return 'break'

    def set(self, value, anchor=None):
        old=self.scale();canvas=self.canvas
        if value!='Fit':
            value=max(self.steps[0],min(self.steps[-1],value))
            value=int(value+0.5) if self.integer else round(value,4)
        if value==('Fit' if self.variable.get()=='Fit' else old):self.sync();return
        if canvas is not None:
            x,y=anchor or (canvas.winfo_width()/2,canvas.winfo_height()/2)
            logical=(canvas.canvasx(x)/old,canvas.canvasy(y)/old)
        self.variable.set('Fit' if value=='Fit' else f'{value:g}')
        self.redraw()
        if canvas is not None:
            region=canvas.cget('scrollregion')
            if region:
                left,top,right,bottom=map(float,canvas.tk.splitlist(region));scale=self.scale()
                # Canvas fractions describe the entire scrollregion, not its
                # scrollable remainder. Include the border's canvas offset.
                inset=float(canvas.cget('highlightthickness'))+float(canvas.cget('borderwidth'))
                canvas.xview_moveto((logical[0]*scale-x+inset-left)/max(1,right-left))
                canvas.yview_moveto((logical[1]*scale-y+inset-top)/max(1,bottom-top))
            if self.after_scroll:self.after_scroll()

    def wheel(self,event):
        number=getattr(event,'num',None)
        if number in (4,5):count=1 if number==4 else -1
        else:
            delta=getattr(event,'delta',0)
            self.remainder+=delta if self.tk.call('tk','windowingsystem')=='aqua' else delta/120
            count=math.trunc(self.remainder);self.remainder-=count
        if count:
            value=self.scale()
            for _ in range(min(abs(count),len(self.steps))):
                choices=[v for v in self.steps if v>value+1e-6] if count>0 else [v for v in reversed(self.steps) if v<value-1e-6]
                if choices:value=choices[0]
            self.set(value,(event.x,event.y))
        return 'break'

    def destroyed(self,event):
        if event.widget is self:self.variable.trace_remove('write',self.trace)


class DrawingTools(ttk.Frame):
    """Labelled, mutually exclusive buttons; wrapping keeps every tool visible."""
    def __init__(self,parent,variable,groups,command):
        super().__init__(parent,padding=(6,0,6,2))
        self.buttons={}
        style=ttk.Style(self)
        style.configure('Drawing.Toolbutton',padding=(7,4),anchor='center',relief='raised',borderwidth=1,
                        background='#e5eaed',bordercolor='#b9c5cd')
        style.map('Drawing.Toolbutton',background=[('selected','#256477'),('active','#dcebed')],
                  foreground=[('selected','#ffffff')],relief=[('selected','sunken')])
        for index,(label,items) in enumerate(groups):
            if index:ttk.Frame(self,width=6).pack(side='left')
            for value,title,hint in items:
                button=ttk.Radiobutton(self,text=title,value=value,variable=variable,style='Drawing.Toolbutton',
                                       command=lambda v=value:command(v))
                button.pack(side='left');tooltip(button,f'{label}: {hint}');self.buttons[value]=button
        # Flow the whole strip together. Fixed rows per group would leave
        # little map visible when narrow docks make each group wrap again.
        flow_toolbar(self)
