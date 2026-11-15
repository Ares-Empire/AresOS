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

Brief 22d adds the routine route: Claude runs the lines, he approves each root line
by typing his password into the desktop's window (decisions 2, 3 and 5):

- tools_folder: Claude's line as ares, no window. Its only input is the announced
  commit, added after its last word. It refuses unless that commit is on origin/main
  and this checkout's os/owner-tools equals it (so the root line Claude copies from
  commands.json is the commit's), then fills the folder with git archive of that
  commit's payload and checks the payload's fingerprint against the pinned one.
- routine lines: SUDO_ASKPASS=/usr/bin/ksshaskpass /usr/bin/sudo -k -A -p '<label>'
  bash -c '<script>'. One window per go: the tools-only line is the folder block,
  then the new tools' check and title in the same root shell, stopping at the first
  STOP. The label names the tools' first 8 hex and the action.
"""
import re
import shlex

FOLDER = '/var/home/ares/ares-tools'
SOURCES = ('stick', 'folder')
# Claude's checkout on the laptop (as ares); the folder line reads only its git objects
# and compares its os/owner-tools with the announced commit.
CHECKOUT = '/var/home/ares/AresOS'
# Absolute: ~/.local/bin is first on his PATH (brief 22d, decision 2).
SUDO = '/usr/bin/sudo'
ASKPASS = '/usr/bin/ksshaskpass'
INSTALLED = '/var/lib/ares/at'
# The action each routine line's window names, after "AresOS owner tools <8 hex>: ".
ACTIONS = {'tools-routine': 'install these tools, then check and title',
           'export-routine': 'export the records'}


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


def label(fingerprint, action):
    """The line inside the password window: the tools' first 8 hex, then the action.

    ksshaskpass remembers an answer only for prompts that match its SSH and git
    patterns; this shape matches none of them (test_owner_bootstrap holds it). sudo
    expands % in a prompt and a quote would change the line's quoting, so the label
    keeps to letters, digits, spaces, commas and its one colon.
    """
    assert re.fullmatch('[0-9a-f]{64}', fingerprint)
    text = 'AresOS owner tools ' + fingerprint[:8] + ': ' + action
    assert re.fullmatch('[A-Za-z0-9 ,]+: [A-Za-z0-9 ,]+', text)
    return text


def routine(fingerprint, action, script):
    """One routine line: a fresh password in the window, then script in one root shell."""
    assert "'" not in script
    return ('SUDO_ASKPASS=' + ASKPASS + ' ' + SUDO + ' -k -A -p ' + shlex.quote(label(fingerprint, action))
            + ' bash -c ' + shlex.quote(script))


def tools_routine(fingerprint):
    """The tools-only box in one window: the folder block, then the new tools' check and title."""
    body = '\n'.join([verification(fingerprint, 'folder'), 'bash ./at install',
                      # From here the new tools are installed: a STOP is theirs, not the install's.
                      'trap "echo STOP after install: check or title refused" ERR',
                      INSTALLED + ' check', INSTALLED + ' title'])
    return routine(fingerprint, ACTIONS['tools-routine'], body)


def export_routine(fingerprint):
    """After a STOP on the routine route: the installed tools' export, without the stick."""
    return routine(fingerprint, ACTIONS['export-routine'], INSTALLED + ' export')


def tools_folder(fingerprint):
    """Claude's line as ares: the announced commit's payload into a fresh folder, or a STOP.

    Chained under set -e, so any failure stops before the folder changes or the
    window opens. git archive reads the commit, never the working tree.
    """
    assert re.fullmatch('[0-9a-f]{64}', fingerprint)
    stop = 'echo "STOP tools folder: '
    script = '\n'.join([
        'set -euo pipefail',
        'export PATH=/usr/bin:/bin',
        'trap "echo STOP tools folder: refused, nothing was installed" ERR',
        'c=${1:-}; [[ $c =~ ^[0-9a-f]{40}$ ]] || { ' + stop + 'give the full commit hash"; exit 1; }',
        'cd ' + CHECKOUT,
        'git fetch --quiet origin +refs/heads/main:refs/remotes/origin/main',
        'git merge-base --is-ancestor "$c" refs/remotes/origin/main || { ' + stop + '$c is not on origin/main"; exit 1; }',
        'git diff --quiet "$c" -- os/owner-tools || { ' + stop + 'this checkout differs from $c in os/owner-tools"; exit 1; }',
        'rm -rf ' + FOLDER + '; mkdir ' + FOLDER,
        'git archive "$c":os/owner-tools/payload | tar -x -C ' + FOLDER,
        'cd ' + FOLDER + '; echo "' + fingerprint + '  SHA256SUMS" | sha256sum -c --strict'])
    assert "'" not in script
    return '/usr/bin/bash -c ' + shlex.quote(script) + ' tools-folder'


def lines(fingerprint):
    """Every generated line commands.json holds besides the stick block, by its name there."""
    return {'tools-folder': tools_folder(fingerprint), 'tools-routine': tools_routine(fingerprint),
            'export-routine': export_routine(fingerprint)}
