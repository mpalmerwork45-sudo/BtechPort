"""Real library editing/import/export and launcher play/resume on private Xvfb."""
def run(env,work):
    import copy
    import json
    import os
    from pathlib import Path
    import subprocess
    import tempfile
    import time
    import tkinter as tk
    from tkinter import messagebox
    from unittest.mock import patch
    from PIL import ImageGrab
    from editor_model import ProjectDocument,create_project
    from roster_editor import RosterEditor
    from graphics_editor import open_image_editor
    from launcher import Launcher
    from reference_session import WindowKeys
    root=Path(__file__).resolve().parents[1];os.environ['DISPLAY']=env['DISPLAY']
    with tempfile.TemporaryDirectory(prefix='library-ui-',dir=work) as temp:
        temp=Path(temp);tool=root/'build/btp-project'
        doc=create_project(root/'examples/beacon-demo',temp/'game','library-ui','Library test game',tool)
        window=tk.Tk();errors=[];window.report_callback_exception=lambda kind,error,tb:errors.append(error)
        def pump():
            window.update()
            if errors:raise errors.pop(0)
        def fail(title,text,**kwargs):raise AssertionError(f'{title}: {text}')
        def choose(browser,kind,*ids):
            browser.kind.set(kind);browser.query.set('');browser.refresh()
            browser.listing.selection_set(ids);browser.show();pump()
        with patch.object(messagebox,'showerror',fail):
            try:
                app=RosterEditor(window,tool,temp/'state');app.settings['library-root']=str(temp/'library');app.set_document(doc)
                app.open_library();browser=app.unit_library_window;pump()
                assert len(browser.bundles)>=82
                # Check both requested mech silhouettes against the decoded
                # original animation, including a migrated cached Jenner.
                from art_editing import original_sprite
                for identity,first in [('mech-library:king-crab-kgc-0000',0),
                                       ('mech-library:awesome-aws-8q',146),
                                       ('chi-original:template-5',0)]:
                    choose(browser,'Mechs',identity);assert len(browser.photos)==4
                    preview=browser.edit();pump()
                    expected=original_sprite(preview.document,app.settings,first,16)
                    assert preview.sprite_source['frames']==expected['frames']
                    assert len({str(f) for f in expected['frames'][:4]})>1
                    preview.close();pump()
                choose(browser,'Vehicles','vehicles:patton');assert len(browser.photos)==4
                editor=browser.edit();pump();editor.variables[('name',)][0].set('Patton Library Test')
                editor.variables[('price',)][0].set('12345');editor.save();pump()
                assert browser.bundles['vehicles:patton']['revision']==2
                assert browser.bundles['vehicles:patton']['content']['mechs'][0]['price']==12345
                editor.close();pump()
                choose(browser,'Vehicles','vehicles:patton','vehicles:pegasus')
                original=copy.deepcopy(doc.content);browser.import_selected();pump();assert len(doc.content['mechs'])==5
                app.undo();pump();assert doc.content==original and not doc.metadata
                app.redo();pump();assert len(doc.content['mechs'])==5
                app.kind.set('Vehicles');app.change_kind();app.refresh_list('vehicles:patton')
                app.variables[('price',)][0].set('13000')
                with patch.object(messagebox,'askyesnocancel',return_value=True):browser.export_from_game()
                pump();assert browser.bundles['vehicles:patton']['revision']==3
                choose(browser,'Infantry','beacon:cole');infantry=browser.edit();pump()
                assert infantry.sprite_source['frames']==original_sprite(infantry.document,app.settings,270,16)['frames']
                infantry.variables[('name',)][0].set('Cole Library Test')
                infantry.variables[('attributes',0)][0].set('11');infantry.save();pump()
                opened=[]
                def capture(*args):
                    value=open_image_editor(*args);opened.append(value);return value
                infantry.close();pump()
                with patch('graphics_editor.open_image_editor',side_effect=capture):infantry=browser.edit_sprite()
                pump();sprite=opened[-1];sprite.color.set('42ab88ff')
                sprite.canvas.event_generate('<Button-1>',x=1,y=1);sprite.canvas.event_generate('<ButtonRelease-1>',x=1,y=1);pump()
                sprite.apply();infantry.save();pump();infantry.close();pump()
                choose(browser,'Infantry','beacon:cole');browser.infantry_art.set(True);browser.import_selected();pump()
                person=next(p for p in doc.adventure['people'] if p['id']=='beacon:cole')
                assert person['name']=='Cole Library Test' and person['attributes'][0]==11
                assert person.get('image') and any(i['id']==person['image'] for i in doc.art['images'])
                assert len({p['identity'] for p in doc.adventure['people']})==3
                # Imported vehicles become real starting units, rather than
                # just remaining unused library entries in this test project.
                a=copy.deepcopy(doc.adventure)
                for person,unit in zip(a['start']['party'],('vehicles:patton','vehicles:pegasus')):person['mech']=unit
                doc.replace_adventure(a);app.save();pump()
                exported=temp/'export';doc.export(exported);reopened=ProjectDocument(exported,tool)
                assert reopened.metadata==doc.metadata and reopened.art==doc.art
                browser.kind.set('All');browser.query.set('');browser.refresh();browser.window.lift();pump()
                ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'unit-library.png')
                browser.window.geometry('940x650+0+0');pump()
                assert browser.canvas.winfo_width()>=200 and browser.listing.winfo_width()>=300
                assert browser.status_label.winfo_ismapped()
                assert browser.status_label.winfo_rooty()+browser.status_label.winfo_height()<=browser.window.winfo_rooty()+browser.window.winfo_height()
                # Cancelling a close protects edits in an open library entry.
                choose(browser,'Vehicles','vehicles:patton');pending=browser.edit();pump()
                pending.variables[('price',)][0].set('12346')
                with patch.object(messagebox,'askyesnocancel',return_value=None):browser.close()
                assert browser.window.winfo_exists() and pending.window.winfo_exists()
                with patch.object(messagebox,'askyesnocancel',return_value=False):pending.close()
                pump();browser.window.lift();pump()
                form=browser.new();form.values['name'].set('New GUI hovercraft');form.values['type'].set('Hovercraft')
                form.apply_button.invoke();pump()
                new_editor=browser.editors[-1]
                assert new_editor.item()['name']=='NEW GUI HOVERCRAFT' and new_editor.item()['movement']['type']=='hover'
                new_editor.close();pump()
                ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'unit-library.png')
                print('PASS: built-ins, library property/sprite editing, revisions, multiple imports, undo/redo, game export, infantry identities/art and project save/export.',flush=True)
                # A real launcher button starts the newly authored project.
                # F5 is then continued through the launcher's quicksave action.
                launch_window=tk.Toplevel(window);launcher=Launcher(launch_window,temp/'launch')
                launcher.choice.set('My project');launcher.project.set(str(doc.root));launcher.describe();launch_window.lift();pump()
                ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'btechport-launcher.png')
                with patch.dict(os.environ,SDL_AUDIODRIVER='dummy'):
                    process=launcher.play();keys=WindowKeys()
                    try:
                        def game_window():
                            deadline=time.monotonic()+10
                            while time.monotonic()<deadline:
                                found=next((w for w,n in keys.windows() if n=='Library test game'),None)
                                if found:return found
                                if process.poll() is not None:raise AssertionError((temp/'launch/player.log').read_text())
                                pump();time.sleep(.025)
                            raise AssertionError('Game did not start from launcher')
                        game=game_window();keys.key(game,'F5');keys.key(game,'Ctrl+Shift+Escape');process.wait(timeout=10);pump()
                        assert process.returncode==0
                        process=launcher.play(True);game=game_window();keys.key(game,'Ctrl+Shift+Escape');process.wait(timeout=10);pump()
                        assert process.returncode==0
                    finally:
                        keys.x.XCloseDisplay(keys.display)
                        if process.poll() is None:process.terminate();process.wait(timeout=5)
                print('PASS: launcher starts the imported-vehicle game and resumes its real F5 quicksave, with no command-line setup.',flush=True)
                # The two campaign buttons retain their pre-game logo path
                # and use explicit separate edition/save namespaces.
                for choice in ('Original','Updated'):
                    launcher.choice.set(choice)
                    with patch.dict(os.environ,SDL_AUDIODRIVER='dummy'):
                        process=launcher.play();keys=WindowKeys()
                        try:
                            deadline=time.monotonic()+10;found=None
                            while time.monotonic()<deadline:
                                found=next((w for w,n in keys.windows() if n=='BtechPort - '+choice+' BTECH CHI'),None)
                                if found:break
                                if process.poll() is not None:raise AssertionError((temp/'launch/player.log').read_text())
                                pump();time.sleep(.025)
                            assert found,choice+' did not launch'
                            keys.key(found,'Ctrl+Shift+Escape');process.wait(timeout=10);assert process.returncode==0
                        finally:
                            keys.x.XCloseDisplay(keys.display)
                            if process.poll() is None:process.terminate();process.wait(timeout=5)
                print('PASS: launcher starts Original and Updated campaigns at the normal logo flow.',flush=True)
                launch_window.destroy()
                # Test the actual double-click entry with a clean system-Python
                # PATH and a different working directory, not just its class.
                clean=dict(os.environ,PATH='/usr/bin:/bin');clean.pop('PYTHONPATH',None)
                process=subprocess.Popen([str(root/'BtechPort')],cwd=temp,env=clean,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                keys=WindowKeys()
                try:
                    deadline=time.monotonic()+10;found=None
                    while time.monotonic()<deadline:
                        found=next((w for w,n in keys.windows() if n=='BattleTech Construction Kit'),None)
                        if found:break
                        if process.poll() is not None:raise AssertionError(process.communicate()[1])
                        pump();time.sleep(.025)
                    assert found,'Root application launcher did not appear'
                    # Xvfb has no window manager. This check only exercises
                    # startup; clean up our owned subprocess after finding it.
                    process.terminate();process.wait(timeout=5)
                    print('PASS: executable application entry starts from another directory with clean system Python.',flush=True)
                finally:
                    keys.x.XCloseDisplay(keys.display)
                    if process.poll() is None:process.terminate();process.wait(timeout=5)
            finally:window.destroy()
