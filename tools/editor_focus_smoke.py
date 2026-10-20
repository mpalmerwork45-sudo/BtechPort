"""KWin focus/stacking checks in a private D-Bus session and X display."""
def run(env,work):
    import os
    import signal
    import subprocess
    import tempfile
    import time
    import tkinter as tk
    from tkinter import filedialog
    from pathlib import Path
    from PIL import ImageGrab
    from editor_model import create_project
    from editor_workspace import Workspace
    from editor_session import guard,apply_draft
    from reference_session import WindowKeys
    with tempfile.TemporaryDirectory(prefix='editor-kwin-',dir=work) as temporary:
        directory=Path(temporary);manager=None;root=None
        settings=dict(env,XDG_CONFIG_HOME=str(directory/'config'),XDG_CACHE_HOME=str(directory/'cache'),KWIN_COMPOSE='N')
        try:
            with (work/'editor-kwin.log').open('w') as log:
                manager=subprocess.Popen(['dbus-run-session','--','kwin_x11','--replace'],env=settings,stdout=log,stderr=log,start_new_session=True)
            for _ in range(100):
                check=subprocess.run(['xprop','-root','_NET_SUPPORTING_WM_CHECK'],env=env,capture_output=True,text=True)
                if 'window id #' in check.stdout:break
                if manager.poll() is not None:raise AssertionError('KWin did not start; see editor-kwin.log')
                time.sleep(.05)
            else:raise AssertionError('KWin did not claim the private display')
            root=tk.Tk();workspace=Workspace(root,Path('build/btp-project'),directory/'state')
            document=create_project(Path('examples/beacon-demo'),directory/'game','focus-test','Focus test',Path('build/btp-project'))
            workspace.app.set_document(document);root.update();errors=[]
            root.report_callback_exception=lambda kind,error,tb:errors.append(error)
            def pump(duration=.15):
                deadline=time.monotonic()+duration
                while time.monotonic()<deadline:
                    root.update();time.sleep(.01)
                    if errors:raise errors.pop(0)
            form=workspace.app.mount_dialog(True);pump();form.values['ammunition'].set('invalid')
            guard(form,lambda:apply_draft(form));pump()
            assert root.grab_current() is form.window
            assert root.focus_get() is form.widgets['ammunition']
            root.lift();pump()
            stack=root.tk.splitlist(root.tk.call('wm','stackorder',root._w))
            assert stack[-1]==form.window._w,'Transient error form was obscured by its workspace'
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'editor-kwin-focus.png')
            # Cancel the actual Tk file chooser via XTEST, then correct the
            # original field. No simulated messagebox replaces this path.
            keys=WindowKeys()
            def cancel_chooser():
                try:
                    window=next(w for w,title in keys.windows() if title=='Recovery focus chooser');keys.key(window,'Escape',press_gap=0)
                except Exception as error:
                    errors.append(error)
                    root.tk.call('::tk::dialog::file::CancelCmd','.__tk_filedialog')
            root.after(400,cancel_chooser)
            selected=filedialog.askopenfilename(parent=form.window,title='Recovery focus chooser',initialdir=directory)
            pump();assert not selected and root.grab_current() is form.window
            form.widgets['ammunition'].focus_set();form.values['ammunition'].set('0');apply_draft(form);pump()
            assert root.grab_current() is None
            root.iconify();pump();root.deiconify();pump()
            assert root.state()=='normal'
            # Exercise the reported map toolbar routes, not only roster forms.
            # KWin maps new transient windows asynchronously.
            workspace.app.edit_adventure();maps=workspace.app.map_editor;pump()
            def newest_form():
                return next(d.view for d in reversed(workspace.app._editor_scope.live())
                            if hasattr(d.view,'values'))
            for name in ('Encounter','Entrance','NPC'):
                maps.drawing_tools.buttons[name].invoke();pump()
                maps.canvas.event_generate('<Button-1>',x=48,y=48);pump()
                form=newest_form()
                assert form.window.winfo_viewable() and root.grab_current() is form.window,name
                assert form.apply_button.winfo_viewable(),name
                if name=='Encounter':
                    form.recovery_children['enemy']();pump()
                    child=newest_form()
                    assert child is not form and root.grab_current() is child.window
                    child.close();pump();assert root.grab_current() is form.window
                form.close();pump();assert root.grab_current() is None
                maps.canvas.event_generate('<ButtonRelease-1>',x=48,y=48);pump()
            # A dialog destroyed before its first Map must not leave a pending
            # callback or change the current grab when Tk next processes events.
            from adventure_editor import Form
            early=Form(maps,'Closed before mapping');early.close();pump()
            assert root.grab_current() is None
            # Validation can originate in Units but its JSON path names the
            # exact map/entrance. Navigation must use that path, not the owner.
            import copy
            from editor_session import report
            from editor_model import EditorError
            original=copy.deepcopy(document.adventure);invalid=copy.deepcopy(original)
            scene=invalid['maps'][1];door=scene['entrances'][0];door['at']=[0,0]
            wall=next(t for t in invalid['tiles'] if t['terrain']=='wall')
            cell=wall['key'] if invalid['schema_version']==1 else wall['id']
            scene['overlays'].append(dict(at=[0,0],rows=[cell*3 if invalid['schema_version']==1 else [cell]*3 for _ in range(3)]))
            document.replace_adventure(invalid)
            try:document.validate()
            except EditorError as error:report(workspace.app,error)
            else:raise AssertionError('Expected blocked entrance validation')
            pump();row=workspace.problem_list.get_children()[-1]
            workspace.problem_list.selection_set(row);workspace.problem_list.focus_set()
            workspace.problem_list.event_generate('<Return>');pump()
            assert maps.scene()['id']==scene['id'] and maps.selected_marker[2]==door['id']
            assert workspace.current_view() is maps.window
            assert workspace.output.tag_ranges('problem-'+row),'Output error has no navigation link'
            document.replace_adventure(original);maps.refresh();pump()
            # Real popup lifecycle: keep Tk's grab until Escape/outside-click.
            from types import SimpleNamespace
            from editor_ui import popup_menu
            where=SimpleNamespace(x_root=root.winfo_rootx()+300,y_root=root.winfo_rooty()+250)
            for _ in range(3):
                maps.map_tile_menu(SimpleNamespace(x=48,y=48,**vars(where)));pump()
                menu=maps.map_context_menu
                assert menu.winfo_viewable() and root.grab_current() is menu
                assert root.focus_get() is menu
                menu.event_generate('<Escape>');pump()
                assert not menu.winfo_viewable() and root.grab_current() is None
            maps.map_tile_menu(SimpleNamespace(x=48,y=48,**vars(where)));pump()
            menu=maps.map_context_menu
            menu.event_generate('<ButtonPress-1>',x=-30,y=-30)
            menu.event_generate('<ButtonRelease-1>',x=-30,y=-30);pump()
            assert not menu.winfo_viewable() and root.grab_current() is None
            parent=Form(maps,'Context parent');parent.field('name','Unchanged');parent.submit(lambda _:None);pump()
            menu=tk.Menu(parent.window,tearoff=False);menu.add_command(label='Unused')
            popup_menu(menu,where);pump();menu.event_generate('<Escape>');pump()
            assert parent.window.winfo_viewable() and root.grab_current() is parent.window
            from tile_browser import TileBrowser
            browser=TileBrowser(maps);pump()
            assert root.grab_current() is browser.window
            browser.canvas.event_generate('<Button-3>',x=20,y=20);pump()
            active=root.grab_current()
            assert isinstance(active,tk.Menu) and active.winfo_viewable()
            active.event_generate('<Escape>');pump()
            assert browser.window.winfo_viewable() and root.grab_current() is browser.window
            browser.close();pump();assert root.grab_current() is parent.window
            parent.close();pump()
            print('PASS: KWin modal mapping, Encounter/Entrance/NPC toolbar forms, nested enemy dialog, early close, transient stacking, invalid-field focus, real file-chooser grab restoration and minimize/restore on an isolated desktop.')
            print('PASS: blocked entrance error jumps from Units to its map marker; Output links, repeated popup Escape, outside-click dismissal, tile chooser and parent grab restoration.')
        finally:
            if root:root.destroy()
            if manager and manager.poll() is None:
                os.killpg(manager.pid,signal.SIGTERM)
                try:manager.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(manager.pid,signal.SIGKILL);manager.wait()
