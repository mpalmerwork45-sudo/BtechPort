"""Short, process-wide writer lock; the OS releases it after a crash.

Readers never create lock files. All editor saves and command-line batches use
this lock; files written by other applications are still checked by snapshots.
The empty lock file stays in place so waiting processes lock the same inode.
"""
from contextlib import contextmanager
import os
from pathlib import Path
import threading
import hashlib
import tempfile
import getpass

_guard = threading.RLock()
_held = set()


@contextmanager
def project_lock(root):
    from editor_model import child, EditorError
    root = Path(root).resolve()
    with _guard:
        if root in _held:
            yield
            return
        # Locks live outside packages: even a rejected save must leave a
        # project's file inventory unchanged. A per-user private directory
        # also makes read-only packages inspectable without lock artifacts.
        owner=str(os.getuid()) if hasattr(os,'getuid') else hashlib.sha256(getpass.getuser().encode()).hexdigest()[:16]
        folder=Path(tempfile.gettempdir())/('btp-project-locks-'+owner)
        if folder.is_symlink():raise EditorError('Project lock directory must not be a symlink.')
        folder.mkdir(mode=0o700,exist_ok=True)
        path=child(folder,hashlib.sha256(str(root).encode()).hexdigest()+'.lock')
        with path.open('a+b') as stream:
            try:
                if os.name == 'nt':
                    import msvcrt
                    stream.seek(0)
                    if not stream.read(1):
                        stream.write(b'0'); stream.flush()
                    stream.seek(0)
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise EditorError('Project is being saved by another process. Retry after it finishes.') from exc
            _held.add(root)
            try:
                yield
            finally:
                _held.remove(root)
                if os.name == 'nt':
                    stream.seek(0); msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(stream, fcntl.LOCK_UN)
