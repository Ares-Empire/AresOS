import base64,json,pathlib,sys
sys.path.insert(0,'os/tests')
from serial_pty import Fixture,ROOT
from serial_console import encode_command
retained=json.loads((ROOT/'os/tests/fixtures/owner-console/14za-login-command.json').read_text())
with Fixture(retained['before']) as f:
    adapter=f.root/'python-adapter.py'
    adapter.write_text(adapter.read_text().replace('exec(compile(source,',"(root/'reader-started').write_text('started')\nexec(compile(source,"))
    f.guest.send(encode_command(retained['script']))
    try:f.guest.wait(r'\r?\nARESOS_CMD_DONE:(\d+)\r?\n',timeout=.5)
    except TimeoutError:pass
    result=dict(kind='real local Bash/PTY; no VM; old reader left waiting with no new record',
        original_script_unchanged=True,reader_started=(f.root/'reader-started').exists(),
        normal_received_command_ps2_count=f.guest.transcript.count('> '),
        retained_ps2_count=base64.b64decode(retained['retained_transcript']['base64']).count(b'> '),
        completion_observed='ARESOS_CMD_DONE:' in f.guest.transcript,
        conclusion='Continuation prompts occur even when the complete old command executes; retained PS2 alone cannot prove an open heredoc')
    assert result['reader_started'] and not result['completion_observed']
    (ROOT/'.work/14/14zb-observations.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
