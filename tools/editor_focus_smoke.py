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
            print('PASS: KWin transient stacking, invalid-field focus, real file-chooser cancellation/grab restoration and minimize/restore on an isolated desktop.')
        finally:
            if root:root.destroy()
            if manager and manager.poll() is None:
                os.killpg(manager.pid,signal.SIGTERM)
                try:manager.wait(timeout=5)
                except subprocess.TimeoutExpired:os.killpg(manager.pid,signal.SIGKILL);manager.wait()
