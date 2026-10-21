"""Shared table sorting and keyboard completion for ordinary ttk controls."""
import re
import time
import tkinter as tk
from tkinter import ttk


def sort_key(value):
    text=str(value).strip();number=text.replace(',','')
    if re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)',number):return (0,float(number))
    # Natural text order also keeps model names like Unit 2 before Unit 10.
    return (1,tuple((0,int(p)) if p.isdigit() else (1,p.casefold()) for p in re.split(r'(\d+)',text)))


class TableOrder:
    def __init__(self,table):
        self.table=table;self.column=None;self.direction=0;self.natural=list(table.get_children());self.job=None;self.sorting=False
        self.headings={c:table.heading(c,'text') for c in ('#0',*table['columns'])}
        # Observe model refreshes (delete/reinsert, cell edits) without polling.
        # Moves change only the view: row IDs, selections and callbacks remain.
        self.original=table._w+'__order';table.tk.call('rename',table._w,self.original)
        table.tk.createcommand(table._w,self.command)
        table.bind('<Destroy>',self.destroy,add='+')

    def command(self,*args):
        result=self.table.tk.call(self.original,*args)
        mutation=args and (args[0] in ('insert','delete','detach') or args[0]=='item' and len(args)>3 or args[0]=='set' and len(args)>3)
        if mutation and not self.sorting:
            children=list(self.table.get_children());self.natural=[i for i in self.natural if i in children]
            if args[0]=='insert' and result in children:
                # Respect a caller's explicit insertion index in the natural
                # order; most refreshed tables append rows in document order.
                index=args[2]
                self.natural.insert(len(self.natural) if index=='end' else min(int(index),len(self.natural)),result)
            self.natural.extend(i for i in children if i not in self.natural)
            if self.direction and self.job is None:self.job=self.table.after_idle(self.apply)
        return result

    def click(self,column):
        self.direction=(self.direction+1)%3 if column==self.column else 1
        self.column=column;self.apply()

    def apply(self):
        if self.job:self.table.after_cancel(self.job);self.job=None
        table=self.table
        if not table.winfo_exists():return
        children=set(table.get_children());self.natural=[i for i in self.natural if i in children]
        order=self.natural
        if self.direction:
            order=sorted(order,key=lambda row:sort_key(table.item(row,'text') if self.column=='#0' else table.set(row,self.column)),reverse=self.direction==2)
        self.sorting=True
        try:
            for i,row in enumerate(order):table.move(row,'',i)
            for key,title in self.headings.items():table.heading(key,text=title+(' ↑' if self.direction==1 else ' ↓') if key==self.column and self.direction else title)
        finally:self.sorting=False

    def destroy(self,event):
        if event.widget is not self.table:return
        if self.job:self.table.after_cancel(self.job);self.job=None
        # Tk destroys the renamed widget command itself; release our proxy.
        self.table.tk.deletecommand(self.table._w)


def install(window):
    root=window._root()
    if getattr(root,'_list_helpers',False):return
    root._list_helpers=True
    def mapped(event):
        table=event.widget
        if isinstance(table,ttk.Treeview) and 'headings' in tuple(map(str,table['show'])) and not hasattr(table,'table_order'):
            table.table_order=TableOrder(table)
    def heading(event):
        table=event.widget
        if isinstance(table,ttk.Treeview) and table.identify_region(event.x,event.y)=='heading':
            mapped(event)
            if hasattr(table,'table_order'):
                column=table.identify_column(event.x)
                # Display order can differ from the underlying column tuple.
                if column!='#0':column=table.column(column,'id')
                table.table_order.click(column)
    root.bind_class('Treeview','<Map>',mapped,add='+')
    root.bind_class('Treeview','<ButtonRelease-1>',heading,add='+')

    def typed(event):
        combo=event.widget;posted=None
        # Tk's posted listbox is created internally, so event.widget may be its
        # Tcl path rather than a Python widget. Typing searches that open list
        # too; Enter/click still performs its ordinary selection callback.
        if not isinstance(combo,ttk.Combobox) and '.popdown.' in str(combo):
            posted=str(combo)
            try:combo=root.nametowidget(posted.split('.popdown.',1)[0])
            except KeyError:return
        if not isinstance(combo,ttk.Combobox) or combo.instate(['disabled']):return
        if event.state&0x0c:return  # Ctrl/Alt shortcuts keep their normal role.
        if not posted and not combo.instate(['readonly']):return
        values=tuple(map(str,combo['values']))
        if not values:return
        now=time.monotonic();before,stamp=getattr(combo,'_typeahead',('',0))
        if now-stamp>1.2:before=''
        if event.keysym=='BackSpace':prefix=before[:-1]
        elif event.char and event.char.isprintable():prefix=before+event.char
        else:combo._typeahead=('',0);return
        matches=[i for i,v in enumerate(values) if v.casefold().startswith(prefix.casefold())] if prefix else []
        if not matches and event.char:
            prefix=event.char;matches=[i for i,v in enumerate(values) if v.casefold().startswith(prefix.casefold())]
        combo._typeahead=(prefix,now)
        if matches:
            current=combo.current();index=matches[0]
            if before.casefold()==prefix.casefold() and len(prefix)==1:index=next((i for i in matches if i>current),matches[0])
            if posted:
                combo.tk.call(posted,'selection','clear',0,'end');combo.tk.call(posted,'selection','set',index)
                combo.tk.call(posted,'activate',index);combo.tk.call(posted,'see',index)
            else:
                combo.current(index)
                if index!=current:combo.event_generate('<<ComboboxSelected>>')
        return 'break'

    def complete(event):
        combo=event.widget
        if not isinstance(combo,ttk.Combobox) or combo.instate(['readonly']) or combo.instate(['disabled']) or event.state&0x0c:return
        character=event.char or (event.keysym if len(event.keysym)==1 else ' ' if event.keysym=='space' else '')
        if not character or not character.isprintable():return
        value=combo.get();cursor=combo.index('insert')
        if cursor!=len(value) or not value:return
        match=next((str(v) for v in combo['values'] if str(v).casefold().startswith(value.casefold())),None)
        if match and len(match)>len(value):combo.set(match);combo.icursor(len(value));combo.selection_range(len(value),'end')
    root.bind_class('TCombobox','<KeyPress>',typed,add='+')
    root.bind_class('ComboboxListbox','<KeyPress>',typed,add='+')
    root.bind_class('TCombobox','<KeyRelease>',complete,add='+')
