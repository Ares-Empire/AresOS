import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

policy = json.loads(Path('/etc/claude-code/managed-settings.json').read_text())
if sys.argv[1] == 'assistant':
    assert policy['permissions']['defaultMode'] == 'default'
    for name in ['transcript.jsonl', '.credentials.json']:
        path = Path('/home/assistant/.claude') / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('SYNTHETIC_ASSISTANT_ONLY\n')
        os.chown(path, 10001, 10001)
        path.chmod(0o600)
    Path('/run/aresos-tools').mkdir(exist_ok=True)
    listener = socket.socket(socket.AF_UNIX)
    listener.bind('/run/aresos-tools/act.sock')
    listener.listen()
    print('ASSISTANT_READY separate_home transcripts credentials socket policy=default', flush=True)
    time.sleep(120)
else:
    assert os.getuid() == 10003
    assert policy['permissions']['defaultMode'] == 'plan'
    for path in ['/home/assistant/.claude/transcript.jsonl', '/home/assistant/.claude/.credentials.json']:
        assert not Path(path).exists(), path
    for name in ['act', 'admin', 'chrome']:
        address = '/run/aresos-tools/' + name + '.sock'
        assert not Path(address).exists(), address
        try:
            socket.socket(socket.AF_UNIX).connect(address)
        except OSError:
            pass
        else:
            raise AssertionError(address)
    home = Path('/home/coder/.claude')
    home.mkdir(exist_ok=True)
    (home / 'transcript.jsonl').write_text('SYNTHETIC_CODER_ONLY\n')
    (home / '.credentials.json').write_text('{}\n')
    result = subprocess.run(['/usr/local/bin/claude', 'mcp', 'list'], capture_output=True, text=True, timeout=45)
    print(result.stdout + result.stderr)
    assert result.returncode == 0 and 'No MCP servers' in result.stdout + result.stderr
    print('ISOLATION_OK uid=10003 policy=plan no_assistant_home no_transcripts no_credentials no_tool_sockets no_app_mcp')
