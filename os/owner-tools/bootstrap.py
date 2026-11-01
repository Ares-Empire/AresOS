"""Generate the literal trusted command; this module never runs on the USB."""
import re
import shlex


def verification(fingerprint):
    assert re.fullmatch('[0-9a-f]{64}', fingerprint)
    # No stick code, parser or PATH is used before the pinned system checks.
    # The private tmpfs copy stays until reboot; only our private mount is
    # unmounted on exit, so cleanup cannot recursively delete another path.
    body = '\n'.join([
        'set -euo pipefail',
        'export PATH=/usr/sbin:/usr/bin:/sbin:/bin; umask 077',
        'trap "echo STOP bootstrap: verification or install refused" ERR',
        'p=$(mktemp -d /run/ares-bootstrap.XXXXXX); mkdir "$p/m"',
        'mount -o ro,nodev,nosuid,noexec LABEL=ARESTOOLS "$p/m"; trap "umount $p/m" EXIT',
        'cd "$p"; cp -R --no-preserve=mode,ownership m/ares-tools .; test ! -L ares-tools; cd ares-tools',
        'test -z "$(find . ! -type d ! -type f -print -quit)"',
        'echo "' + fingerprint + '  SHA256SUMS" | sha256sum -c --strict',
        'cmp -s \\',
        '  <(find . -type f -printf "%P\\n" | sort) \\',
        '  <({ cut -c67- SHA256SUMS; echo SHA256SUMS; } | sort)',
        'sha256sum -c --strict SHA256SUMS'])
    return body


def command(fingerprint):
    body = verification(fingerprint) + '\nbash ./at install'
    result = 'sudo bash -c ' + shlex.quote(body)
    assert all(len(line) < 120 for line in result.splitlines())
    return result
