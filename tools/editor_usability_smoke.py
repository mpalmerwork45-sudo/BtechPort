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
