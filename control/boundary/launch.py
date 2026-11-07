"""Launcher draft: fixed CLI, fixed policy, mandatory effective seccomp check."""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

ROOT = Path('/opt/aresos-control')
FILTER = ROOT / 'node_modules/@anthropic-ai/sandbox-runtime/vendor/seccomp/x64/apply-seccomp'
CLAUDE = Path('/usr/local/bin/claude')


def trusted(path):
    path = path.resolve(strict=True)
    for part in (path, *path.parents):
        info = part.stat()
        if info.st_uid != 0 or info.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise ValueError(f'untrusted root-owned path: {part}')


def main():
    for path in (ROOT, Path(__file__), FILTER, CLAUDE, ROOT / 'pins.json',
                 ROOT / 'run.mjs', ROOT / 'seccomp-canary.py',
                 Path('/usr/local/bin/node'), Path('/usr/bin/python3'),
                 ROOT / 'sandbox.json', Path('/etc/claude-code/managed-settings.json'),
                 Path('/etc/claude-code/managed-mcp.json')):
        trusted(path)
    # An empty enabledPlugins map is not a wildcard deny. Refuse a pre-existing
    # install rather than assume marketplace install policy unloads its LSP.
    plugins = Path('/home/assistant/.claude/plugins/installed_plugins.json')
    if plugins.exists() and json.loads(plugins.read_text()).get('plugins'):
        raise ValueError('central session must have no installed plugins')
    if not os.access(FILTER, os.X_OK):
        raise ValueError('seccomp helper missing or not executable')
    expected = json.loads((ROOT / 'pins.json').read_text())['seccomp_x64_sha256']
    if hashlib.sha256(FILTER.read_bytes()).hexdigest() != expected:
        raise ValueError('seccomp helper hash mismatch')
    os.chdir('/home/assistant/work')
    # Do not merely test that a file exists. Require the real sandbox to execute
    # a canary and return EPERM for both socket families, before Claude starts.
    probe = subprocess.run(
        ['/usr/local/bin/node', str(ROOT / 'run.mjs'),
         '/usr/bin/python3 -I /opt/aresos-control/seccomp-canary.py'],
        capture_output=True, text=True, timeout=45, close_fds=True)
    if probe.returncode or probe.stdout.strip() != 'SECCOMP_CANARY_OK':
        raise ValueError('effective seccomp canary failed: ' + probe.stderr[-1500:])
    os.execve(str(CLAUDE), [str(CLAUDE), '--setting-sources', ''], dict(os.environ))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print('REFUSE: ' + str(error), file=sys.stderr)
        sys.exit(78)
