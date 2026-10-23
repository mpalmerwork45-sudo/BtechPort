"""Common desktop launch paths; subprocess arguments never pass through a shell."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from editor_model import EditorError

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / 'work/roster-editor'


def binary(name):
    suffix = '.exe' if os.name == 'nt' else ''
    for folder in ('build', 'build-windows', 'build/Release', 'build/Debug'):
        path = ROOT / folder / (name+suffix)
        if path.is_file(): return path
    return ROOT / 'build' / (name+suffix)


def default_settings():
    return dict(player=str(binary('btech-port')), data=str(ROOT/'Original DOS'),
                **{name+'-data':str(ROOT/'work'/file) for name,file in
                   [('dialogue','talk-data.bin'),('combat','combat-data.bin'),('world','world-data.bin')]})


def settings():
    value=default_settings()
    try: value.update(json.loads((STATE/'settings.json').read_text()))
    except (OSError,ValueError): pass
    return value


def prepare_original(paths):
    missing=[key for key in ('dialogue','combat','world') if not Path(paths[key+'-data']).is_file()]
    if not missing:return
    source=Path(paths['data'])/'BTECH.EXE'
    if not source.is_file():raise EditorError('Choose your original DOS game folder in Player setup, or play an independent demo.')
    for key in missing:
        script='talk' if key=='dialogue' else key
        result=subprocess.run([sys.executable,str(ROOT/'tools'/('prepare_'+script+'.py')),
                               '--data',str(Path(paths['data']).resolve()),'--output',str(Path(paths[key+'-data']).resolve())],
                              cwd=ROOT,capture_output=True,text=True,timeout=30)
        if result.returncode:raise EditorError(result.stderr.strip() or 'Cannot prepare original game data.')


def restore_legacy_campaign_saves(choice, state_dir, legacy_dir=None):
    """Copy older command-line slots into vacant launcher slots, keeping originals."""
    if choice not in ('Original', 'Updated'):
        return []
    source_dir=Path(legacy_dir) if legacy_dir is not None else ROOT/'work'
    target_dir=Path(state_dir)/'games'/choice.lower()
    edition='-updated' if choice=='Updated' else ''
    restored=[]
    for slot in range(1,7):
        suffix='' if slot==1 else '-'+str(slot)
        source=source_dir/('player-save'+edition+suffix+'.btp')
        target=target_dir/('game'+edition+suffix+'.btp')
        if not source.is_file() or target.exists():
            continue
        # The desktop launcher introduced a separate namespace. Preserve each
        # slot number and edition, and never replace newer desktop progress.
        data=source.read_bytes()
        target_dir.mkdir(parents=True,exist_ok=True)
        try:
            output=target.open('xb')
        except FileExistsError:
            continue
        try:
            with output:
                output.write(data)
            shutil.copystat(source,target)
        except BaseException:
            target.unlink(missing_ok=True)
            raise
        restored.append((source,target))
    return restored


def game_command(choice, paths, state_dir, project=None, resume=False):
    player=Path(paths['player'])
    if not player.is_file():raise EditorError('The game player has not been built. Use Build application in the launcher.')
    state_dir=Path(state_dir);state_dir.mkdir(parents=True,exist_ok=True)
    command=[str(player.resolve())]
    original=choice in ('Original','Updated')
    if project:
        from editor_model import ProjectDocument,references,needs_original
        doc=ProjectDocument(Path(project),binary('btp-project'))
        original=needs_original(doc.manifest)
        identity=doc.manifest['package_id']
        # A changed project gets fresh launch/save slots, preserving earlier
        # revisions. C save loading still verifies the full package fingerprint.
        digest=hashlib.sha256(b''.join(doc.snapshot[name] for name in references(doc.manifest))).hexdigest()[:16]
        save=state_dir/'games'/identity/digest/'game.btp'
        candidate=save.with_name(save.stem+'-project-'+identity+save.suffix)
        playable=doc.root
        if doc.source is not None:
            # Source projects launch a content-specific compiled cache. Notes
            # and module organization do not create new campaign save slots.
            playable=save.parent/'package'
            if not playable.exists():doc.export(playable)
            else:
                retained=ProjectDocument(playable,doc.validator)
                if any(retained.snapshot.get(name)!=doc.snapshot[name] for name in references(doc.manifest)):
                    raise EditorError('The cached playable package was edited. Preserve it separately, then choose a new launcher state directory.')
            doc.unchanged_on_disk()
        command+=['--project',str(playable)]
    else:
        command+=['--edition',choice.lower()]
        save=state_dir/'games'/choice.lower()/'game.btp';candidate=save
        # Import personal saves only into the real desktop state folder. Tests
        # and temporary library previews must never pick up the user's campaign.
        if state_dir.resolve()==STATE.resolve():
            restore_legacy_campaign_saves(choice,state_dir)
    save.parent.mkdir(parents=True,exist_ok=True)
    command+=['--save-file',str(save.resolve())]
    if original:
        prepare_original(paths)
        for key in ('data','dialogue-data','combat-data','world-data'):command+=['--'+key,str(Path(paths[key]).resolve())]
    if resume:
        # Updated's normal save namespace is derived by the player.
        if choice=='Updated' and not project:
            candidate=save.with_name(save.stem+'-updated'+save.suffix)
        if not candidate.exists():raise EditorError('No quicksave exists for this game version. Choose New game first; F5 saves during play.')
        command+=['--load',str(candidate.resolve())]
    return command


def spawn(command, state_dir):
    state_dir=Path(state_dir);state_dir.mkdir(parents=True,exist_ok=True)
    with (state_dir/'player.log').open('a',encoding='utf-8') as log:
        return subprocess.Popen(command,cwd=ROOT,stdout=log,stderr=log)
