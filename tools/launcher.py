#!/usr/bin/env python3
"""Desktop entry point for playing games, editing projects and the Unit Library."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from editor_runtime import prefer_system_tk
if __name__=='__main__':prefer_system_tk()
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from app_runtime import ROOT,STATE,binary,settings,game_command,spawn
from editor_model import EditorError,ProjectDocument
from roster_editor import RosterEditor,configure_editor_style

GAMES={'Original':'Original CHI campaign with the original roster.',
       'Updated':'Original campaign with the expanded roster and Enhanced combat.',
       'BattleTech demo':'Last Beacon: two contracts, nine mechs and ten vehicles. Requires original CHI files.',
       'Vehicle proving ground':'Independent two-planet vehicle test game. No original files needed.',
       'Independent demo':'Small complete quest and editor template. No original files needed.',
       'My project':'Choose your own game project folder.'}
PROJECTS={'BattleTech demo':ROOT/'examples/battletech-demo',
          'Relay Contract (command-created)':ROOT/'examples/relay-contract',
          'Vehicle proving ground':ROOT/'examples/vehicle-lab',
          'Independent demo':ROOT/'examples/beacon-demo'}


def create_shortcut():
    # Generate an absolute local launch target. The source launchers themselves
    # remain portable when the checkout moves; regenerate this shortcut then.
    path=ROOT/'BtechPort.desktop'
    def quote(value):return '"'+str(value).replace('\\','\\\\').replace('"','\\"').replace('$','\\$').replace('`','\\`')+'"'
    launch=quote(ROOT/'ConstructionKit') if (ROOT/'ConstructionKit').is_file() else quote('python3')+' '+quote(ROOT/'BtechPort.pyw')
    path.write_text('[Desktop Entry]\nType=Application\nName=BattleTech Construction Kit\nComment=Play games, edit projects and browse the Unit Library\n'
                    +'Exec='+launch+'\nPath='+str(ROOT)+'\n'
                    +'Icon=applications-games\nTerminal=false\nCategories=Game;Development;\n',encoding='utf-8')
    path.chmod(0o755)
    return path


class Launcher:
    def __init__(self,window,state_dir=STATE):
        self.window,self.state_dir=window,Path(state_dir)
        self.state_dir.mkdir(parents=True,exist_ok=True)
        self.paths=settings();self.editors=[];self.running=[];self.build_process=None;self.callbacks=set()
        configure_editor_style(window)
        window.title('BattleTech Construction Kit');window.geometry('780x610');window.minsize(730,570)
        header=ttk.Frame(window,padding=(24,20,24,12));header.pack(fill='x')
        ttk.Label(header,text='BattleTech Construction Kit',style='Title.TLabel').pack(anchor='w')
        ttk.Label(header,text='Play a game, build your own, or work on the shared Unit Library.',style='Muted.TLabel').pack(anchor='w',pady=(6,0))
        body=ttk.Frame(window,padding=(24,0));body.pack(fill='both',expand=True)
        ttk.Label(body,text='Game or project',style='Section.TLabel').pack(anchor='w')
        self.choice=tk.StringVar(value='Independent demo' if (os.environ.get('BTP_BUNDLED_RUNTIME') or (ROOT/'DISTRIBUTION.json').is_file()) and not (ROOT/'Original DOS').exists() else 'BattleTech demo')
        self.game=ttk.Combobox(body,textvariable=self.choice,values=tuple(GAMES),state='readonly',font='TkDefaultFont')
        self.game.pack(fill='x',pady=8);self.game.bind('<<ComboboxSelected>>',lambda _:self.describe())
        self.description=tk.StringVar();ttk.Label(body,textvariable=self.description,wraplength=660).pack(fill='x',pady=(0,12))
        custom=ttk.Frame(body);custom.pack(fill='x')
        self.project=tk.StringVar()
        ttk.Entry(custom,textvariable=self.project).pack(side='left',fill='x',expand=True)
        ttk.Button(custom,text='Choose project...',command=lambda:self.guard(self.browse)).pack(side='left',padx=(8,0))
        play=ttk.Frame(body);play.pack(fill='x',pady=16)
        ttk.Button(play,text='New game',style='Accent.TButton',command=lambda:self.guard(self.play)).pack(side='left',padx=(0,8))
        ttk.Button(play,text='Continue quicksave',command=lambda:self.guard(lambda:self.play(True))).pack(side='left')
        ttk.Separator(body).pack(fill='x',pady=(0,16))
        edit=ttk.Frame(body);edit.pack(fill='x')
        ttk.Button(edit,text='Open editor',command=lambda:self.guard(self.edit)).pack(side='left',padx=(0,8))
        ttk.Button(edit,text='Unit Library',command=lambda:self.guard(self.library)).pack(side='left',padx=(0,8))
        ttk.Button(edit,text='New project',command=lambda:self.guard(self.new_project)).pack(side='left')
        ttk.Label(body,text='The editor has its own Play button. Game saves and library designs stay separate from the supplied examples.',style='Muted.TLabel',wraplength=660).pack(fill='x',pady=16)
        tools=ttk.Frame(body);tools.pack(fill='x')
        ttk.Button(tools,text='Player setup',command=lambda:self.guard(self.setup)).pack(side='left',padx=(0,8))
        ttk.Button(tools,text='Build application',command=lambda:self.guard(self.build)).pack(side='left',padx=(0,8))
        if os.name!='nt':ttk.Button(tools,text='Create launch shortcut',command=lambda:self.guard(self.shortcut)).pack(side='left')
        self.status=tk.StringVar(value='Ready. New game starts fresh; Continue loads the F5 quicksave for this version.')
        ttk.Label(window,textvariable=self.status,style='Status.TLabel',wraplength=710).pack(fill='x',side='bottom')
        window.protocol('WM_DELETE_WINDOW',self.close)
        window.bind('<Destroy>',self.destroyed,add='+')
        self.describe()

    def guard(self,method):
        try:return method()
        except (EditorError,OSError,ValueError,KeyError,subprocess.SubprocessError) as exc:
            self.status.set(str(exc));messagebox.showerror('BattleTech Construction Kit',str(exc),parent=self.window)

    def describe(self):self.description.set(GAMES[self.choice.get()])

    def browse(self):
        path=filedialog.askdirectory(title='Choose a game project containing project.json',parent=self.window)
        if path:self.project.set(path);self.choice.set('My project');self.describe()

    def selected_project(self):
        if self.choice.get()=='My project':
            if not self.project.get():raise EditorError('Choose your game project folder first.')
            return Path(self.project.get())
        return PROJECTS.get(self.choice.get())

    def play(self,resume=False):
        self.paths=settings()
        command=game_command(self.choice.get(),self.paths,self.state_dir,self.selected_project(),resume)
        process=spawn(command,self.state_dir);self.running.append(process)
        self.status.set('Game started. F5 saves; F9 loads. Close the game to return here.')
        self.later(500,lambda:self.monitor(process))
        return process

    def monitor(self,process):
        if not self.window.winfo_exists():return
        if process.poll() is None:self.later(500,lambda:self.monitor(process));return
        if process in self.running:self.running.remove(process)
        if process.returncode:
            log=(self.state_dir/'player.log').read_text(errors='replace')[-2500:]
            self.status.set('The game could not start. Check Player setup.')
            messagebox.showerror('Game launch',log,parent=self.window)
        else:self.status.set('Game closed. Choose another game or return to the editor.')

    def editor(self,project=None):
        tool=binary('btp-project')
        if not tool.exists():raise EditorError('Build the application first using the button below.')
        from editor_workspace import create_editor
        window=tk.Toplevel(self.window);app=create_editor(window,tool,self.state_dir)
        if project:app.set_document(ProjectDocument(project,tool))
        self.editors.append(app);return app

    def edit(self):
        project=self.selected_project()
        if project is None:project=ROOT/'examples/battletech-demo'
        return self.editor(project)

    def library(self):
        app=self.editor();app.open_library();return app.unit_library_window

    def new_project(self):
        app=self.editor();app.new_project();return app

    def setup(self):self.editor().setup()

    def shortcut(self):self.status.set('Created '+str(create_shortcut())+'. You may copy it to your desktop.')

    def build(self):
        if self.build_process and self.build_process.poll() is None:return
        command=[sys.executable,str(ROOT/'tools/build_application.py')]
        self.build_process=spawn(command,self.state_dir)
        self.status.set('Building with two jobs. Progress is written to player.log.')
        self.later(500,self.poll_build)

    def poll_build(self):
        if self.build_process.poll() is None:self.later(500,self.poll_build);return
        self.status.set('Build complete. Choose New game or Open editor.' if not self.build_process.returncode else 'Build failed. See work/roster-editor/player.log for details.')

    def close(self):
        for editor in list(self.editors):
            if editor.window.winfo_exists():
                editor.close()
                if editor.window.winfo_exists():return
        # Games run independently and are not killed when the launcher closes.
        self.window.destroy()

    def later(self,delay,callback):
        def run():
            self.callbacks.discard(identity);callback()
        identity=self.window.after(delay,run);self.callbacks.add(identity)

    def destroyed(self,event):
        if event.widget==self.window:
            for identity in self.callbacks:self.window.after_cancel(identity)
            self.callbacks.clear()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--create-shortcut',action='store_true')
    parser.add_argument('--check-runtime',action='store_true',help='bounded launcher/editor/PNG/player check (requires a display)')
    args=parser.parse_args()
    if args.check_runtime:
        from runtime_probe import check
        check();return
    if args.create_shortcut:print(create_shortcut());return
    window=tk.Tk();Launcher(window);window.mainloop()


if __name__=='__main__':main()
