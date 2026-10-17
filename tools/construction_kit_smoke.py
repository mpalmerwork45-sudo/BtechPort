"""Real Tk workflows for the Construction Kit milestones on private Xvfb."""
def run(env,work):
    import copy
    import os
    from pathlib import Path
    import tempfile
    import time
    import tkinter as tk
    from tkinter import messagebox
    from unittest.mock import patch
    from PIL import ImageGrab
    from editor_model import ProjectDocument,create_project
    from roster_editor import RosterEditor
    from building_templates import service_building
    from event_workbench import EventGraph,ObjectiveEditor,editor_data
    from playtest_workbench import PlaytestWindow
    root=Path(__file__).resolve().parents[1];os.environ['DISPLAY']=env['DISPLAY']
    with tempfile.TemporaryDirectory(prefix='construction-kit-',dir=work) as tmp:
        tmp=Path(tmp);doc=create_project(root/'examples/beacon-demo',tmp/'game','kit-test','Construction Kit test',root/'build/btp-project')
        window=tk.Tk();errors=[];window.report_callback_exception=lambda kind,error,tb:errors.append(error)
        def pump():
            window.update()
            if errors:raise errors.pop(0)
        def fail(title,text,**kwargs):raise AssertionError(f'{title}: {text}')
        with patch.object(messagebox,'showerror',fail):
            try:
                app=RosterEditor(window,root/'build/btp-project',tmp/'settings');app.set_document(doc)
                assert window.title()=='BattleTech Construction Kit'
                menu=service_building(doc,'Full service depot','Depot',{op:100 for op in ('repair','rearm','heal','salvage')},doc.content['mechs'][0]['id'])
                app.edit_adventure();owner=app.map_editor;owner.event_id=menu;owner.refresh_events();owner.populate_event();pump()
                graph=EventGraph(owner);pump();first=doc.adventure['events'][0]['id'];x,y=graph.positions[first]
                graph.canvas.event_generate('<Button-1>',x=int(x+20),y=int(y+20));graph.canvas.event_generate('<B1-Motion>',x=int(x+60),y=int(y+60));graph.canvas.event_generate('<ButtonRelease-1>',x=int(x+60),y=int(y+60));pump()
                assert editor_data(doc)['event_layout'][first]==[x+40,y+40]
                graph.selected=menu;graph.edit();pump();assert owner.event_id==menu
                graph.window.lift();pump();ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'construction-kit-events.png')
                objectives=ObjectiveEditor(owner);pump();objectives.window.destroy()
                graph.window.destroy();test=PlaytestWindow(owner);test.actions.delete('1.0','end');test.actions.insert('1.0','accept\n');test.name.set('smoke');test.run(False)
                deadline=time.monotonic()+20
                while test.busy and time.monotonic()<deadline:pump();time.sleep(.02)
                assert not test.busy and test.selected() and (test.selected()/'state.btp').exists(),test.status.get()
                assert test.trace.get_children();test.window.lift();pump();ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'construction-kit-checkpoint.png')
                test.window.destroy();owner.save();reopened=ProjectDocument(doc.root,doc.validator)
                assert editor_data(reopened)==editor_data(doc)
                print('PASS: Construction Kit title, services, event forms/graph dragging, shared metadata, saved checkpoints and runtime trace inspection.')
            finally:window.destroy()
