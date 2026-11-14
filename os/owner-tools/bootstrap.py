"""Generate the literal trusted commands; this module never runs on the USB.

Two start blocks, one per source of the reviewed bundle, that differ in exactly
their source lines (brief 22c, stage 1b, addition 3):

- stick: the labelled tools USB, mounted read-only (the emergency route);
- folder: a local folder that Claude fills from the repository checkout at the
  announced commit, so a routine tools update needs neither the stick nor Windows.
  The folder may be writable by ares: only its verified private copy is used.

Everything after the source lines is the same for both: system tools only, a copy
into a fresh root-only folder under /run, no links, no special files, the literal
fingerprint checked against SHA256SUMS, every file checked, then at install.
"""
import re
import shlex

FOLDER = '/var/home/ares/ares-tools'
SOURCES = ('stick', 'folder')


def source_lines(source):
    """Where the bundle comes from: each source's lines end in its private copy's root, ares-tools."""
    if source == 'stick':
        return ['p=$(mktemp -d /run/ares-bootstrap.XXXXXX); mkdir "$p/m"',
                'mount -o ro,nodev,nosuid,noexec LABEL=ARESTOOLS "$p/m"; trap "umount $p/m" EXIT',
                'cd "$p"; cp -R --no-preserve=mode,ownership m/ares-tools .; test ! -L ares-tools; cd ares-tools']
    if source == 'folder':
        return ['p=$(mktemp -d /run/ares-bootstrap.XXXXXX)',
                'cd "$p"; cp -R --no-preserve=mode,ownership ' + FOLDER + ' .; test ! -L ares-tools; cd ares-tools']
    raise ValueError('Unknown bundle source: ' + str(source))


def verification(fingerprint, source='stick'):
    assert re.fullmatch('[0-9a-f]{64}', fingerprint)
    # No bundle code, parser or PATH is used before the pinned system checks.
    # The private tmpfs copy stays until reboot; only our private mount is
    # unmounted on exit, so cleanup cannot recursively delete another path.
    # cp -R copies a link or a special file as itself, never what it names; the
    # checks below refuse both before any bundle file is read.
    body = '\n'.join([
        'set -euo pipefail',
        'export PATH=/usr/sbin:/usr/bin:/sbin:/bin; umask 077',
        'trap "echo STOP bootstrap: verification or install refused" ERR',
        *source_lines(source),
        'test -z "$(find . ! -type d ! -type f -print -quit)"',
        'echo "' + fingerprint + '  SHA256SUMS" | sha256sum -c --strict',
        'cmp -s \\',
        '  <(find . -type f -printf "%P\\n" | sort) \\',
        '  <({ cut -c67- SHA256SUMS; echo SHA256SUMS; } | sort)',
        'sha256sum -c --strict SHA256SUMS'])
    return body


def command(fingerprint, source='stick'):
    body = verification(fingerprint, source) + '\nbash ./at install'
    result = 'sudo bash -c ' + shlex.quote(body)
    assert all(len(line) < 120 for line in result.splitlines())
    return result
