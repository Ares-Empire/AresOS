"""Allow only bounded, scanned files into the public hosted bench artifact."""
import os
import pathlib
import re
import stat
import sys

MAX_TOTAL = 179_999_999
MAX_TEXT = 1024 * 1024
MAX_SHOT = 8 * 1024 * 1024
NUMBERED = re.compile(r'0(?:0[1-9]|[12][0-9]|3[0-2])\.(?:png|journal\.txt)')
TOKEN = re.compile(
    rb'(?i)(?:gh[pousr]_[a-z0-9]{20,}|github_pat_[a-z0-9_]{20,}|glpat-[a-z0-9_-]{20,}'
    rb'|(?:AKIA|ASIA)[A-Z0-9]{16}|xox[baprs]-[a-z0-9-]{12,}|sk-(?:proj-)?[a-z0-9_-]{20,}'
    rb'|AIza[a-z0-9_-]{35}|eyJ[a-z0-9_-]{8,}\.[a-z0-9_-]{10,}\.[a-z0-9_-]{10,}'
    rb'|-----BEGIN [A-Z ]*PRIVATE KEY-----|\bbearer[ \t]+[a-z0-9._=+/-]{12,}'
    rb'|\b(?:aresos_)?(?:nonce|password|api[_ -]?key|(?:access|view|launch|refresh)[_ -]?(?:token|nonce))'
    rb'["\']?\s*[:=]\s*["\']?[a-z0-9_./=+-]{12,})'
    # The supervisor uses token_urlsafe(24), and the bench view uses token_urlsafe(32).
    rb'|(?<![a-zA-Z0-9_-])(?:[a-zA-Z0-9_-]{32}|[a-zA-Z0-9_-]{43})(?![a-zA-Z0-9_-])'
)


def scan(folder):
    if folder.resolve() != folder.absolute() or not stat.S_ISDIR(folder.lstat().st_mode):
        raise ValueError('Bench evidence directory must be a real directory')
    count = total = 0
    has_run = False
    for path in folder.iterdir():
        name = path.name
        if name not in {'run.json', 'results.txt'} and not NUMBERED.fullmatch(name):
            raise ValueError('Unexpected bench evidence path')
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError('Bench evidence must contain standalone regular files')
        limit = MAX_SHOT if name.endswith('.png') else MAX_TEXT
        if info.st_size > limit or total + info.st_size > MAX_TOTAL:
            raise ValueError('Bench evidence exceeds size cap')
        with path.open('rb') as stream:
            data = stream.read(limit + 1)
        if len(data) != info.st_size:
            raise ValueError('Bench evidence changed during scan')
        if TOKEN.search(data):
            raise ValueError('Token-shaped data in bench evidence')
        if name.endswith('.png'):
            if not data.startswith(b'\x89PNG\r\n\x1a\n'):
                raise ValueError('Bench screenshot is not a PNG')
        else:
            data.decode('utf-8')
        count += 1
        total += len(data)
        has_run |= name == 'run.json'
    if not has_run:
        raise ValueError('Bench run record missing')
    return count, total


if __name__ == '__main__':
    try:
        count, size = scan(pathlib.Path(sys.argv[1]))
    except (OSError, ValueError):
        raise SystemExit('Bench evidence refused (unexpected, oversized, unreadable or token-shaped data)') from None
    print(f'Bench evidence safe: {count} files, {size} bytes')
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as output:
        print('safe=true', file=output)
