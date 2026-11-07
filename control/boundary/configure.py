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
    settings = json.loads(Path('/etc/claude-code/managed-settings.json').read_text())
    (ROOT / 'sandbox.json').write_text(json.dumps(derive(settings), indent=2) + '\n')
