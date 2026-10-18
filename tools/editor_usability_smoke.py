"""User journeys for window ownership and transactional editor drafts."""
def run(env, work):
    import copy
    import os
    from pathlib import Path
    import tempfile
    import tkinter as tk
    from tkinter import messagebox
    from unittest.mock import patch
    from editor_model import ProjectDocument, create_project, EditorError
    from editor_session import apply_draft, guard
    from roster_editor import RosterEditor
    from art_editing import new_image
    from graphics_editor import open_image_editor
    from action_tracks import edit_track
    root=Path(__file__).resolve().parents[1]
    os.environ['DISPLAY']=env['DISPLAY']
    with tempfile.TemporaryDirectory(prefix='editor-usability-',dir=work) as directory:
        directory=Path(directory)
        document=create_project(root/'examples/beacon-demo',directory/'game','usability','Usability test',root/'build/btp-project')
        window=tk.Tk();callback_errors=[]
        window.report_callback_exception=lambda kind,error,tb:callback_errors.append(error)
        def pump():
            window.update()
            if callback_errors:raise callback_errors.pop(0)
        def unexpected(title,message,**kw):raise AssertionError(title+': '+message)
        with patch.object(messagebox,'showerror',unexpected):
            try:
                app=RosterEditor(window,document.validator,directory/'settings');app.set_document(document);pump()
                mount=app.mount_dialog(True);mount.values['ammunition'].set('broken')
                guard(mount,lambda:apply_draft(mount));pump()
                assert 'whole number' in mount.error.get()
                assert mount.values['ammunition'].get()=='broken'
                assert window.grab_current()==mount.window
                with patch.object(messagebox,'askyesnocancel',return_value=None):
                    app.close();pump();assert window.winfo_exists() and mount.window.winfo_exists()
                mount.values['ammunition'].set('0');apply_draft(mount);app.save();pump()
                app.edit_adventure();maps=app.map_editor;maps.edit_graphics();art=maps.art_editor
                image=new_image('usability',document.art['images'],'Draft sprite','sprite',8,8,4);art.put(image);app.save()
                pixel=open_image_editor(art,image);pixel.new_layer();pump()
                # A later invalid roster draft must roll back an earlier art
                # application without discarding either editor's input.
                before=copy.deepcopy(document.art)
                app.variables[('mass_tons',)][0].set('bad mass')
                try:app.save()
                except EditorError:pass
                else:raise AssertionError('Invalid mass unexpectedly saved')
                assert document.art==before and len(pixel.image['_layers'])==2
                assert app.variables[('mass_tons',)][0].get()=='bad mass'
                app.variables[('mass_tons',)][0].set(str(app.item()['mass_tons']))
                with patch.object(messagebox,'askyesnocancel',return_value=None):
                    maps.close();pump();assert pixel.window.winfo_exists()
                app.save();pump()
                reopened=ProjectDocument(document.root,document.validator)
                assert b'Layer 2' in reopened.metadata['EDITOR.json']
                assert not app._editor_scope.dirty()
                edit_track(pixel);pump()
                forms=[d.view for d in app._editor_scope.live() if hasattr(d.view,'values') and hasattr(d.view,'callback')]
                form=forms[-1];form.values['sound'].set('bad cue')
                guard(form,lambda:apply_draft(form));pump()
                assert form.window.master==pixel.window
                assert form.error.get() and window.grab_current()==form.window
                form.window.destroy();pixel.window.destroy()
                print('PASS: inline mount/action errors, active dialog ownership, cancel-close protection, save-all artwork, and failed-save draft rollback.')
            finally:
                window.destroy()
        workspace_journey(directory,document.validator,env,work)
        recovery_journey(directory,document.validator)
        tasks_journey(directory,document.validator,env,work)


def workspace_journey(directory,validator,env,work):
    import tkinter as tk
    from tkinter import messagebox
    from unittest.mock import patch
    from PIL import ImageGrab
    from editor_model import ProjectDocument
    from editor_workspace import Workspace,EditorPane
    from graphics_editor import open_image_editor
    window=tk.Tk();errors=[];workspace=None
    def pump():
        window.update()
        if errors:raise errors.pop(0)
    def fail(title,message,**kw):raise AssertionError(title+': '+message)
    with patch.object(messagebox,'showerror',fail):
        try:
            workspace=Workspace(window,validator,directory/'workspace')
            window.report_callback_exception=lambda kind,error,tb:errors.append(error)
            app=workspace.app;app.set_document(ProjectDocument(directory/'game',validator));pump()
            workspace.open_unit('Mechs',app.document.content['mechs'][0]['id']);pump()
            app.edit_unit_sprite();pump()
            assert app.map_editor is None,'Sprite editing created an unnecessary map editor'
            assert any(v.key[1]=='pixels' for v in workspace.views.values())
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'editor-workspace-sprite.png')
            app.edit_adventure();maps=app.map_editor;pump()
            assert isinstance(maps.window,EditorPane)
            assert not any(isinstance(w,tk.Toplevel) for w in window.winfo_children())
            # Right-click an inactive tab, then change the selection before
            # invoking Close. The captured tab must close, preserving others
            # and reusing the map view's existing close/draft handling.
            sprite_pane=next(v for v in workspace.views.values() if v.key[1]=='pixels')
            sprite_pane.lift();pump();target=workspace.tabs.index(maps.window)
            hit=None
            for x in range(workspace.tabs.winfo_width()):
                try:index=workspace.tabs.index(f'@{x},10')
                except tk.TclError:continue
                if index==target:hit=x;break
            assert hit is not None,'Map tab is not reachable'
            menus=[]
            with patch.object(tk.Menu,'tk_popup',lambda menu,*args:menus.append(menu)):
                workspace.tabs.event_generate('<Button-3>',x=hit,y=10);pump()
            assert menus[-1].entrycget(0,'label')=='Close'
            sprite_pane.lift();menus[-1].invoke(0);pump()
            assert sprite_pane.winfo_exists() and workspace.tabs.tab(maps.window,'state')=='hidden'
            app.edit_adventure();pump();assert app.map_editor is maps
            print('PASS: tab context Close targets the clicked pane and preserves other tabs and the shared map controller.',flush=True)
            scenes=app.document.adventure['maps'];workspace.open_map(scenes[0]['id']);workspace.record_navigation();pump()
            workspace.open_map(scenes[1]['id']);workspace.record_navigation();pump();workspace.navigate(-1);pump()
            assert maps.scene()['id']==scenes[0]['id'],'Back did not restore the selected map'
            maps.edit_graphics();art=maps.art_editor;image=art.document.art['images'][-1]
            pixel=open_image_editor(art,image);pump()
            assert open_image_editor(art,image) is pixel
            pixel.new_layer();app.save();pump()
            assert not app._editor_scope.dirty()
            graph=maps.event_graph();assert maps.event_graph() is graph;pump()
            event=next(e for e in app.document.adventure['events'] if e['op']=='say')
            graph.selected=event['id'];graph.edit();pump()
            graph.properties.event_text.delete('1.0','end');graph.properties.event_text.insert('1.0','Edited from the event inspector.');graph.properties.event_pending=True
            app.save();pump()
            assert next(e for e in app.document.adventure['events'] if e['id']==event['id'])['text']=='Edited from the event inspector.'
            graph.arrange();pump();ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'editor-workspace-graph.png')
            graph.properties.event_text.insert('end',' Pending.');graph.properties.event_pending=True
            with patch.object(messagebox,'askyesnocancel',return_value=None):workspace.close_tab();pump()
            assert graph.window.winfo_exists() and graph.properties.event_pending
            app.save();pump()
            graph.objectives();pump()
            assert all(isinstance(v,EditorPane) for v in workspace.views.values())
            workspace.navigate(-1);pump();workspace.navigate(1);pump()
            workspace.reset_layout();pump();workspace.persist_layout()
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'editor-workspace.png')
            assert not any(isinstance(w,tk.Toplevel) for w in window.winfo_children())
            print('PASS: one workspace, embedded map/graphics/sprite/event/objective views, tab reuse, navigation, save/reopen and layout persistence.')
        finally:
            if workspace:workspace.closing=True
            window.destroy()


def recovery_journey(directory,validator):
    import copy
    import tkinter as tk
    from editor_model import create_project,ProjectDocument
    from editor_workspace import Workspace
    from editor_recovery import identity
    from art_editing import new_image
    from graphics_editor import open_image_editor
    from action_tracks import edit_track
    project=create_project(__import__('pathlib').Path('examples/beacon-demo'),directory/'recover-game','recover-test','Recovery test',validator)
    state=directory/'recover-settings'
    root=tk.Tk();workspace=Workspace(root,validator,state);app=workspace.app;app.set_document(project);root.update()
    try:
        art=app.graphics_editor();image=new_image('recover-test',project.art['images'],'Recovery sprite','sprite',8,8,4);art.put(image)
        pixel=open_image_editor(art,image);app.save();root.update()
        pixel.window.lift();pixel.new_layer();root.update()
        assert len(pixel.image['_layers'])==2
        workspace.edit_history(False);root.update();assert len(pixel.image['_layers'])==1
        workspace.edit_history(True);root.update();assert len(pixel.image['_layers'])==2
        app.edit_adventure();graph=app.map_editor.event_graph()
        event=next(e for e in project.adventure['events'] if e['op']=='say')
        graph.selected=event['id'];graph.edit();graph.properties.event_text.insert('end',' Unfinished dialogue.');graph.properties.event_pending=True
        edit_track(pixel);form=[d.view for d in app._editor_scope.live() if hasattr(d.view,'callback')][-1];form.values['sound'].set('invalid sound')
        app.variables[('mass_tons',)][0].set('unfinished mass')
        baseline=dict(project.snapshot);workspace.recovery.write(app._editor_scope)
        record=workspace.recovery.read(workspace.recovery.path(app._editor_scope))
        assert any(e['state'].get('values',{}).get('sound')=='invalid sound' for e in record['drafts'] if isinstance(e['state'].get('values'),dict))
    finally:workspace.closing=True;root.destroy()

    # A new process has no old callbacks or Tk widgets to rely on.
    root=tk.Tk();workspace=Workspace(root,validator,state);app=workspace.app
    try:
        app.set_document(ProjectDocument(project.root,validator));workspace.recovery.offered.add(identity(app._editor_scope));root.update()
        workspace.recovery.restore(app._editor_scope,record);root.update()
        assert not getattr(app._editor_scope,'unrestored_recovery',False)
        assert app.variables[('mass_tons',)][0].get()=='unfinished mass'
        pixel=next(v.controller for v in workspace.views.values() if v.key[1]=='pixels')
        assert len(pixel.image['_layers'])==2
        forms=[d.view for d in app._editor_scope.live() if hasattr(d.view,'callback')]
        assert len(forms)==1 and forms[0].values['sound'].get()=='invalid sound'
        assert 'Unfinished dialogue.' in app.map_editor.event_graph().properties.event_text.get('1.0','end')
        assert app.document.snapshot==baseline
        app.variables[('mass_tons',)][0].set(str(app.item()['mass_tons']));forms[0].values['sound'].set('0')
        app.save();root.update();workspace.recovery.write(app._editor_scope)
        assert not workspace.recovery.path(app._editor_scope).exists()
        assert not app._editor_scope.dirty()
        print('PASS: shared artwork Undo/Redo and crash recovery restore layers, event text and invalid unit/animation fields before a valid save.')
        # A lost/moved project must still be recoverable from its recorded
        # baseline. The source bytes and raw invalid inputs remain intact.
        from unittest.mock import patch
        moved=directory/'recover-original-moved';project.root.rename(moved)
        target=directory/'recovered-copy';target.mkdir()
        with patch('editor_recovery.filedialog.askdirectory',return_value=str(target)):
            scope=workspace.recovery.copy_into(record,root)
        root.update()
        assert scope.document.root==target and app.variables[('mass_tons',)][0].get()=='unfinished mass'
        assert (moved/project.manifest['definitions']).is_file()
        assert scope.document.snapshot==baseline and workspace.recovery.path(scope).is_file()
        print('PASS: a missing source project recovers into a separate copy, retaining invalid fields and its own recovery record.')
    finally:workspace.closing=True;root.destroy()



def tasks_journey(directory,validator,env,work):
    import threading
    import time
    import tkinter as tk
    from unittest.mock import patch
    from pathlib import Path
    from PIL import ImageGrab
    from editor_model import create_project,ProjectDocument
    from editor_workspace import Workspace
    from editor_tasks import save,validate
    project=create_project(Path('examples/beacon-demo'),directory/'task-game','task-test','Background tasks',validator)
    root=tk.Tk();workspace=Workspace(root,validator,directory/'task-settings');app=workspace.app;app.set_document(project);root.update()
    errors=[];root.report_callback_exception=lambda kind,error,tb:errors.append(error)
    beats=[];running=True
    def heartbeat():
        if running:beats.append(time.monotonic());root.after(10,heartbeat)
    heartbeat()
    def pump_until(predicate,timeout=15):
        deadline=time.monotonic()+timeout
        while not predicate():
            root.update()
            if errors:raise errors.pop(0)
            if time.monotonic()>deadline:raise AssertionError('Editor task did not finish')
            time.sleep(.005)
        root.update()
    try:
        field=app.variables[('price',)][0];field.set('4321')
        before=(project.root/project.manifest['definitions']).read_bytes()
        gate=threading.Event();entered=threading.Event();original=ProjectDocument.validate
        def slow(document):entered.set();gate.wait(5);return original(document)
        with patch.object(ProjectDocument,'validate',slow):
            started=time.monotonic();save(workspace,app._editor_scope);feedback=time.monotonic()-started
            pump_until(entered.is_set);field=app.variables[('price',)][0];field.set('4567')
            root.after(200,gate.set);pump_until(lambda:not workspace.tasks.jobs)
        assert (project.root/project.manifest['definitions']).read_bytes()==before,'Stale validation saved earlier fields'
        assert 'changed during validation' in app.status.get()
        save(workspace,app._editor_scope);pump_until(lambda:not workspace.tasks.jobs)
        assert not app._editor_scope.dirty()
        assert ProjectDocument(project.root,validator).content['mechs'][0]['price']==4567
        gate=threading.Event();entered=threading.Event();original_save=ProjectDocument.save
        def slow_save(document):entered.set();gate.wait(5);return original_save(document)
        app.variables[('price',)][0].set('5000')
        with patch.object(ProjectDocument,'save',slow_save):
            save(workspace,app._editor_scope);pump_until(entered.is_set)
            app.variables[('price',)][0].set('5050');gate.set();pump_until(lambda:not workspace.tasks.jobs)
        assert ProjectDocument(project.root,validator).content['mechs'][0]['price']==5000
        assert app.variables[('price',)][0].get()=='5050' and app._editor_scope.dirty()
        assert 'Newer edits remain unsaved' in app.status.get()
        before=dict(ProjectDocument(project.root,validator).snapshot)
        with patch.object(ProjectDocument,'save',side_effect=OSError('Simulated disk write failure')):
            save(workspace,app._editor_scope);pump_until(lambda:not workspace.tasks.jobs)
        assert ProjectDocument(project.root,validator).snapshot==before and app._editor_scope.dirty()
        assert app.variables[('price',)][0].get()=='5050' and not app._editor_scope.saving
        save(workspace,app._editor_scope);pump_until(lambda:not workspace.tasks.jobs)
        assert ProjectDocument(project.root,validator).content['mechs'][0]['price']==5050 and not app._editor_scope.dirty()
        print('PASS: edits during a durable save remain unsaved; write failure preserves disk and current edits, and retry saves them.')
        # Navigation stays live during validation; callbacks are retired on
        # close without reactivating a closed tab or losing later edits.
        workspace.open_map();validate(workspace,app._editor_scope);workspace.app.window.lift()
        pump_until(lambda:not workspace.tasks.jobs)
        gaps=[b-a for a,b in zip(beats,beats[1:])]
        print(f'PASS: background save rejects stale validation, saves corrected inputs, and leaves navigation responsive; initial feedback {feedback*1000:.1f}ms, heartbeat max {max(gaps,default=0)*1000:.1f}ms.')
        for percent in (100,150,200):
            workspace.scale(percent);root.update();workspace.open_map();root.update()
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/f'editor-scale-{percent}.png')
        workspace.scale(100);root.update()
        # Play the real SDL game from a validated private snapshot and stop
        # exactly the process this workspace launched.
        app.settings['player']=str(Path('build/btech-port').resolve())
        gate=threading.Event();entered=threading.Event();original_export=ProjectDocument.export
        def slow_export(document,target):entered.set();gate.wait(5);return original_export(document,target)
        with patch.object(ProjectDocument,'export',slow_export):
            unrelated=workspace.tasks.submit('Independent operation',app,lambda cancel:gate.wait(5))
            workspace.play_session.start(app._editor_scope);pump_until(entered.is_set)
            workspace.play_session.stop()
            assert not unrelated.cancelled.is_set()
            gate.set();pump_until(lambda:not workspace.tasks.jobs)
            assert workspace.play_session.process is None and not workspace.play_session.preparing
        workspace.play_session.start(app._editor_scope)
        pump_until(lambda:workspace.play_session.process is not None)
        process=workspace.play_session.process;root.after(200,workspace.play_session.stop)
        pump_until(lambda:workspace.play_session.process is None)
        assert process.poll() is not None
        assert not app._editor_scope.dirty()
        print('PASS: 100/150/200% workspace captures, isolated preparation cancellation and real snapshot Play/Stop without changing editor or ordinary game saves.')
        from editor_benchmark import run as benchmark
        benchmark(workspace,directory/'large-fixture',validator,work)
    finally:
        running=False;workspace.closing=True;root.destroy()
