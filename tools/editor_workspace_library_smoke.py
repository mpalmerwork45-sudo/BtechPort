"""Concurrent project/library scopes, partial Save All and library recovery."""
def run(env,work):
    import copy
    from pathlib import Path
    import tempfile
    import time
    import tkinter as tk
    from editor_workspace import Workspace
    from editor_model import ProjectDocument,create_project
    from unit_library import UnitLibrary
    from editor_tasks import save
    from editor_recovery import identity
    with tempfile.TemporaryDirectory(prefix='workspace-library-',dir=work) as temporary:
        directory=Path(temporary);validator=Path('build/btp-project')
        document=create_project(Path('examples/beacon-demo'),directory/'game','scopes-test','Project and library scopes',validator)
        unit=document.content['mechs'][0]['id'];library=UnitLibrary(directory/'library',validator)
        saved=library.export_unit(document,unit,'Mechs')
        root=tk.Tk();workspace=Workspace(root,validator,directory/'state');app=workspace.app
        errors=[];root.report_callback_exception=lambda kind,error,tb:errors.append(error)
        def pump_until(test,seconds=30):
            deadline=time.monotonic()+seconds
            while not test():
                root.update();time.sleep(.005)
                if errors:raise errors.pop(0)
                if time.monotonic()>deadline:raise AssertionError('Workspace library task timed out')
            root.update()
        try:
            app.settings['library-root']=str(library.root);app.set_document(document);root.update()
            app.open_library();browser=app.unit_library_window
            pump_until(lambda:not workspace.tasks.jobs)
            browser.refresh(saved['entry_id']);editor=browser.edit();root.update()
            assert app._editor_scope is not editor._editor_scope and app.current==editor.current==unit
            editor.variables[('price',)][0].set('6500')
            app.variables[('price',)][0].set('invalid project price')
            outcomes=[];workspace.save_all_async(outcomes.append)
            pump_until(lambda:bool(outcomes))
            assert outcomes==[False]
            assert app.variables[('price',)][0].get()=='invalid project price'
            assert next(b for b in library.entries() if b['entry_id']==saved['entry_id'])['content']['mechs'][0]['price']==6500
            assert ProjectDocument(document.root,validator).content['mechs'][0]['price']!=6500
            app.variables[('price',)][0].set('7800');save(workspace,app._editor_scope);pump_until(lambda:not workspace.tasks.jobs)
            assert ProjectDocument(document.root,validator).content['mechs'][0]['price']==7800
            editor.edit_unit_sprite();root.update()
            pixel=next(v.controller for v in workspace.views.values() if v.scope is editor._editor_scope and v.key[1]=='pixels')
            pixel.new_layer();editor.variables[('price',)][0].set('invalid library price')
            workspace.recovery.write(editor._editor_scope);record=workspace.recovery.read(workspace.recovery.path(editor._editor_scope))
            # Simulate losing only the library's editor process state. The
            # catalog and disk bundle are not changed by the recovery record.
            for pane in list(workspace.views.values()):
                if pane.scope is editor._editor_scope and pane.controller is not editor:pane.destroy()
            editor.window.destroy();workspace.scopes.remove(editor._editor_scope)
            browser.refresh(saved['entry_id']);editor=browser.edit()
            workspace.recovery.offered.add(identity(editor._editor_scope));root.update()
            workspace.recovery.restore(editor._editor_scope,record);root.update()
            assert not getattr(editor._editor_scope,'unrestored_recovery',False)
            assert editor.variables[('price',)][0].get()=='invalid library price'
            pixel=next(v.controller for v in workspace.views.values() if v.scope is editor._editor_scope and v.key[1]=='pixels')
            assert len(pixel.image['_layers'])==2
            editor.variables[('price',)][0].set('6600');save(workspace,editor._editor_scope);pump_until(lambda:not workspace.tasks.jobs)
            assert not editor._editor_scope.dirty()
            editor.settings['player']=str(Path('build/btech-port').resolve())
            editor.window.lift();root.update();assert workspace.command_enabled('Preview library design')
            workspace.invoke('Preview library design');pump_until(lambda:workspace.play_session.process is not None)
            process=workspace.play_session.process;workspace.play_session.stop();pump_until(lambda:workspace.play_session.process is None)
            assert process.poll() is not None and not editor._editor_scope.dirty()
            workspace.close_scope(editor._editor_scope);root.update()
            assert not pixel.window.winfo_exists()
            print('PASS: asynchronous library loading, separate histories/save targets for identical unit IDs, partial Save All, library art/invalid-field recovery, SDL design preview and coordinated scope close.')
        finally:root.destroy()
