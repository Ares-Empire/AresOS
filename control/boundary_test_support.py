"""Install the actual generated policy in disposable, root-run Linux fixtures."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def install_boundary(directory, socket_dir='/run/aresos-tools'):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o755)
    settings = json.loads((ROOT / 'settings/managed-settings.draft.json').read_text())
    if socket_dir not in settings['sandbox']['filesystem']['denyRead']:
        settings['sandbox']['filesystem']['denyRead'].append(socket_dir)
    settings_path, mcp_path = directory / 'managed-settings.json', directory / 'managed-mcp.json'
    settings_path.write_text(json.dumps(settings))
    mcp_path.write_bytes((ROOT / 'settings/managed-mcp.json').read_bytes())
    for path in (settings_path, mcp_path):
        path.chmod(0o644)
    return {'managed_settings': str(settings_path), 'managed_mcp': str(mcp_path)}
