"""Recognise the CI journal follower's readiness record on the serial console.

checks.py starts `journalctl --follow --output=short-monotonic` on ttyS0 and
logs the token with `logger --tag aresos-ci`. Each forwarded record is one line
such as `[   73.458055] bazzite aresos-ci[2795]: ARESOS_JOURNAL_READY`, with
journalctl's colour codes around the message. Those lines look like kernel
records, so serial_console.serial_search strips them (package 21 review fixes 3).
"""
import re

TOKEN = 'ARESOS_JOURNAL_READY'
# A complete follower record: line start, monotonic timestamp, host, the
# aresos-ci tag with its PID, the message, and the terminating newline.
RECORD = re.compile(r'^\[\s*\d+\.\d+\] \S+ aresos-ci\[\d+\]: ([^\r\n]*)\r?\n', re.M)
COLOUR = re.compile(r'\x1b\[[0-9;:]*m')


def follower_ready(transcript):
    """True only for a complete record whose message is exactly the token.

    A prefix or suffix (`FAILED ARESOS_JOURNAL_READY`, `ARESOS_JOURNAL_READY_NOT`),
    another tag, or a record still missing its newline never counts.
    """
    return any(COLOUR.sub('', message) == TOKEN for message in RECORD.findall(transcript))
