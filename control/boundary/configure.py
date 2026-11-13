"""Explicit reproduction of the documented settings -> SRT boundary subset.

Not Claude Code's private settings resolver. See README for the exact difference.
Run as image root, not by the assistant or from its writable working directory.
"""
import json
from pathlib import Path

ROOT = Path('/opt/aresos-control')


def derive(settings):
    sandbox = settings['sandbox']
    return {
        'network': {key: sandbox['network'][key] for key in
                    ('allowedDomains', 'deniedDomains', 'allowAllUnixSockets', 'allowLocalBinding')},
        'filesystem': {
            key: [value.replace('~/', '/home/assistant/') for value in sandbox['filesystem'][key]]
            for key in ('denyRead', 'allowRead', 'denyWrite', 'allowWrite')
        },
        'allowNestedUserNamespaces': False,
        'enableWeakerNestedSandbox': False,
    }


if __name__ == '__main__':
    settings = json.loads((ROOT / 'optional-sandbox.json').read_text())
    (ROOT / 'sandbox.json').write_text(json.dumps(derive(settings), indent=2) + '\n')
    # SRT 0.0.81 otherwise asks bwrap 0.8 to create missing mandatory-deny
    # mount points after mounting this re-exposed work root read-only. Keep
    # benign placeholders in the image; the hostile checks detect omissions.
    work = Path('/home/assistant/work')
    for name in ['.gitconfig', '.gitmodules', '.bashrc', '.bash_profile',
                 '.zshrc', '.zprofile', '.profile', '.ripgreprc', '.mcp.json']:
        path = work / name
        if not path.exists():
            path.write_text('{"mcpServers":{}}\n' if name == '.mcp.json' else '')
    for name in ['.vscode', '.idea', '.claude/commands', '.claude/agents']:
        (work / name).mkdir(parents=True, exist_ok=True)

    for name in ('hostile.py', 'socket-state.py'):
        (work / ('boundary-' + name)).write_bytes((ROOT / name).read_bytes())
    # The native canary must not inherit the standalone helper's filter, or it
    # could pass even when the native binary's embedded stage is broken.
    native_canary = derive(settings)
    native_canary['network']['allowAllUnixSockets'] = True
    native_canary['allowNestedUserNamespaces'] = True
    (ROOT / 'native-canary.json').write_text(json.dumps(native_canary))
    import hashlib
    native = Path('/usr/local/bin/claude').resolve()
    (ROOT / 'native-pin.json').write_text(json.dumps({'sha256': hashlib.sha256(native.read_bytes()).hexdigest(),
        'cli_sha256': hashlib.sha256(native.read_bytes()).hexdigest()}))
