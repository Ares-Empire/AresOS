"""Local diagnostic: exercise the real descriptor walk inside this worktree."""
from contextlib import contextmanager
from pathlib import Path
import os
import shutil
from unittest.mock import patch


@contextmanager
def local_policy():
    root = Path('.work/linux-policy-root').resolve()
    target = root / 'etc/claude-code'
    target.mkdir(parents=True, exist_ok=True)
    for source, name in [('managed-settings.draft.json', 'managed-settings.json'), ('managed-mcp.json', 'managed-mcp.json')]:
        destination = target / name
        if not destination.exists():
            shutil.copyfile(Path('control/settings') / source, destination)
    real_open = os.open
    def opened(path, *args, **kwargs):
        return real_open(root if path == '/' else path, *args, **kwargs)
    with patch.object(os, 'open', side_effect=opened), patch('aresos_control.boundary.protected'):
        yield
