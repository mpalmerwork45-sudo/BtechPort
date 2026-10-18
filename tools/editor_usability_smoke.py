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
    finally:workspace.closing=True;root.destroy()
