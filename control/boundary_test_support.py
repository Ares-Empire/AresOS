"""Install the actual generated policy in disposable, root-run Linux fixtures."""
import atexit
import json
import os
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def install_boundary(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o755)
    settings = json.loads((ROOT / 'settings/managed-settings.draft.json').read_text())
    settings_path, mcp_path = directory / 'managed-settings.json', directory / 'managed-mcp.json'
    settings_path.write_text(json.dumps(settings))
    mcp_path.write_bytes((ROOT / 'settings/managed-mcp.json').read_bytes())
    for path in (settings_path, mcp_path):
        path.chmod(0o644)
    return {'managed_settings': str(settings_path), 'managed_mcp': str(mcp_path)}


_FIXTURES = {}


def fixture_boundary(directory):
    """Root-run containers must not put policy beneath the runner-owned bind mount."""
    if os.geteuid() == 0:
        logical = str(directory)
        if logical not in _FIXTURES:
            prefix = Path('/etc/claude-code/fixtures')
            prefix.mkdir(mode=0o755, parents=True, exist_ok=True)
            protected = Path(tempfile.mkdtemp(prefix='boundary-', dir=prefix))
            _FIXTURES[logical] = protected
            atexit.register(shutil.rmtree, protected, ignore_errors=True)
        directory = _FIXTURES[logical]
    return install_boundary(directory)
