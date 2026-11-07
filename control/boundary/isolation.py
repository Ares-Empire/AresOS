import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

sys.path.insert(0, '/opt/aresos-control')
from boundary_assertions import validate_managed_mcp

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
    names = validate_managed_mcp(result, require_failed=True)
    print('MANAGED_MCP_OK user=coder all_failed names=' + json.dumps(names), flush=True)
    # This flag is rejected before auth by the assistant's managed policy.
    # In the coding container it reaches the signed-out auth preflight instead,
    # demonstrating that the native CLI actually reads the distinct policy.
    policy_probe = subprocess.run(
        ['/usr/local/bin/claude', '--agents', '{}', '-p', 'do not call a model'],
        capture_output=True, text=True, timeout=45)
    output = policy_probe.stdout + policy_probe.stderr
    print('CODING_POLICY_PROBE exit=' + str(policy_probe.returncode) + '\n' + output)
    assert policy_probe.returncode != 0 and 'Not logged in' in output
    assert 'disableSideloadFlags' not in output
    print('ISOLATION_OK uid=10003 policy=plan no_assistant_home no_transcripts no_credentials no_tool_sockets no_connected_app_mcp')
