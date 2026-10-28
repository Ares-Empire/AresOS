"""Bounded public-script transfer; credentials belong to the physical prompt.

Only tiny control lines cross the UART at once. A lost/corrupt acknowledgement
stops the transfer; it never retries a write or starts an unverified script.
"""
import base64
import hashlib
import re
import secrets
import shlex
import time

from serial_console import encode_command, strip_kernel_lines

INLINE_BYTES = 256
CHUNK_BYTES = 96
MAX_CONTROL_LINE = 512
ACK_TIMEOUT = 10
TRANSFER_TIMEOUT = 120
STAGE_ROOT = '/run'


class Ack:
    serial_ack = True
    record = re.compile(r'ARESOS_ACK:(?P<nonce>[^:\r\n]+):(?P<phase>[^:\r\n]+):'
        r'(?P<index>[^:\r\n]+):(?P<status>[^:\r\n]+):END')

    def __init__(self, nonce, phase, index):
        assert re.fullmatch('[0-9a-f]{16}', nonce) and re.fullmatch('[a-z]+', phase) and index >= 0
        self.nonce, self.phase, self.index = nonce, phase, index

    def __str__(self):
        return f'ARESOS_ACK:{self.nonce}:{self.phase}:{self.index}:<status>:END'

    def search(self, transcript):
        clean = strip_kernel_lines(transcript)
        matches = list(self.record.finditer(clean))
        assert clean.count('ARESOS_ACK:') <= 1 and len(matches) <= 1, 'Duplicate serial ACK; STOP'
        if not matches:
            return None
        match, = matches
        assert (match['nonce'], match['phase'], match['index']) == (self.nonce, self.phase, str(self.index)), 'Mismatched or out-of-order serial ACK; STOP'
        assert re.fullmatch(r'0|[1-9][0-9]{0,2}', match['status']) and int(match['status']) <= 255, 'Malformed serial ACK status; STOP'
        return match


def acknowledged(command, nonce, phase, index):
    Ack(nonce, phase, index)
    line = ("{ " + command + "; _ares_status=$?; printf '\\nARESOS_ACK:%s:%s:%s:%s:END\\n' "
        + nonce + ' ' + phase + ' ' + str(index) + ' "$_ares_status"; }\n')
    assert len(line.encode()) <= MAX_CONTROL_LINE, 'Serial control line too large'
    return line


def plan(script, nonce, root=STAGE_ROOT):
    """Pure source generation, also used by syntax tests and the local PTY."""
    assert re.fullmatch('[0-9a-f]{16}', nonce)
    raw = script.encode()
    check_root = ('_ares_root=' + shlex.quote(root)
        + ' && test "$(id -u)" = 0 && test -d "$_ares_root" && test ! -L "$_ares_root"'
        + ' && test "$(findmnt -n -o FSTYPE -T "$_ares_root")" = tmpfs')
    setup = ('_ares_stage="$_ares_root/ares-serial-' + nonce + '"'
        + ' && mkdir -m 700 -- "$_ares_stage"'
        + ' && (umask 077; set -C; : > "$_ares_stage/script")')
    steps = [('root', check_root), ('create', setup)]
    for offset in range(0, len(raw), CHUNK_BYTES):
        chunk = base64.b64encode(raw[offset:offset + CHUNK_BYTES]).decode()
        steps.append(('chunk', 'test "$(wc -c < "$_ares_stage/script")" = ' + str(offset)
            + ' && printf %s ' + shlex.quote(chunk) + ' | base64 -d >> "$_ares_stage/script"'))
    digest = hashlib.sha256(raw).hexdigest()
    steps.append(('integrity', 'test ! -L "$_ares_stage/script"'
        + ' && test "$(stat -c %u:%a "$_ares_stage")" = 0:700'
        + ' && test "$(stat -c %u:%a "$_ares_stage/script")" = 0:600'
        + ' && printf "%s  %s\\n" ' + digest + ' "$_ares_stage/script" | sha256sum -c --status'))
    steps.append(('syntax', '(umask 077; bash -n "$_ares_stage/script" > "$_ares_stage/syntax" 2>&1)'
        + ' && test ! -s "$_ares_stage/syntax"'))
    # All of this group is parsed before bash can read a tty. No future serial
    # command is queued while the script runs. The input file contains no secret.
    run = ('{ bash "$_ares_stage/script" </dev/null; _ares_status=$?; '
        'if rm -f -- "$_ares_stage/script" "$_ares_stage/syntax" && rmdir -- "$_ares_stage"; '
        'then :; else _ares_status=125; fi; '
        'printf "\\nARESOS_CMD_%s:%s\\n" DONE "$_ares_status"; }\n')
    assert len(run.encode()) <= MAX_CONTROL_LINE
    return [(phase, acknowledged(command, nonce, phase, i)) for i, (phase, command) in enumerate(steps)], run


def roundtrip(send, wait, command, nonce, index, timeout, phase='resync'):
    send(acknowledged(command, nonce, phase, index))
    pattern = Ack(nonce, phase, index)
    output = wait(pattern, timeout)
    assert int(pattern.search(output)['status']) == 0, 'Serial control step refused'
    return output


def execute(send, wait, script, timeout, record, known_secrets=()):
    # Refuse before hashing, evidence, serial writes or tmpfs allocation.
    assert not any(value and value in script for value in known_secrets), 'Secret-bearing serial script refused; use the hidden physical prompt'
    assert '\0' not in script, 'NUL in serial script refused before transport'
    if len(script.encode()) <= INLINE_BYTES:
        send(encode_command(script))
        return wait(r'\r?\nARESOS_CMD_DONE:(\d+)\r?\n', timeout)
    nonce = secrets.token_hex(8)
    steps, run = plan(script, nonce, STAGE_ROOT)
    deadline = time.monotonic() + TRANSFER_TIMEOUT
    summary = dict(sha256=hashlib.sha256(script.encode()).hexdigest(), bytes=len(script.encode()),
        chunks=sum(phase == 'chunk' for phase, _ in steps), staged=True, verified=False,
        transfer_timeout=TRANSFER_TIMEOUT, execution_timeout=timeout, steps=[])
    record(dict(summary))
    for index, (phase, line) in enumerate(steps):
        remaining = deadline - time.monotonic()
        assert remaining > 0, 'Serial transfer deadline'
        send(line)
        pattern = Ack(nonce, phase, index)
        try:
            output = wait(pattern, min(ACK_TIMEOUT, remaining))
            code = int(pattern.search(output)['status'])
        except BaseException as error:
            summary['steps'].append(dict(index=index, phase=phase,
                status='invalid acknowledgement; STOP; no retry' if isinstance(error, AssertionError) else 'no acknowledgement; STOP; no retry',
                failure_kind=type(error).__name__))
            record(dict(summary))
            raise
        summary['steps'].append(dict(index=index, phase=phase, status='passed' if code == 0 else 'refused'))
        record(dict(summary))
        if code:
            # Only an ACK proves that the shell parsed this step. Lost ACKs
            # never cause a speculative cleanup command into a possibly busy tty.
            if phase in ('chunk', 'integrity', 'syntax'):
                roundtrip(send, wait, 'rm -f -- "$_ares_stage/script" "$_ares_stage/syntax"'
                    ' && rmdir -- "$_ares_stage"', nonce, len(steps), ACK_TIMEOUT, phase='cleanup')
                summary['cleanup'] = 'completed after acknowledged refusal'
                record(dict(summary))
            raise AssertionError('Serial staged ' + phase + ' refused; script not executed')
    summary['verified'] = True
    record(dict(summary))
    send(run)
    return wait(r'\r?\nARESOS_CMD_DONE:(\d+)\r?\n', timeout)
