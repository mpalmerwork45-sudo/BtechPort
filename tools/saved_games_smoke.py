"""Real launcher/editor Saved games journey on a private desktop and project."""
def run(env,work,windows=False):
    import copy,json,subprocess,tempfile,time,tkinter as tk
    from pathlib import Path
    from PIL import ImageGrab
    from launcher import Launcher
    from editor_model import create_project,ProjectDocument
    from app_runtime import binary,project_slot_name
    from save_catalogue import SaveCatalogue
    from saved_games_view import open_saved_games
    from reference_session import WindowKeys
    root=Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='saved-games-gui-',dir=work) as directory:
        folder=Path(directory);window=tk.Tk();launcher=Launcher(window,folder/'state');errors=[];keys=WindowKeys()
        window.report_callback_exception=lambda kind,error,tb:errors.append(error)
        def pump(condition=lambda:True,timeout=30):
            limit=time.monotonic()+timeout
            while True:
                window.update()
                if errors:raise errors.pop(0)
                if condition():return
                if time.monotonic()>limit:raise AssertionError('Saved games GUI timed out')
                time.sleep(.01)
        def player_window():return next((w for w,n in keys.windows() if n.startswith('BtechPort') or n=='Saved Games GUI'),None)
        def pick(view,path):
            key=next(k for k,r in view.rows.items() if r.path==path);view.table.selection_set(key);view.table.focus(key);view.select();return key
        try:
            doc=create_project(root/'examples/beacon-demo',folder/'Game é 漢字','saves-gui','Saved Games GUI',binary('btp-project'))
            launcher.choice.set('My project');launcher.project.set(str(doc.root));launcher.describe()
            model=SaveCatalogue(launcher.state_dir,launcher.paths,document=doc);saves=model.directory();saves.mkdir(parents=True)
            for slot in range(1,7):
                subprocess.run([str(binary('btech-headless')),'--project',str(doc.root),'--save',str(saves/project_slot_name(doc,slot))],capture_output=True,check=True,timeout=20)
            selected=saves/project_slot_name(doc,3);original=selected.read_bytes()
            view=launcher.saved_games();pump(lambda:view.job is None and len(view.rows)==6)
            assert all(r.mtime for r in view.rows.values())
            pick(view,selected);view.continue_game();pump(lambda:view.job is None and bool(launcher.running))
            process=launcher.running[-1];pump(lambda:player_window() is not None)
            game_window=player_window();keys.key(game_window,'F5');keys.key(game_window,'Ctrl+Shift+Escape');pump(lambda:process.poll() is not None)
            assert process.returncode==0 and selected.read_bytes()==original
            view.refresh();pump(lambda:view.job is None);assert any(r.location=='Backup' for r in view.rows.values())
            pick(view,selected);view.slot.set('6');view.recover();pump(lambda:view.job is None)
            assert 'occupied' in view.status.get(),view.status.get()
            (saves/project_slot_name(doc,6)).unlink();view.slot.set('6');view.recover();pump(lambda:view.job is None)
            assert (saves/project_slot_name(doc,6)).read_bytes()==original
            view.window.lift();pump()
            for button in view.buttons:assert button.winfo_rooty()+button.winfo_height()<=view.window.winfo_rooty()+view.window.winfo_height()
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/('saved-games-launcher'+('-windows' if windows else '')+'.png'))
            changed=copy.deepcopy(doc.adventure);changed['start']['credits']+=123;doc.replace_adventure(changed);doc.save()
            view.refresh();pump(lambda:view.job is None);pick(view,selected)
            assert view.selected().project and not view.selected().current
            editor=launcher.edit();workspace=editor.window.workspace;managed=open_saved_games(editor)
            pump(lambda:managed.job is None);pick(managed,selected);managed.continue_game()
            pump(lambda:managed.job is None and workspace.play_session.process is not None)
            pump(lambda:player_window() is not None);keys.key(player_window(),'Ctrl+Shift+Escape')
            pump(lambda:workspace.play_session.process is None)
            assert 'Continued' in managed.status.get(),managed.status.get()
            editor.window.winfo_toplevel().geometry('1280x800+0+0');editor.window.winfo_toplevel().lift();pump()
            for button in managed.buttons:
                assert button.winfo_rooty()+button.winfo_height()<=managed.window.winfo_rooty()+managed.window.winfo_height()
                assert button.winfo_rootx()+button.winfo_width()<=managed.window.winfo_rootx()+managed.window.winfo_width()
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/('saved-games-editor'+('-windows' if windows else '')+'.png'))
            assert selected.read_bytes()==original
            window.destroy()
            (work/('saved-games-gui'+('-windows' if windows else '')+'.json')).write_text(json.dumps(dict(status='passed',desktop='Linux Tk',player='Windows/Wine' if windows else 'Linux',checks=['six slots and dates','native launcher Continue/F5/quit','automatic backups','occupied-slot preservation','vacant-slot recovery','earlier exact revision after edits','editor Continue and normal Stop/log lifecycle','visible controls within window bounds']),indent=2)+'\n')
            print('PASS: launcher/editor saved games, all slots, exact old revisions, recovery, backups and native Continue.',flush=True)
        finally:
            for process in launcher.running:
                if process.poll() is None:process.terminate();process.wait(timeout=10)
            try:window.destroy()
            except tk.TclError:pass
            keys.x.XCloseDisplay(keys.display)
