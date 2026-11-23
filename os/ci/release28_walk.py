"""Package 42, step 3: release 28's rehearsal mode `release-28` (briefs/42-release-28.md, B), in a VM.

The owner's route to release 28 from the laptop's state, in package 22c's harness (os/ci/owner_vm.py) with
package 22d's dialog driver (os/ci/tools_local.Walk, with its step 6d safeguards):

  0. The laptop's state (the lead's decision of 2026-11-17, the first builder's JUDGMENT-CALL): package 27's
     route to release 27 with tools version 2 (owner_vm.laptop_update; release 27's facts from fixed sources:
     version 2's own bundle at TOOLS_V2_COMMIT and os/manifest/releases/27.json, never release.json), his one-time
     administrator password and his sudo; then 22d's folder and routine lines at the stand-in for 634e1237, so
     the window installs tools version 4 (dcbc375f) as the laptop's session does. The lead confirms version 4 on
     the laptop after the owner's 22d session.
  1. B.1, from Claude's terminal: the folder and routine lines at the stand-in announced commit. Before the
     password, the 8 characters of the window's label equal line 1 of the stand-in's docs/OWNER-TOOLS.md. Then
     `Tools updated from version 4 to 5`, PASS install, PASS check, PASS title; the receipt names version 4 to 5.
  2. B.2 (only while CHROME_RIDES): root writes the made-up sites list with tee, as the guide does, and records
     its SHA-256.
  3. B.3, on the console (tty3): `at update` (release 28 staged), `at title`, `at reboot`; the guide's start
     (F12, Bazzite: the harness's one-time Linux start); `at check` and `at title` confirm the update. On release
     28: package 21's rules, fc-match gives Space Grotesk as ares, package 31's Ares-Crown is labwc's theme, and
     its terminal PATH and runtime polkit grants are checked. Control's boot state and absence of login
     dependencies are checked here and again after forward.
     The lead's note (2026-11-16): with no `foot` of ares, `at check` STOPs with
     `Read failed: pgrep -u ares -x foot`; the SETUP screen's foot is ended first, then the Terminal app's foot
     is opened again (the guide's "open the Terminal app first").
  4. B.4: `at previous` to release 27, its start, `at check` (Return confirmed); then `at forward` to release
     28, its start, `at check` (Forward confirmed). The home screen's instance and apps.json survive the round
     trip. Last, 23d's game scope: a real JVM through the real wrapper runs in its scope with memory.high
     2684354560 (the check-build VM's method; it latches RECOVERY, so it runs at the very end).
  5. B.5: every start ends in package 11's audits (owner_vm.finish: the stand-in Windows disk and its boot
     entry byte-identical), the deployment list is checked at every start (stock pinned; only release 13 goes,
     at the update's shutdown, as package 22's JUDGMENT-CALL 1 allows), and the Windows markers at the end.

The stand-in origin (lead's decision 2, 2026-11-17): GitHub is not reachable from the VM, so the guest's origin
holds a stand-in for 634e1237 (its os/owner-tools tree, release.json and OWNER-TOOLS.md, byte-identical), then
a stand-in announced commit: version 4's code with tools_version 5 and release 28's record (announced()). The
walk records that commit's hash and the tree and blob hashes of os/owner-tools, os/manifest/release.json and
docs/OWNER-TOOLS.md. Step 5's real payload commit must hold the same os/owner-tools tree, release.json blob,
guide line 1 and full fingerprint (matches()). Only the verified unchanged v4 baseline may defer this comparison
in a local preparatory walk. The VM requires successful comparison before starting the route.

Release 28's record is a parameter (the image exists only after step 5): the CI mode reads
os/manifest/releases/28.json, which step 5 writes, and stops without it.
"""
import base64
import gzip
import hashlib
import json
import os
import pathlib
import shlex
import subprocess
import time

import tools_local

# Tools version 4 (package 22d, merged as 634e1237): the laptop's tools when release 28 comes (lead, 2026-11-17).
V4_COMMIT = '634e12378b68f77398f7c8b633fcea988a768acf'
TOOLS_V4 = 'dcbc375faa4b269bacaf316c5ddc24503b9773b2538bcd017065ce8e312597be'
V4_TREE = '73fb5929cddd36db91662bad7d83e5453b965ca6'
# Release 28's bundle: version 4's code with tools_version 5 and release 28's record (lead's decision 1).
TOOLS_VERSION = 5
IDENTITY = 'https://github.com/Ares-Empire/AresOS/.github/workflows/os-image.yml@refs/heads/pkg/42-release-28'
RECORD = 'os/manifest/releases/28.json'
R27_RECORD = 'os/manifest/releases/27.json'
# The paths of the announced commit that step 5's real commit must hold byte for byte (os/owner-tools as a
# tree), and the guide whose line 1 the owner compares (its other lines may change after the rehearsal).
BOUND = ('os/owner-tools', 'os/manifest/release.json')
GUIDE = 'docs/OWNER-TOOLS.md'
GENERATED = ('commands.json', 'history.json', 'payload/history.json', 'payload/release.json', 'payload/SHA256.json',
             'payload/SHA256SUMS')

# Part A is in release 28. The browser side and its excluded-sites list ride the release after.
CONTROL_RIDES = True
CHROME_RIDES = False
CONTROL_CHECKER = 'os/ci/control/release_checks.py'
CONTROL_CHECKS = ('service_user', 'unit', 'claude_code_files', 'folders', 'state_folders')
SITES = '/var/lib/aresos-control/chrome-excluded-sites.json'
SITES_LIST = '{"format":1,"hosts":["rehearsal.invalid"]}'
# Package 23d's soft memory target of the game scope (aresos-desktop's MEMORY_HIGH, 2560M).
MEMORY_HIGH = str(2560 * 1024 ** 2)
SPACE_GROTESK = '/usr/share/fonts/aresos/SpaceGrotesk-Variable.ttf'
THEME = 'Ares-Crown'
# Tools version 4's check reads his foot (owner.py:2016-2017); without one it stops with this line.
FOOT_STOP = 'Read failed: pgrep -u ares -x foot'
INSTANCE = '/var/home/ares/.local/share/PrismLauncher/instances/AresDesktop'
APPS = INSTANCE + '/minecraft/config/aresos/apps.json'
# Same schema and fields as AppsConfig's schema-4 fixture; a real pinned app and saved town placement.
APPS_CONFIG = dict(schemaVersion=4, baseline='2026-11-13', apps=[dict(id='terminal', name='Terminal',
    command=[], type='helper', system=dict(source='system', categories=['Utility']), look='minecraft:command_block',
    pinned=True, mine=True, names=['terminal'], place='S0R0')])
# Prism may update these accounting keys and Minecraft may create logs/crash reports on the next R28 start.
# Only their content/presence is allowed to change; existing entries must retain ownership and permissions.
MUTABLE_DIRS = ('minecraft/logs', 'minecraft/crash-reports')
MUTABLE_INI_KEYS = ('lastLaunchTime', 'lastTimePlayed', 'totalTimePlayed')
REQUIRED_INSTANCE = ('.aresos-managed.json', 'instance.cfg', 'mmc-pack.json', 'minecraft/options.txt',
                     'patches', 'libraries', 'minecraft/mods', 'minecraft/saves', 'minecraft/config/aresos/apps.json')
INSTANCE_LINKS = {'patches': '/usr/share/aresos/minecraft/patches',
                  'libraries': '/usr/share/aresos/minecraft/libraries',
                  'minecraft/mods': '/usr/share/aresos/minecraft/mods',
                  'minecraft/saves': '/var/home/ares/.local/share/aresos/worlds'}
# Synthetic VM-only save data: a gzip NBT-like level and a small region with an empty location/timestamp header.
WORLD = 'Release28Rehearsal'
WORLD_FILES = {'level.dat': gzip.compress(b'\x0a\x00\x00\x08\x00\x09LevelName\x00\x12Release28Rehearsal\x00', mtime=0).hex(),
               'region/r.0.0.mca': (bytes(8192) + b'AresOS release-28 synthetic region\n').hex()}
AS_ARES = ['runuser', '-u', 'ares', '--', 'env', '-i', 'HOME=/var/home/ares', 'XDG_RUNTIME_DIR=/run/user/1001',
           'PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin']


def git(*args, data=None, env=None, source='.'):
    return tools_local.git(source, *args, data=data, env=env)


def guide_line(fingerprint, version):
    return 'Owner tools version ' + str(version) + ': ' + fingerprint[:8]


def bootstrap_of(source='.'):
    """Version 4's own bootstrap.py, read from 634e1237 (the lines it generates are the tools' own)."""
    namespace = dict(__name__='owner_bootstrap_v4')
    exec(compile(git('show', V4_COMMIT + ':os/owner-tools/bootstrap.py', source=source), 'bootstrap.py@' + V4_COMMIT[:8], 'exec'),
         namespace)
    return namespace


def announced(record, source='.'):
    """The files of the announced commit that differ from 634e1237, from release 28's record (its bytes).

    Version 4's history gains release 28 (reference, signature identity, daily_wheel true) and tools_version 5;
    the payload's release.json and os/manifest/release.json are the record; the payload's manifests and
    commands.json are made again the way bundle.py --refresh and bootstrap.py make them; line 1 and the full
    fingerprint of docs/OWNER-TOOLS.md name the new tools. Returns dict(files={path: bytes}, fingerprint, version).
    """
    release = json.loads(record)
    reference = release['reference']
    assert reference.startswith('ghcr.io/ares-empire/aresos@sha256:') and len(reference.split('@sha256:')[1]) == 64, \
        'STOP: release 28 is not an org image digest'
    assert release['signature']['identity'] == IDENTITY and release.get('daily_wheel') is True, \
        "STOP: release 28's record does not name its own signature identity with the daily wheel"
    assert record.endswith(b'\n'), "STOP: release 28's record is not a written record"
    show = lambda path: git('show', V4_COMMIT + ':' + path, source=source)
    assert git('rev-parse', V4_COMMIT + ':os/owner-tools', source=source).decode().strip() == V4_TREE, 'STOP: 634e1237 is not version 4'
    assert hashlib.sha256(show('os/owner-tools/payload/SHA256SUMS')).hexdigest() == TOOLS_V4, 'STOP: 634e1237 is not dcbc375f'
    history = json.loads(show('os/owner-tools/history.json'))
    assert history['tools_version'] == 4 and reference not in [row['reference'] for row in history['releases']], \
        'STOP: version 4 already knows release 28'
    history = dict(tools_version=TOOLS_VERSION, releases=[*history['releases'], dict(
        reference=reference, identity=IDENTITY, daily_wheel=True)])
    raw_history = (json.dumps(history, indent=2) + '\n').encode()
    payload = {'history.json': raw_history, 'release.json': record}
    rows = [dict(sha256=hashlib.sha256(payload[row['path']] if row['path'] in payload else
                                       show('os/owner-tools/payload/' + row['path'])).hexdigest(), path=row['path'])
            for row in json.loads(show('os/owner-tools/payload/SHA256.json'))]
    assert {'history.json', 'release.json'} <= {row['path'] for row in rows}
    raw = (json.dumps(rows, indent=2) + '\n').encode()
    sums = (''.join(row['sha256'] + '  ' + row['path'] + '\n' for row in rows)
            + hashlib.sha256(raw).hexdigest() + '  SHA256.json\n').encode()
    fingerprint = hashlib.sha256(sums).hexdigest()
    bootstrap = bootstrap_of(source)
    commands = json.loads(show('os/owner-tools/commands.json'))
    assert commands['install'] == bootstrap['command'](TOOLS_V4), "STOP: 634e1237's commands are not version 4's"
    commands['install'] = bootstrap['command'](fingerprint)
    commands.update(bootstrap['lines'](fingerprint))
    guide = show(GUIDE).decode().split('\n')
    assert guide[0] == guide_line(TOOLS_V4, 4) and guide[2] == TOOLS_V4, "STOP: 634e1237's guide does not start with version 4"
    guide[0], guide[2] = guide_line(fingerprint, TOOLS_VERSION), fingerprint
    files = {'os/owner-tools/history.json': raw_history, 'os/owner-tools/payload/history.json': raw_history,
             'os/owner-tools/payload/release.json': record, 'os/owner-tools/payload/SHA256.json': raw,
             'os/owner-tools/payload/SHA256SUMS': sums,
             'os/owner-tools/commands.json': (json.dumps(commands, indent=2) + '\n').encode(),
             'os/manifest/release.json': record, GUIDE: '\n'.join(guide).encode()}
    assert sorted(path.removeprefix('os/owner-tools/') for path in files if path.startswith('os/owner-tools/')) == sorted(GENERATED)
    return dict(files=files, fingerprint=fingerprint, version=TOOLS_VERSION)


def put(repo, tree, parts, entry):
    """`tree` (None: empty) with entry (mode, kind, object) at the path `parts`, made with ls-tree and mktree only
    (the stand-in is a bare repository). A file replaced keeps its mode, which must be a plain file's."""
    rows = {}
    if tree:
        for line in git('ls-tree', tree, source=repo).decode().splitlines():
            meta, name = line.split('\t', 1)
            rows[name] = tuple(meta.split())
    head, *rest = parts
    if rest:
        rows[head] = ('040000', 'tree', put(repo, rows[head][2] if head in rows else None, rest, entry))
    else:
        assert head not in rows or rows[head][:2] == entry[:2], 'STOP: ' + '/'.join(parts) + ' changes its kind or mode'
        rows[head] = entry
    listing = ''.join(mode + ' ' + kind + ' ' + value + '\t' + name + '\n' for name, (mode, kind, value) in sorted(rows.items()))
    return git('mktree', data=listing.encode(), source=repo).decode().strip()


def tree_with(repo, root, files):
    """`root` with each of `files` written as a blob in its place. Returns (the new root, its bound and guide hashes)."""
    for path, data in sorted(files.items()):
        blob = git('hash-object', '-w', '--stdin', data=data, source=repo).decode().strip()
        root = put(repo, root, path.split('/'), ('100644', 'blob', blob))
    return root, {path: git('rev-parse', root + ':' + path, source=repo).decode().strip() for path in (*BOUND, GUIDE)}


def standin_origin(destination, record, source='.'):
    """A git bundle for the guest's stand-in origin: on `main` first a stand-in for 634e1237 (tag `version-4`),
    then the stand-in announced commit. Each holds os/owner-tools, os/manifest/release.json and
    docs/OWNER-TOOLS.md; the first holds 634e1237's (byte-identical trees and blobs), the second announced()'s.
    Returns dict(bundle, repository, commits={'v4', 'announced'}, hashes={...: {path: object}}, fingerprint)."""
    destination = pathlib.Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    made = announced(record, source)
    repo = destination / 'stand-in.git'
    subprocess.run(['git', 'init', '--quiet', '--bare', str(repo)], check=True)
    tops = [V4_COMMIT + ':' + path for path in (*BOUND, GUIDE)]
    listing = git('rev-list', '--objects', V4_COMMIT + ':os/owner-tools', source=source)
    objects = [line.split(b' ')[0] for line in listing.splitlines()]
    objects += [git('rev-parse', top, source=source).strip() for top in tops[1:]]
    git('index-pack', '--stdin', data=git('pack-objects', '--stdout', data=b''.join(o + b'\n' for o in objects), source=source),
        source=repo)
    # 634e1237's three paths, as the root of the stand-in's first commit.
    base_root = put(repo, None, ['os', 'owner-tools'], ('040000', 'tree', V4_TREE))
    for path, top in zip((BOUND[1], GUIDE), tops[1:]):
        base_root = put(repo, base_root, path.split('/'), ('100644', 'blob', git('rev-parse', top, source=source).decode().strip()))
    commits, hashes = {}, {}
    v4 = git('commit-tree', base_root, '-m', 'Stand-in for ' + V4_COMMIT + ': its os/owner-tools, release.json and OWNER-TOOLS.md',
             env=tools_local.STANDIN_ENV, source=repo).decode().strip()
    commits['v4'] = v4
    hashes['v4'] = {path: git('rev-parse', v4 + ':' + path, source=repo).decode().strip() for path in (*BOUND, GUIDE)}
    root, hashes['announced'] = tree_with(repo, base_root, made['files'])
    commits['announced'] = git('commit-tree', root, '-p', v4, '-m', 'Stand-in announced commit: tools version 5 for release 28',
                               env=tools_local.STANDIN_ENV, source=repo).decode().strip()
    git('update-ref', 'refs/heads/main', commits['announced'], source=repo)
    git('tag', 'version-4', v4, source=repo)
    bundle = destination / 'stand-in.bundle'
    git('bundle', 'create', str(bundle.resolve()), 'main', 'version-4', source=repo)
    for path in (*BOUND, GUIDE):
        assert hashes['v4'][path] == git('rev-parse', V4_COMMIT + ':' + path, source=source).decode().strip(), \
            'STOP: the stand-in for 634e1237 differs in ' + path
    sums = git('show', commits['announced'] + ':os/owner-tools/payload/SHA256SUMS', source=repo)
    assert hashlib.sha256(sums).hexdigest() == made['fingerprint'], 'STOP: the stand-in announced commit is not the new tools'
    return dict(bundle=bundle, repository=repo, commits=commits, hashes=hashes, fingerprint=made['fingerprint'],
                trees={key: value['os/owner-tools'] for key, value in hashes.items()}, version=made['version'])


def matches(commit, recorded, source='.'):
    """Compare the real tools tree, release blob, guide line 1 and full fingerprint. Other guide prose is free.
    recorded: the walk's `announced` row (bound hashes, fingerprint, version). Returns differing paths."""
    differ = []
    for path in BOUND:
        found = subprocess.run(['git', '-C', str(source), 'rev-parse', '--verify', '--quiet', commit + ':' + path],
                               capture_output=True, text=True)
        if found.returncode != 0 or found.stdout.strip() != recorded['bound'][path]:
            differ.append(path)
    try:
        lines = git('show', commit + ':' + GUIDE, source=source).decode().splitlines()
        if lines[0] != guide_line(recorded['fingerprint'], recorded['version']) or lines[2] != recorded['fingerprint']:
            differ.append(GUIDE)
    except (subprocess.CalledProcessError, IndexError, UnicodeDecodeError):
        differ.append(GUIDE)
    return differ


def real_commit(head, standin, source='.', *, allow_deferred=False):
    """Only the verified unchanged v4 baseline may defer, for a local preparatory walk. VM qualification
    requires equality with the real announced commit, including the guide's two fingerprint lines."""
    baseline = dict(bound=standin['hashes']['v4'], fingerprint=TOOLS_V4, version=4)
    if not matches(head, baseline, source):
        assert allow_deferred, 'STOP: final qualification requires a successful real-commit comparison; payload not cut'
        return dict(carries_release_28=False, head=head, equal=False, deferred=True)
    differ = matches(head, dict(bound=standin['hashes']['announced'], fingerprint=standin['fingerprint'],
                                version=standin['version']), source)
    assert not differ, 'STOP: this checkout differs from the rehearsed bundle in ' + ', '.join(differ)
    return dict(carries_release_28=True, head=head, equal=True)


class Walk(tools_local.Walk):
    """22d's dialog driver over this walk's stand-in origin: `main` at the stand-in for 634e1237 first."""

    def __init__(self, vm, guest, ares_password, standin):
        super().__init__(vm, guest, ares_password, standin, 'announced', standin['fingerprint'])
        self.compared = []

    def setup(self, stage):
        guest, data = self.guest, base64.b64encode(self.standin['bundle'].read_bytes()).decode()
        guest.command(stage + '-bundle-begin', 'set -e; rm -f /run/aresos-standin.b64; : > /run/aresos-standin.b64')
        size = 48000
        for index in range(0, len(data), size):
            guest.command(stage + '-bundle-' + str(index // size), 'set -e; printf %s ' + data[index:index + size] + ' >> /run/aresos-standin.b64')
        digest = hashlib.sha256(self.standin['bundle'].read_bytes()).hexdigest()
        first, checkout, origin = self.standin['commits']['v4'], self.bootstrap.CHECKOUT, tools_local.GUEST_ORIGIN
        ares = tools_local.AS_ARES
        guest.command(stage + '-origin', '\n'.join([
            'set -e', 'cd /var/home/ares', 'base64 -d /run/aresos-standin.b64 > /run/aresos-standin.bundle; rm /run/aresos-standin.b64',
            'test "$(sha256sum < /run/aresos-standin.bundle)" = ' + shlex.quote(digest + '  -'),
            'chmod 0644 /run/aresos-standin.bundle',
            ares + 'git clone --quiet --bare /run/aresos-standin.bundle ' + origin,
            ares + 'git -C ' + origin + ' update-ref refs/heads/main ' + first,
            ares + 'git -C ' + origin + ' symbolic-ref HEAD refs/heads/main',
            ares + 'git clone --quiet --branch main ' + origin + ' ' + checkout,
            'test "$(' + ares + 'git -C ' + checkout + ' rev-parse HEAD)" = ' + first,
            'test "$(' + ares + 'git -C ' + checkout + ' rev-parse HEAD:os/owner-tools)" = ' + self.standin['trees']['v4']]))
        self.keyrings = self.capture(stage + '-keyrings', tools_local.KEYRINGS)

    def compare(self, stage, key, action):
        """The owner's look at his phone: line 1 of OWNER-TOOLS.md at the announced commit names the 8
        characters the window will show (its label, which window() then requires of the helper)."""
        commit = self.standin['commits'][key]
        line = git('show', commit + ':' + GUIDE, source=self.standin['repository']).decode().split('\n')[0]
        fingerprint = TOOLS_V4 if key == 'v4' else self.standin['fingerprint']
        label = self.bootstrap.label(fingerprint, action)
        shown = label.removeprefix('AresOS owner tools ')[:8]
        assert line.endswith(': ' + shown) and line == guide_line(fingerprint, 4 if key == 'v4' else TOOLS_VERSION), \
            'STOP: the window would show ' + shown + ', OWNER-TOOLS.md line 1 says ' + line + '; nothing is typed'
        self.compared.append(dict(stage=stage, commit=commit, line_1=line, label_8=shown))
        tools_local.td_save(self.vm, stage + '-owner-tools-line-1', self.compared[-1])


# On release 28 in his session: the theme in the rc.xml the running labwc reads, fontconfig's Space Grotesk as ares,
# his terminals.
SESSION = r'''import json,os,pathlib,subprocess,xml.etree.ElementTree as ET
AS_ARES=@AS_ARES@
out={}
labwc=subprocess.run(['pgrep','-u','ares','-x','labwc'],capture_output=True,text=True).stdout.split()
out['labwc']=len(labwc)
# The configuration the running labwc reads: its --config-dir (aresos-session: /usr/share/aresos/labwc).
argv=pathlib.Path('/proc/'+labwc[0]+'/cmdline').read_bytes().split(b'\0')[:-1] if labwc else []
argv=[word.decode() for word in argv]
folder=argv[argv.index('--config-dir')+1] if '--config-dir' in argv else '/var/home/ares/.config/labwc'
rc=pathlib.Path(folder,'rc.xml')
out.update(labwc_argv=argv,rc=str(rc))
out['theme']=ET.parse(rc).getroot().findtext('theme/name') if rc.is_file() else None
out['themerc']=pathlib.Path('/usr/share/themes/'+str(out['theme'])+'/labwc/themerc').is_file()
fonts={}
for pattern in ('Space Grotesk','Space Grotesk:bold'):
    done=subprocess.run(AS_ARES+['/usr/bin/fc-match','-f','%{file}',pattern],capture_output=True,text=True)
    fonts[pattern]=done.stdout if done.returncode==0 else 'exit '+str(done.returncode)
out['fonts']=fonts
out['foot']=len(subprocess.run(['pgrep','-u','ares','-x','foot'],capture_output=True,text=True).stdout.split())
print(json.dumps(out))
'''

# The guide's "open the Terminal app": the hub's terminal (owner_vm.HUB_TERMINAL) in his labwc session, as ares.
# Its environment is the desktop supervisor's (`aresos-desktop session`, started by labwc's autostart), which the
# hub's programs inherit. labwc's own /proc environ never holds WAYLAND_DISPLAY: labwc sets it after it starts, so a
# foot started from that environment found no display and exited at once (rehearsal 6, run 44781321736). Like the
# hub (apps/terminal.json "working_directory": "~", aresos-shell's working_directory), it starts in his home: the
# serial root shell's directory is the recovery account's, which ares cannot enter, and foot exits when its chdir
# fails. foot's own messages are kept for the evidence. It starts on his desktop (no_foot switches to tty1 first): a foot
# started while tty3 is in front finds no monitor and exits (rehearsal 7, run 44812508100). labwc may bring its output
# back a moment after the switch, so a launch that ends with "no monitors available" is tried again, five times at most.
TERMINAL = r'''import json,pathlib,subprocess,time
SUPERVISOR=b'/usr/bin/python3\0/usr/libexec/aresos-desktop\0session\0'
LOG='/run/aresos-terminal.log'
def cmdline(pid):
    try: return pathlib.Path('/proc/'+pid+'/cmdline').read_bytes()
    except FileNotFoundError: return b''
def feet():
    return subprocess.run(['pgrep','-u','ares','-x','foot'],capture_output=True,text=True).stdout.split()
named=subprocess.run(['pgrep','-u','ares','-x','aresos-desktop'],capture_output=True,text=True).stdout.split()
supervisor=[pid for pid in named if cmdline(pid)==SUPERVISOR]
out=dict(supervisors=len(supervisor),wayland=False,home=False,foot=0,running=0,attempts=0,log='')
if len(supervisor)==1:
    env=dict(i.split('=',1) for i in pathlib.Path('/proc/'+supervisor[0]+'/environ').read_text().split('\0') if '=' in i)
    out['wayland']=bool(env.get('WAYLAND_DISPLAY')) and bool(env.get('XDG_RUNTIME_DIR'))
    out['home']=env.get('HOME')=='/var/home/ares'
if out['wayland'] and out['home']:
    keep=['HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','WAYLAND_DISPLAY','DBUS_SESSION_BUS_ADDRESS','XDG_SESSION_ID','XDG_SEAT','XDG_SESSION_TYPE','XDG_CURRENT_DESKTOP']
    words=['runuser','-u','ares','--','env','-i']+[k+'='+env[k] for k in keep if k in env]+['PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin','setsid','-f']+@ARGV@
    logs=[]
    for attempt in range(1,6):
        out['attempts']=attempt
        with open(LOG,'wb') as log:
            subprocess.run(words,cwd=env['HOME'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,check=True)
        for n in range(60):
            found=feet()
            if found: break
            time.sleep(1)
        out['foot']=len(found)
        # A foot that cannot reach the display, a monitor or its directory exits at once: the same one must still run.
        time.sleep(3)
        out['running']=len(set(found)&set(feet()))
        logs.append(pathlib.Path(LOG).read_text(errors='replace'))
        if out['running'] or 'no monitors available' not in logs[-1]: break
        time.sleep(2)
    out['log']=''.join('[attempt '+str(n+1)+'] '+text for n,text in enumerate(logs))[-2000:]
print(json.dumps(out))
'''

# Ends every foot of ares (the SETUP screen's message window among them) and waits until none is left.
END_FOOT = r'''import json,subprocess,time
before=subprocess.run(['pgrep','-u','ares','-x','foot'],capture_output=True,text=True).stdout.split()
subprocess.run(['pkill','-u','ares','-x','foot'])
for n in range(30):
    left=subprocess.run(['pgrep','-u','ares','-x','foot'],capture_output=True,text=True).stdout.split()
    if not left: break
    time.sleep(1)
print(json.dumps(dict(ended=len(before),left=len(left))))
'''

# Used by both the root snapshot and the reader running as ares. The saves root is resolved separately:
# walking the instance without following its links must not hide the worlds stored elsewhere in home.
HOME_SNAPSHOT = r'''def snapshot(root, check_access=False):
    rows={}
    def denied(error): raise error
    for folder,dirs,files in os.walk(root,followlinks=False,onerror=denied):
        for p in [pathlib.Path(folder)]+[pathlib.Path(folder,name) for name in sorted(files+dirs)]:
            name=str(p.relative_to(root)); s=p.lstat()
            row=dict(uid=s.st_uid,gid=s.st_gid,mode=stat.S_IMODE(s.st_mode),kind=stat.S_IFMT(s.st_mode))
            if check_access:
                needed=os.R_OK|os.X_OK if p.is_dir() else os.R_OK
                assert os.access(p,needed), 'Inaccessible saved-world entry: '+name
            if p.is_symlink(): row['target']=os.readlink(p)
            elif p.is_file(): row['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
            rows[name]=row
    return rows
'''

# The VM stays in SETUP: plant representative config and save data, then snapshot bytes AND metadata.
# This proves persistence/accessibility, not Minecraft loading the configuration or starting a world.
HOME = r'''import hashlib,json,os,pathlib,stat,subprocess
''' + HOME_SNAPSHOT + r'''
instance=pathlib.Path(@INSTANCE@); apps=pathlib.Path(@APPS@)
planted=False
if @PLANT@ and not apps.exists():
    apps.parent.mkdir(parents=True,exist_ok=True)
    apps.write_text(json.dumps(@CONFIG@,indent=2)+'\n')
    for p in (apps,apps.parent,apps.parent.parent):
        os.chown(p,1001,1001)
    planted=True
links=@LINKS@
for name,target in links.items():
    p=instance/name
    assert p.is_symlink() and os.readlink(p)==target, 'STOP: incorrect instance link: '+name
saves=(instance/'minecraft/saves').resolve(strict=True)
world=saves/@WORLD@
if @PLANT@:
    assert not world.exists(), 'STOP: synthetic rehearsal world already exists'
    for name,data in @WORLD_FILES@.items():
        p=world/name
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(bytes.fromhex(data))
    for folder,dirs,files in os.walk(world):
        for p in [pathlib.Path(folder)]+[pathlib.Path(folder,name) for name in files]:
            os.chown(p,1001,1001)
rows=snapshot(instance); stable={}; mutable={}
for name,row in rows.items():
    if any(name==d or name.startswith(d+'/') for d in @MUTABLE_DIRS@):
        mutable[name]=row
        continue
    stable[name]=dict(row)
    if name=='instance.cfg':
        lines=[l for l in (instance/name).read_text().splitlines() if l.split('=',1)[0].strip() not in @MUTABLE_KEYS@]
        stable[name]['sha256']=hashlib.sha256('\n'.join(lines).encode()).hexdigest()
worlds=snapshot(saves)
for name in @WORLD_FILES@:
    assert @WORLD@+'/'+name in worlds, 'STOP: missing saved-world file: '+name
required=@REQUIRED@
# Actually open the files and traverse the links as ares, not as the serial root shell.
reader=''' + repr('''import hashlib,json,os,pathlib,stat,sys
''' + HOME_SNAPSHOT + '''
root=pathlib.Path(sys.argv[1])
required,links,image_targets=json.loads(sys.argv[2])
for name,target in links.items():
    p=root/name
    assert p.is_symlink() and os.readlink(p)==target, 'Incorrect instance link: '+name
for name in required:
    # R27 retains R28's link text in home, but does not contain R28's image payload.
    if name in links and name!='minecraft/saves' and not image_targets: continue
    p=root/name
    assert p.exists(), 'Missing instance file: '+name
    if p.is_dir(): assert os.access(p,os.R_OK|os.X_OK), 'Inaccessible instance directory: '+name
    else: p.read_bytes()
apps=root/'minecraft/config/aresos/apps.json'
assert os.access(apps,os.R_OK|os.W_OK), 'apps.json is not readable/writable as ares'
worlds=snapshot((root/'minecraft/saves').resolve(strict=True),check_access=True)
print(json.dumps(dict(uid=os.getuid(),apps=hashlib.sha256(apps.read_bytes()).hexdigest(),worlds=worlds)))
''') + r'''
read=subprocess.run(@AS_ARES@+['python3','-c',reader,str(instance),json.dumps([required,links,@IMAGE_TARGETS@])],capture_output=True,text=True)
accessible=json.loads(read.stdout) if read.returncode==0 else dict(error=read.stderr[-600:])
print(json.dumps(dict(instance=instance.is_dir(),files=len(rows),tree=hashlib.sha256(json.dumps(rows).encode()).hexdigest(),
    entries=rows,stable=stable,mutable=mutable,accessible=accessible,worlds=worlds,
    apps=hashlib.sha256(apps.read_bytes()).hexdigest() if apps.is_file() else None,
    apps_config=json.loads(apps.read_text()) if apps.is_file() else None,planted=planted)))
'''

# Package 23d's game scope, as the check-build VM proves it (os/ci/overlay/checks.py, desktop_jvm): a real JVM
# through the real wrapper waits at startup; its cgroup is this launch's game scope with memory.high 2560 MiB.
# Killing the scope latches RECOVERY (nothing starts again by itself), so this runs last.
JVM = r'''import json,os,pathlib,subprocess,time
AS_ARES=@AS_ARES@
lock=json.loads(pathlib.Path('/usr/share/aresos/minecraft/desktop.lock.json').read_text())
instance='/var/home/ares/.local/share/PrismLauncher/instances/'+lock['instance']
pause='/tmp/aresos-release28-jvm.paused'
def status():
    done=subprocess.run(AS_ARES+['/usr/libexec/aresos-desktop','status'],capture_output=True,text=True)
    return json.loads(done.stdout) if done.returncode==0 else dict(error=done.stderr[-400:])
wrapper=subprocess.Popen(AS_ARES+['INST_ID='+lock['instance'],'INST_DIR='+instance,'/usr/libexec/aresos-desktop-java',lock['java']['path'],
    '-XX:+UnlockDiagnosticVMOptions','-XX:+PauseAtStartup','-XX:PauseAtStartupFile='+pause,'-version'],
    cwd=instance+'/minecraft',stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
state={}
for n in range(120):
    state=status()
    if state.get('jvm_pid') or wrapper.poll() is not None: break
    time.sleep(.5)
out=dict(state_before=state)
jvm=state.get('jvm_pid')
if jvm:
    runtime=json.loads(pathlib.Path('/run/user/1001/aresos/desktop-runtime.json').read_text())
    unit='aresos-game-'+runtime['launch']+'.scope'
    line=next(l for l in pathlib.Path('/proc/'+str(jvm)+'/cgroup').read_text().splitlines() if l.startswith('0::'))
    folder='/sys/fs/cgroup'+line.split('::',1)[1]
    out.update(unit=unit,cgroup=folder,in_scope=folder.endswith('/user@1001.service/aresos.slice/'+unit),
        memory_high=pathlib.Path(folder,'memory.high').read_text().strip())
    subprocess.run(AS_ARES+['/usr/bin/systemctl','--user','kill','--signal=SIGKILL',unit],capture_output=True)
try: output,_=wrapper.communicate(timeout=60)
except subprocess.TimeoutExpired:
    wrapper.kill(); output,_=wrapper.communicate()
out['wrapper_exit']=wrapper.returncode
out['wrapper_output']=output.decode(errors='replace')[-1000:]
time.sleep(2)
out['state_after']=status()
print(json.dumps(out))
'''

def program(source, **values):
    return tools_local.program(source, **values)


def receipt_setting(receipt):
    assert type(receipt.get('control_rides')) is bool and receipt['control_rides'] == CONTROL_RIDES, \
        'STOP: host walk Control setting differs from the VM driver'


# The release checker is bound by the host receipt and passed through its documented stdin interface.
CONTROL = '''import json, subprocess
checked=subprocess.run(['/usr/bin/python3','-I','-',*@CHECKS@],input=@CHECKER@,capture_output=True,text=True,timeout=150)
roots=['greetd.service','systemd-user-sessions.service']
graph={}
pending=list(roots)
while pending:
    name=pending.pop(0)
    if name in graph: continue
    assert len(graph)<1024, 'login dependency graph too large'
    shown=subprocess.run(['systemctl','show','-p','Id','-p','LoadState','-p','After','-p','Requires','-p','Requisite','-p','BindsTo','--',name],capture_output=True,text=True,timeout=30)
    row=dict(line.split('=',1) for line in shown.stdout.splitlines() if '=' in line)
    graph[name]=dict(status=shown.returncode,properties=row,stderr=shown.stderr)
    pending.extend(dep for key in ('After','Requires','Requisite','BindsTo') for dep in row.get(key,'').split() if dep not in graph)
print(json.dumps(dict(release_checks=dict(status=checked.returncode,stdout=checked.stdout,stderr=checked.stderr),login=dict(roots=roots,graph=graph))))
'''


def control(guest, stage, vm):
    source = pathlib.Path(CONTROL_CHECKER).read_text()
    probe = program(CONTROL, checker=source, checks=CONTROL_CHECKS)
    value = guest.capture_json(stage + '-control', vm.sw.framed('python3 -c ' + shlex.quote(probe)))
    # Retain failures too, before making assertions on the result.
    vm.td.save(stage + '-control', value)
    checked = value['release_checks']
    lines = checked['stdout'].splitlines()
    assert checked['status'] == 0 and len(lines) == 2 and lines[-1] == 'CONTROL_RELEASE_CHECKS_PASS', \
        'STOP: Control release checker failed: ' + json.dumps(checked)
    results = json.loads(lines[0])
    assert set(results) == set(CONTROL_CHECKS) \
        and all(row['ok'] is True for row in results.values()), 'STOP: Control checks missing or failed'
    user = results['service_user']['value']
    assert (user['uid'], user['gid'], user['group_gid']) == (250, 250, 250) \
        and user['users_with_250'] == user['groups_with_250'] == ['aresos-tools'], 'STOP: Control account differs'
    state = results['state_folders']['value']
    expected = {'/var/lib/aresos-tools': '0700', '/var/lib/aresos-operation-evidence': '0700', '/run/aresos-tools': '0711'}
    assert set(state) == set(expected), 'STOP: Control state folders missing'
    for name, mode in expected.items():
        row = state[name]
        assert row['directory'] is True and row['owner'] == [250, 250] and row['mode'] == row['expected_mode'] == mode, \
            'STOP: Control state folder metadata differs: ' + name
        if name.startswith('/var/'):
            assert row['not_owned_count'] == 0 and row['not_owned'] == [], 'STOP: Control state has foreign owners'
    folders = results['folders']['value']
    assert folders['owner_uid'] == 1001 and set(folders['folders']) == {'/var/home/ares/Downloads', '/var/home/ares/Documents'}, \
        'STOP: Control daily folders differ'
    for name, row in folders['folders'].items():
        assert row['exists'] is True and row['directory'] is True and row['link'] is False and row['uid'] == 1001 \
            and row['mode'] == '0700', 'STOP: Control daily folder metadata differs: ' + name
    login = value['login']
    assert login['roots'] == ['greetd.service', 'systemd-user-sessions.service'], 'STOP: missing login roots'
    graph = login['graph']
    pending, seen, masked_units, required = list(login['roots']), set(), set(), set()
    while pending:
        name = pending.pop()
        assert name != 'aresos-toold.service', 'STOP: Control service delays login'
        if name in seen:
            continue
        seen.add(name)
        row = graph[name]
        properties = row['properties']
        assert properties.get('Id') and properties['Id'] != 'aresos-toold.service', 'STOP: login dependency query failed or names Control'
        dependencies = [dep for key in ('After', 'Requires', 'Requisite', 'BindsTo') for dep in properties.get(key, '').split()]
        # Optional After= units (for example home.mount on an Atomic image) can be absent. They cannot delay
        # login; a missing root or an unreadable graph still stops the walk.
        absent = properties.get('LoadState') == 'not-found' and name not in login['roots'] and not dependencies
        # A masked unit never starts, so as an ordering-only reference it cannot delay login: the stock base
        # masks systemd-remount-fs.service (rehearsal 4, run 44729393652; the laptop's release 27 too). Its own
        # ordering is still followed, so Control behind it still stops the walk; a masked login root, or a
        # masked unit another login unit requires (which would keep that unit from starting), stops it.
        masked = properties.get('LoadState') == 'masked' and name not in login['roots']
        if masked:
            masked_units.add(name)
        required.update(dep for key in ('Requires', 'Requisite', 'BindsTo') for dep in properties.get(key, '').split())
        assert (row['status'] == 0 and (properties.get('LoadState') == 'loaded' or masked)) \
            or (absent and row['status'] in (0, 1)), 'STOP: login dependency query failed: ' + name
        pending.extend(dependencies)
    assert set(graph) == seen, 'STOP: login graph has unvisited entries'
    assert not masked_units & required, 'STOP: login dependency query failed: a login unit requires masked ' \
        + ', '.join(sorted(masked_units & required))
    return dict(checks=results, login=login, checker_sha256=hashlib.sha256(source.encode()).hexdigest())


def sites_hash(guest, stage):
    """The made-up sites list's SHA-256 as root reads it (B.2, B.3, B.4: the check must be able to fail)."""
    return guest.command(stage + '-sites-hash', 'set -e; sha256sum < ' + SITES + " | cut -d' ' -f1").strip().splitlines()[-1]


def write_sites(guest, stage):
    """B.2: root writes the list with tee, as the guide does; the folder root's 0755 first if R27 lacks it."""
    guest.command(stage + '-sites', '\n'.join([
        'set -e', 'test -d /var/lib/aresos-control || install -d -o root -g root -m 0755 /var/lib/aresos-control',
        'printf %s\\\\n ' + shlex.quote(SITES_LIST) + ' | tee ' + SITES + ' > /dev/null']))
    return sites_hash(guest, stage)


def session(guest, stage, vm):
    """B.3's session checks on release 28."""
    value = guest.capture_json(stage + '-session', vm.sw.framed('python3 -c ' + shlex.quote(program(SESSION, as_ares=AS_ARES))))
    vm.td.save(stage + '-session', value)
    assert value['labwc'] == 1, 'STOP: his labwc session is not running'
    assert value['theme'] == THEME and value['themerc'], "STOP: package 31's Ares-Crown is not labwc's theme: " + str(value['theme'])
    assert set(value['fonts'].values()) == {SPACE_GROTESK}, 'STOP: fontconfig does not give Space Grotesk: ' + str(value['fonts'])
    return value


def home(guest, stage, vm, plant=False, *, image_targets=True):
    value = guest.capture_json(stage + '-home', vm.sw.framed('python3 -c ' + shlex.quote(
        program(HOME, instance=INSTANCE, apps=APPS, plant=plant, config=APPS_CONFIG, as_ares=AS_ARES,
                mutable_dirs=MUTABLE_DIRS, mutable_keys=MUTABLE_INI_KEYS, required=REQUIRED_INSTANCE,
                links=INSTANCE_LINKS, image_targets=image_targets, world=WORLD, world_files=WORLD_FILES))))
    vm.td.save(stage + '-home', value)
    assert value['instance'] and value['apps'], "STOP: the home screen's instance or apps.json is missing at " + stage
    assert value['apps_config'] == APPS_CONFIG, 'STOP: apps.json is not the representative schema-4 configuration'
    assert all(row['uid'] == row['gid'] == 1001 for row in value['entries'].values()), \
        'STOP: instance ownership changed from ares'
    assert value['accessible'].get('uid') == 1001 and value['accessible'].get('apps') == value['apps'], \
        'STOP: instance or apps.json is inaccessible as ares: ' + str(value['accessible'])
    assert all(row['uid'] == row['gid'] == 1001 for row in value['worlds'].values()), \
        'STOP: saved-world ownership changed from ares'
    assert value['accessible'].get('worlds') == value['worlds'], \
        'STOP: saved-world data is inaccessible as ares: ' + str(value['accessible'])
    return value


def home_unchanged(before, after, *, prism_started=False):
    assert before['worlds'] == after['worlds'], 'STOP: saved-world contents or metadata changed'
    assert before['stable'] == after['stable'], 'STOP: stable instance files or metadata changed'
    if not prism_started:
        assert before['entries'] == after['entries'], 'STOP: release 27 changed instance files or metadata'
    else:
        for name in before['mutable'].keys() & after['mutable'].keys():
            fields = ('uid', 'gid', 'mode', 'kind')
            assert all(before['mutable'][name][k] == after['mutable'][name][k] for k in fields), \
                'STOP: mutable instance metadata changed: ' + name


def no_foot(console, guest, stage, vm):
    """The lead's note: `at check` with no foot of ares STOPs with FOOT_STOP; then the Terminal app's foot again."""
    ended = guest.capture_json(stage + '-end-foot', vm.sw.framed('python3 -c ' + shlex.quote(END_FOOT)))
    vm.td.save(stage + '-end-foot', ended)
    assert ended['left'] == 0, 'STOP: a foot of ares is still running'
    stopped = console.run('check', stage + '-no-foot-check', expect_stop=True)
    assert FOOT_STOP in str(stopped['error']), 'STOP: check without foot did not stop with ' + FOOT_STOP + ': ' + str(stopped['error'])
    assert not any(row.get('mutation') for row in stopped['trace']), 'STOP: the stopped check changed something'
    # His guide opens the Terminal app on his desktop: back to tty1 and his active session first.
    guest.keys(['ctrl', 'alt', 'f1'])
    guest.command(stage + '-terminal-desktop', 'set -e; for n in {1..60}; do if test "$(cat /sys/class/tty/tty0/active)" = tty1; then exit 0; fi; sleep 1; done; exit 1')
    guest.command(stage + '-terminal-session', vm.ACTIVE_DESKTOP)
    time.sleep(1)
    opened = guest.capture_json(stage + '-terminal', vm.sw.framed('python3 -c ' + shlex.quote(program(TERMINAL, argv=vm.HUB_TERMINAL))))
    vm.td.save(stage + '-terminal', opened)
    assert opened['supervisors'] == 1, 'STOP: not exactly one desktop supervisor (aresos-desktop session) of ares: ' + str(opened['supervisors'])
    assert opened['wayland'] is True, "STOP: the desktop supervisor's environment has no Wayland display"
    assert opened['home'] is True, "STOP: the desktop supervisor's HOME is not his home"
    assert opened['foot'] >= 1, 'STOP: the Terminal app did not open a foot'
    assert opened['running'] >= 1, "STOP: the Terminal app's foot exited at once: " + opened['log'][-500:]
    return dict(ended=ended['ended'], stop=str(stopped['error']), terminal=opened)


def game_scope(guest, stage, vm):
    value = guest.capture_json(stage + '-game-scope', vm.sw.framed('python3 -c ' + shlex.quote(program(JVM, as_ares=AS_ARES))))
    vm.td.save(stage + '-game-scope', value)
    assert value.get('in_scope') is True and value.get('memory_high') == MEMORY_HIGH, \
        "STOP: the JVM is not in its game scope with 23d's memory.high: " + json.dumps({k: value.get(k) for k in ('unit', 'cgroup', 'memory_high')})
    assert value['wrapper_exit'] == 128 + 9, 'STOP: the game scope was not ended'
    return value


def facts_27(vm):
    """Release 27's facts from fixed sources (as 22d's step 6c bound them to b216f28f): version 2's own bundle
    names it as its target, and its record in os/manifest/releases/27.json agrees."""
    record = json.loads(vm.git_blob(vm.TOOLS_V2_COMMIT, 'os/manifest/release.json'))
    fixed = json.loads(pathlib.Path(R27_RECORD).read_text())
    assert record['reference'] == fixed['reference'] and record['source_commit'] == fixed['source_commit'], \
        "STOP: version 2's release and release 27's record differ"
    return record


def rehearsal(vm, audit, media, password, hashed, ares_password, version_2, record, *, allow_deferred=False):
    """The walk in the module docstring. vm: the running owner_vm module; record: release 28's record (bytes)."""
    td, Console = vm.td, vm.Console
    head = os.environ['GITHUB_SHA']
    release_27 = facts_27(vm)
    r27, r28 = release_27['reference'], json.loads(record)['reference']
    standin = standin_origin(td.WORK / 'stand-in-28', record)
    fingerprint = standin['fingerprint']
    real = real_commit(head, standin, allow_deferred=allow_deferred)
    announced_rows = [dict(standin=standin['commits'][key], real=V4_COMMIT if key == 'v4' else head if real['equal'] else None,
                           bound={path: standin['hashes'][key][path] for path in BOUND}, guide=standin['hashes'][key][GUIDE],
                           fingerprint=TOOLS_V4 if key == 'v4' else fingerprint, version=4 if key == 'v4' else TOOLS_VERSION)
                      for key in ('v4', 'announced')]
    route = vm.laptop_update(audit, media, password, hashed, bundle=(version_2, vm.TOOLS_V2), target=r27)
    stock, stock_digest = route['stock'], route['stock_digest']
    d13, d27, d28 = route['old_digest'], route['new_digest'], r28.split('@')[1]
    bootstrap = vm.bundle_module('bootstrap')
    routine_action = bootstrap.ACTIONS['tools-routine']
    entries = dict(folder='tools-folder', routine='tools-routine')
    sites, controls = None, {}
    guest = td.start_installed(password, hashed, 'release-27')
    try:
        console, identities = vm.confirmed_update(guest, password, route)
        console.passwd(ares_password, 'release-27-ares-password')
        Console(guest, 'tty4').ares_sudo(ares_password, 'release-27-ares-sudo')
        walk = Walk(vm, guest, ares_password, standin)
        walk.setup('r28-setup')
        start = walk.state('r28-start')
        assert start['entry'] == 'tools-' + vm.TOOLS_V2 + '/at' and (start['journal'] is None or start['journal']['phase'] == 'complete'), \
            'STOP: the walk does not start from tools version 2'

        # The laptop's 22d session: version 4 by the folder and routine lines at 634e1237's stand-in.
        stand_v4 = standin['commits']['v4']
        walk.compare('r28-v4', 'v4', routine_action)
        out = walk.caller('r28-v4', ('folder', 'routine'), stand_v4, entries=entries)
        walk.window('r28-v4', out, TOOLS_V4, routine_action, 'password')
        done = walk.result('r28-v4', out)
        walk.lines_are(done, dict(folder=bootstrap.tools_folder(TOOLS_V4), routine=bootstrap.tools_routine(TOOLS_V4)))
        passes = [line for line in done['routine']['stdout'].splitlines() if line.startswith('PASS ')]
        assert done['routine']['status'] == 0 and passes == ['PASS install', 'PASS check', 'PASS title'], \
            'STOP: version 4 did not install, check and title from its window'
        assert 'Tools updated from version 2 to 4' in done['routine']['stdout'], 'STOP: version 4 did not replace version 2'
        records = walk.capture('r28-v4-records', vm.diagnostic_reader())
        installed = walk.state('r28-v4')
        assert installed['entry'] == 'tools-' + TOOLS_V4 + '/at', 'STOP: version 4 is not the installed tools'
        walk.record('r28-v4', commit=stand_v4, real_commit=V4_COMMIT, passes=passes, tools=TOOLS_V4)

        # B.1: the announced commit's lines; version 4 installs version 5 from the folder.
        walk.advance_origin('r28-origin')
        stand = standin['commits']['announced']
        walk.compare('r28-tools', 'announced', routine_action)
        out = walk.caller('r28-tools', ('folder', 'routine', 'no-ticket'), stand, entries=entries)
        walk.window('r28-tools', out, fingerprint, routine_action, 'password')
        done = walk.result('r28-tools', out)
        walk.lines_are(done, dict(folder=bootstrap.tools_folder(fingerprint), routine=bootstrap.tools_routine(fingerprint)))
        passes = [line for line in done['routine']['stdout'].splitlines() if line.startswith('PASS ')]
        assert done['routine']['status'] == 0 and passes == ['PASS install', 'PASS check', 'PASS title'], \
            'STOP: the announced tools did not install, check and title from one window'
        assert 'Tools updated from version 4 to 5' in done['routine']['stdout'], 'STOP: version 4 did not install version 5'
        assert done['no_ticket']['status'] != 0, 'STOP: sudo kept a ticket after the window'
        receipt = walk.capture('r28-tools-receipt', vm.diagnostic_reader(records, 'tools-update'))
        td.save('r28-tools-receipt', receipt)
        assert (receipt['status'], receipt['manifest'], receipt['previous_manifest']) == ('passed', fingerprint, TOOLS_V4)
        assert (receipt['previous_version'], receipt['tools_version']) == (4, TOOLS_VERSION)
        assert (receipt['source'], receipt['finished_from']) == ('folder', 'folder'), 'STOP: the receipt does not name the folder'
        assert receipt['caller'] == dict(login_uid=1001, terminal=False), 'STOP: the receipt does not name uid 1001 without a terminal'
        assert walk.state('r28-tools')['entry'] == 'tools-' + fingerprint + '/at', 'STOP: the new tools are not installed'
        walk.record('r28-tools', commit=stand, passes=passes, tools=fingerprint, tools_version=TOOLS_VERSION,
                    receipt=dict(source=receipt['source'], caller=receipt['caller'], previous_version=4))

        # B.2 (Chrome browser side only): the made-up sites list.
        if CHROME_RIDES:
            sites = write_sites(guest, 'r28-before-update')

        # B.3: the console's update box.
        console.select()
        update = console.run('update', 'r28-update')
        assert 'Signed exact release staged ' + r28 in vm.result_lines(update), 'STOP: release 28 was not staged'
        vm.deployment_shape(vm.kb.deployment_snapshot(guest, 'r28-update-staged'), stock, [d28, d27, d13, stock_digest], staged=True)
        console.run('title', 'r28-update-title')
        console.run('reboot', 'r28-update-reboot')
    finally:
        vm.finish(guest, audit, 'release-27')

    guest = td.start_installed(password, hashed, 'release-28')
    try:
        # Package 22's JUDGMENT-CALL 1: the update removed release 13 at its shutdown, nothing else.
        identities, booted = vm.deployment_shape(vm.kb.deployment_snapshot(guest, 'release-28'), stock, [d28, d27, stock_digest])
        assert booted == d28, 'STOP: release 28 did not start'
        vm.keyboard(guest, 'release-28', 'de')
        console = Console(guest)
        console.login(password, 'release-28')
        console.become_root(password, 'release-28')
        checked = console.run('check', 'release-28-check')
        titled = console.run('title', 'release-28-title')
        assert 'Update to ' + r28 + ' confirmed after the restart' in vm.result_lines(checked, titled), 'STOP: update not confirmed'
        rules = vm.release_rules(guest, 'release-28')
        seen = session(guest, 'release-28', vm)
        if CONTROL_RIDES:
            controls['release-28'] = control(guest, 'release-28', vm)
        if CHROME_RIDES:
            assert sites_hash(guest, 'release-28') == sites, "STOP: the sites list's hash changed with the update"
        foot = no_foot(console, guest, 'release-28', vm)
        terminal = vm.terminal_path(guest, 'release-28')
        # terminal_path leaves his reopened terminal and local desktop session active for polkit.
        polkit = vm.polkit_sweep(guest, 'release-28')
        console.select()
        kept = home(guest, 'release-28', vm, plant=True)
        returned = console.run('previous', 'r28-previous')
        assert 'Previous AresOS queued for the next start ' + r27 in vm.result_lines(returned), 'STOP: previous did not queue release 27'
        vm.deployment_shape(vm.kb.deployment_snapshot(guest, 'r28-previous-queued'), stock, [d27, d28, stock_digest], queued=True)
        console.run('title', 'r28-previous-title')
        console.run('reboot', 'r28-previous-reboot')
    finally:
        vm.finish(guest, audit, 'release-28')

    # B.4: back on release 27; R27 has no Minecraft desktop, his home keeps the home screen's files.
    guest = td.start_installed(password, hashed, 'previous-27')
    try:
        identities, booted = vm.deployment_shape(vm.kb.deployment_snapshot(guest, 'previous-27'), stock, [d27, d28, stock_digest])
        assert booted == d27, 'STOP: release 27 did not start after previous'
        vm.keyboard(guest, 'previous-27', 'de')
        console = Console(guest)
        console.login(password, 'previous-27')
        console.become_root(password, 'previous-27')
        checked = console.run('check', 'previous-27-check')
        titled = console.run('title', 'previous-27-title')
        assert 'Return to ' + r27 + ' confirmed after the restart' in vm.result_lines(checked, titled), 'STOP: return not confirmed'
        if CHROME_RIDES:
            assert sites_hash(guest, 'previous-27') == sites, "STOP: the sites list's hash changed with previous"
        back = home(guest, 'previous-27', vm, image_targets=False)
        home_unchanged(kept, back)
        forward = console.run('forward', 'r28-forward')
        assert 'Newest installed AresOS starts next ' + r28 in vm.result_lines(forward), 'STOP: forward did not name release 28'
        vm.deployment_shape(vm.kb.deployment_snapshot(guest, 'r28-forward-queued'), stock, [d28, d27, stock_digest], queued=True)
        console.run('title', 'r28-forward-title')
        console.run('reboot', 'r28-forward-reboot')
    finally:
        vm.finish(guest, audit, 'previous-27')

    guest = td.start_installed(password, hashed, 'final-28')
    try:
        identities, booted = vm.deployment_shape(vm.kb.deployment_snapshot(guest, 'final-28'), stock, [d28, d27, stock_digest])
        assert booted == d28, 'STOP: release 28 did not start after forward'
        vm.keyboard(guest, 'final-28', 'de')
        console = Console(guest)
        console.login(password, 'final-28')
        console.become_root(password, 'final-28')
        checked = console.run('check', 'final-28-check')
        titled = console.run('title', 'final-28-title')
        assert 'Forward to ' + r28 + ' confirmed after the restart' in vm.result_lines(checked, titled), 'STOP: forward not confirmed'
        if CHROME_RIDES:
            assert sites_hash(guest, 'final-28') == sites, "STOP: the sites list's hash changed on the way back"
        if CONTROL_RIDES:
            controls['final-28'] = control(guest, 'final-28', vm)
        again = home(guest, 'final-28', vm)
        home_unchanged(kept, again, prism_started=True)
        scope = game_scope(guest, 'final-28', vm)
        console.logout('final-28-logout')
    finally:
        vm.finish(guest, audit, 'final-28')
    td.marker(audit, 'final-unattended-windows')
    td.marker(audit, 'final-detached-windows', detached=True)
    result = dict(status='passed', qualified=not allow_deferred and real['equal'] and (not CONTROL_RIDES or set(controls) == {'release-28', 'final-28'}), commit=head, order='protected-second',
        starting_state="package 27's route (release 27 by tools version 2), then 22d's lines at 634e1237's stand-in: tools version 4",
        release_27=r27, release_28=r28, tools_version_2=vm.TOOLS_V2, tools_version_4=TOOLS_V4, tools=fingerprint,
        tools_version=TOOLS_VERSION, announced=announced_rows, real_commit=real, compared=walk.compared,
        dialogs=walk.dialogs, stages=walk.stages, control_rides=CONTROL_RIDES, chrome_rides=CHROME_RIDES, sites_sha256=sites,
        package21_rules={k: rules[k] for k in ('ares_in_wheel', 'sudo_all_with_password', 'sudo_keeps_no_ticket', 'sudo_n_refused')},
        terminal_path=terminal['path'], terminal_path_retried=terminal['retried'],
        polkit_sweep=dict(actions=polkit['actions'], answers=polkit['answers'], passwordless=len(polkit['passwordless'])),
        session=dict(theme=seen['theme'], fonts=seen['fonts']), control_checked=CONTROL_RIDES and set(controls) == {'release-28', 'final-28'}, control=controls, no_foot=foot,
        home=dict(apps=kept['apps'], instance_tree=kept['tree'], planted=kept['planted'], after_forward_tree=again['tree'],
                  worlds=kept['worlds'], after_forward_worlds=again['worlds']),
        game_scope=dict(unit=scope['unit'], memory_high=scope['memory_high']), caller_terminal=False,
        protected_disk_audits=True, deployments_checked_every_start=True)
    td.save('release-28-rehearsal-result', result)
