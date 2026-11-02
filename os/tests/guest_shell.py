"""Parse stand-in guest scripts and their real serial wrapper without execution."""
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'ci'))
from serial_console import encode_command
import serial_transport


def syntax(name, source):
    layers = [('guest', source), ('serial', encode_command(source))]
    if len(source.encode()) > serial_transport.INLINE_BYTES:
        steps, run = serial_transport.plan(source, '0123456789abcdef')
        layers.append(('staged-control', ''.join(line for _, line in steps) + run))
    for layer, text in layers:
        # Walks stub subprocess.run for host operations; parsing must still use
        # real Bash rather than accidentally passing through that stand-in.
        process = subprocess.Popen(['bash', '--noprofile', '--norc', '-n'],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True)
        try:
            stdout, stderr = process.communicate(text, timeout=15)
        except BaseException:
            process.kill()
            process.communicate()
            raise
        assert process.returncode == 0 and not stdout and not stderr, (
            name, layer, process.returncode, stdout, stderr)
