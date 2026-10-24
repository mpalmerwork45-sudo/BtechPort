"""Real SDL death popup, Space acknowledgement, held save/load and No exit."""
def run(env,work):
    from pathlib import Path
    import json,subprocess,tempfile,time
    from reference_session import WindowKeys
    from PIL import ImageGrab
    root=Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='game-over-gui-',dir=work) as directory:
        folder=Path(directory);frame=folder/'death.ppm'
        subprocess.run([str(root/'build/btp-game-over-tests'),str(root/'Original DOS'),str(root/'work/talk-data.bin'),str(root/'tests/fixtures/game-over-primary.txt'),str(frame)],check=True,capture_output=True,timeout=20)
        slot=folder/'held.btp'
        process=subprocess.Popen([str(root/'build/btech-port'),'--load',str(frame)+'.btp','--save-file',str(slot)],env=env,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        keys=WindowKeys()
        def until(condition,timeout=15):
            limit=time.monotonic()+timeout
            while not condition():
                if process.poll() is not None:raise RuntimeError(process.communicate())
                if time.monotonic()>limit:raise RuntimeError('Timed out death popup GUI check')
                time.sleep(.02)
        try:
            def find():return next((w for w,n in keys.windows() if n.startswith('BtechPort')),None)
            until(lambda:find() is not None);window=find();keys.key(window,'F5');until(slot.exists)
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'game-over-native-popup.png')
            before=slot.read_bytes();keys.key(window,'space');keys.key(window,'F5');until(lambda:slot.read_bytes()!=before)
            result=subprocess.run([str(root/'build/btech-headless'),'--load',str(slot)],capture_output=True,text=True,check=True,timeout=20)
            state=json.loads(result.stdout);assert state['mode']=='game-over' and state['actions_menu']['notice']==1,state
            ImageGrab.grab(xdisplay=env['DISPLAY']).save(work/'game-over-native-again.png')
            keys.key(window,'F9');keys.key(window,'Right');keys.key(window,'space')
            stdout,stderr=process.communicate(timeout=15)
            if process.returncode:raise RuntimeError(stderr)
            (work/'game-over-gui.json').write_text(json.dumps(dict(status='passed',checks=['original glyph/pixel hashes','native death popup','Space acknowledges','prompt save/reload','No exits normally']),indent=2))
            print('PASS: native death popup, Space acknowledgement, held save/load and replay No exit.',flush=True)
        finally:
            keys.x.XCloseDisplay(keys.display)
            if process.poll() is None:process.terminate();process.wait(timeout=5)
