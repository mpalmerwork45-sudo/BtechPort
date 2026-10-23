"""Exercise scenario checkpoint selection and strict current-content checks."""
def run(env,work):
    import copy,json,tempfile,time,tkinter as tk
    from pathlib import Path
    from unittest.mock import patch
    from PIL import ImageGrab
    from world_route_demo import create
    from editor_model import encoded
    from editor_workspace import Workspace
    root=Path(__file__).resolve().parents[1];tool=root/'build/btp-project'
    with tempfile.TemporaryDirectory(prefix='saved-journey-gui-',dir=work) as tmp:
        folder=Path(tmp);doc=create(folder/'game',tool)
        full=dict(format='btp-author-scenario-v1',seed=42,steps=[dict(op='walk',world='survey:aster',at=[54,64]),
            dict(op='checkpoint',name='departed'),dict(op='walk',world='survey:aster',at=[90,64])])
        suffix=dict(format='btp-author-scenario-v1',steps=[dict(op='assert',world_at=[54,64]),dict(op='walk',world='survey:aster',at=[90,64])])
        for name,value in [('full',full),('continue',suffix)]:(folder/(name+'.json')).write_bytes(encoded(value))
        window=tk.Tk();workspace=Workspace(window,tool,folder/'settings');window.geometry('1440x940+0+0');errors=[]
        window.report_callback_exception=lambda kind,error,tb:errors.append(error)
        def pump(condition=lambda:True,timeout=20):
            deadline=time.monotonic()+timeout
            while True:
                window.update()
                if errors:raise errors.pop(0)
                if condition():return
                if time.monotonic()>deadline:raise AssertionError('Timed out: '+workspace.status.get())
                time.sleep(.01)
        try:
            app=workspace.app;app.set_document(doc);app.settings['player']=str(root/'build/btech-port')
            pane=workspace.open_playtest();pump()
            with patch('playtest_workbench.filedialog.askopenfilename',return_value=str(folder/'full.json')):pane.choose_scenario()
            pane.name.set('full');pane.scenario_buttons['Run scenario file'].invoke();pump(lambda:not pane.busy)
            report=json.loads(pane.last_report.read_bytes());assert report['status']=='passed',report
            selected=next(p for p in pane.entries if p.name=='checkpoint-departed.btp');pane.refresh(selected);pump()
            assert pane.trace.item(pane.trace.get_children()[0],'values')[0]=='22'
            pane.scenario_file.set(str(folder/'continue.json'));pane.name.set('continued')
            pane.scenario_buttons['From selected checkpoint'].invoke();pump(lambda:not pane.busy)
            resumed=json.loads(pane.last_report.read_bytes());assert resumed['status']=='passed',resumed
            assert resumed['setup']['kind']=='saved_checkpoint' and resumed['result']['start_rng']==[42,0,0]
            assert (pane.root/'full'/report['result']['save']).read_bytes()==(pane.root/'continued'/resumed['result']['save']).read_bytes()
            pane.show_report();pump();assert workspace.current_view().key[1]=='scenario-report'
            pane.window.lift();pump();ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'checkpoint-scenarios-editor.png')
            # Named scenario saves also work with the existing interactive
            # player and ordinary-action continuation, using their snapshot.
            pane.refresh(selected);pane.play();pump(lambda:not workspace.play_session.preparing)
            assert workspace.play_session.process and workspace.play_session.process.poll() is None
            workspace.play_session.stop();pump(lambda:workspace.play_session.process is None)
            pane.name.set('actions');pane.actions.delete('1.0','end');pane.actions.insert('1.0','right\n');pane.run(True)
            pump(lambda:not pane.busy);assert pane.selected().name=='state.btp'
            assert json.loads((pane.selected().parent/'state.json').read_bytes())['tick']==23

            # A changed current project must fail visibly instead of
            # silently testing the checkpoint's historical definitions.
            a=copy.deepcopy(doc.adventure);a['start']['credits']+=1;doc.replace_adventure(a)
            pane.refresh(selected);pane.name.set('changed-content');pane.run_scenario(True);pump(lambda:not pane.busy)
            assert 'failed' in pane.status.get()
            problem=next(p for p in workspace.problems if p.get('code')=='checkpoint.invalid')
            assert 'exact saved content' in problem['message']
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'checkpoint-scenarios-stale.png')
            # Controls wrap rather than disappearing at the supported
            # minimum desktop size; report stays a workspace tab.
            window.geometry('1024x768+0+0');pump();pane.window.lift();pump()
            for button in pane.scenario_buttons.values():
                assert button.winfo_ismapped() and button.winfo_rootx()+button.winfo_width()<=window.winfo_width()
            (work/'checkpoint-scenarios-gui.json').write_bytes(encoded(dict(status='passed',checks=[
                'choose scenario','run current project','named checkpoint state','resume saved RNG','exact final save',
                'report tab','play selected save','continue actions','changed-content rejection in Problems','1024x768 controls'])))
            print('PASS: scenario runs, named checkpoint selection, saved RNG, exact continuation, interactive Play, actions, visible stale-content error and compact layout.',flush=True)
        finally:
            if workspace.play_session.process:workspace.play_session.stop()
            workspace.tasks.shutdown();window.destroy()
