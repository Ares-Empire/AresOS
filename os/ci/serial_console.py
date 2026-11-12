"""Answer the terminal queries used by the inherited interactive login banner."""
import base64
import hashlib
import re


class IncompleteKernelLine(ValueError):
    pass


def strip_kernel_lines(transcript):
    """Filter complete printk records without guessing missing bytes.

    A record can interrupt any userspace byte. Keep the original transcript
    separately; a partial record must wait for its newline, never grant input.
    """
    clean = re.sub(r'\[\s*\d+\.\d+\] [^\r\n]*\r?\n', '', transcript)
    if re.search(r'\[\s*\d+\.\d+\] [^\r\n]*\r?\Z', clean):
        raise IncompleteKernelLine('Incomplete kernel console record')
    return clean


def serial_search(pattern, transcript):
    clean = strip_kernel_lines(transcript)
    if hasattr(pattern, 'serial_ack'):
        return clean, pattern.search(clean)
    assert 'ARESOS_ACK:' not in clean, 'Unexpected or duplicate serial ACK; STOP'
    return clean, re.search(pattern, clean)


def command_status(transcript):
    clean = strip_kernel_lines(transcript)
    matches = re.findall(r'\r?\nARESOS_CMD_DONE:(0|[1-9][0-9]{0,2})\r?\n', clean)
    assert len(matches) == 1 and int(matches[0]) <= 255, 'Missing, duplicate or malformed command completion; STOP'
    return int(matches[0])


def encode_command(script):
    encoded = base64.b64encode(script.encode()).decode()
    lines = '\n'.join(encoded[n:n + 1024] for n in range(0, len(encoded), 1024))
    # Parse completion printing before execution: a guest command may read from
    # /dev/tty and consume anything queued after the heredoc delimiter.
    header = "{ base64 -d <<'ARESOS_SCRIPT' | bash; printf '\\nARESOS_CMD_%s:%s\\n' DONE $?; }\n"
    return header + lines + '\nARESOS_SCRIPT\n'


def decode_export(transcript):
    # Kernel printk shares the serial UART and can interrupt a base64 line.
    # Remove only recognizable kernel records; the guest checksum guards every
    # decoded byte against missing data or any other console interference.
    clean = strip_kernel_lines(transcript)
    frame = re.search(r'\r?\nARESOS_EXPORT_START\r?\n(.*?)\r?\nARESOS_EXPORT_END\r?\n'
                      r'ARESOS_EXPORT_SHA256[ \t]+([0-9a-f]{64})[ \t]+[^\r\n]+\r?\n', clean, re.S)
    if frame is None:
        raise ValueError('Missing complete checksum-framed guest export')
    raw = base64.b64decode(''.join(frame.group(1).split()), validate=True)
    if hashlib.sha256(raw).hexdigest() != frame.group(2):
        raise ValueError('Guest export checksum mismatch')
    return raw


class TerminalReplies:
    # xterm DSR, OSC dynamic-color and XTGETTCAP queries can span socket reads.
    # systemd 259 asks the serial console for its terminfo name with XTGETTCAP
    # (DCS + q 6E616D65 ST); "0+r" is its own "not supported" answer, so it never
    # waits for one (rehearsal runs 6 and 12 stalled right after that probe).
    query = re.compile(rb'\x1b\[6n|\x1b\](10|11|12);\?(?:\x07|\x1b\\)|(\x1bP\+q[0-9A-Fa-f;]*\x1b\\)')

    def __init__(self):
        self.pending = b''
        self.counts = {}

    def feed(self, data):
        self.pending += data
        replies = []
        consumed = 0
        for match in self.query.finditer(self.pending):
            color = match.group(1)
            if match.group(2) is not None:
                name = 'terminfo'
                replies.append(b'\x1bP0+r\x1b\\')
            elif color is None:
                name = 'cursor-position'
                replies.append(b'\x1b[24;80R')
            else:
                name = f'color-{color.decode()}'
                rgb = b'0000/0000/0000' if color == b'11' else b'ffff/ffff/ffff'
                replies.append(b'\x1b]' + color + b';rgb:' + rgb + b'\x1b\\')
            self.counts[name] = self.counts.get(name, 0) + 1
            consumed = match.end()
        self.pending = self.pending[consumed:][-64:]
        return b''.join(replies)
