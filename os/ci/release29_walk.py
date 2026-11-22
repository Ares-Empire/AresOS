"""Package 331's historical preflight and R29 deployment rehearsal."""
import hashlib
import json
import pathlib
import re
import shlex
import subprocess
import sys
from types import SimpleNamespace

import installer_inspect
import installer_webui
import registry_auth
import release28_walk as r28
import release29_probes as probes
import stock_image
import tools_local

TOOLS_V5_COMMIT = '6ae4da41934821e5bcfda855ce057bc355900161'
TOOLS_V5 = 'df89ac336e13db84934505551ba28163cbd60fa5b3b9fb0ec97b9585945896c6'
TOOLS_V5_TREE = '8f68ef346c33c2a388581f79797b8775df2135a6'
R13_SQUASH = '775be05b7f0d6971cbdc8a3bd1aea617fc008c4d'
R13_IMAGE_PATHS = ('os/Containerfile.keyboard', 'os/.containerignore', 'os/packages.lock.json',
                   'os/config', 'os/policy', 'os/manifest/base.json', 'os/keys', 'os/tests/audit.py')
BASELINE_RECEIPT = pathlib.Path('evidence/release-29-baseline.json')
HOST_WALK_RECEIPT = 'os/manifest/ci/331/host-walk.json'
PARENT_HOST_WALK = 'os/manifest/ci/42/host-walk.json'
PAYLOAD = 'os/owner-tools/payload'
RECORD = 'os/manifest/releases/29.json'
IDENTITY = registry_auth.R29_IDENTITY
# This tracks the historical route's checkout inputs. Image sources, released tools and
# old release records are checked at their pinned Git objects or against their record hashes.
BASELINE_PATHS = (
    '.gitattributes', '.github/workflows/os-image.yml', 'docs/install-tools/OwnerTools.psm1',
    'os/ci/disk_audit.py', 'os/ci/firmware_contract.py', 'os/ci/greeter.py', 'os/ci/grub_bls.py',
    'os/ci/install-tools.sh', 'os/ci/installer_inspect.py',
    'os/ci/installer_webui.py', 'os/ci/keyboard_diagnostic.py', 'os/ci/keyboard_entries.py',
    'os/ci/keyboard_proof.py', 'os/ci/keyboard_vm.py', 'os/ci/offline_webui.py',
    'os/ci/prepare_two_disks.py', 'os/ci/qmp.py', 'os/ci/registry_auth.py', 'os/ci/rehearsal_auth.py',
    'os/ci/release28_walk.py', 'os/ci/release29_walk.py', 'os/ci/release29_probes.py', 'os/ci/reorder_probe.py',
    'os/ci/serial_console.py', 'os/ci/serial_transport.py', 'os/ci/stock_image.py',
    'os/ci/switch_vm.py', 'os/ci/toolchain.json', 'os/ci/tools_local.py', 'os/ci/two_disk_vm.py',
    'os/ci/windows_marker.c',
    'os/manifest/base.json', 'os/manifest/installer-isos.json', 'os/owner-tools/owner.py',
    'os/manifest/ci/13/13f-zero-cost/qemu-keymap.csv',
    'os/tests/inherited-homebrew.sh',
)
INPUT_PATHSPECS = ('os/ci/owner*.py', 'os/manifest/ci/14/14zu-local',
                   'os/manifest/ci/14/keyboard-sources')


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(path):
    return json.loads(pathlib.Path(path).read_bytes())


def fetch_historical_sources(vm):
    records = registry_auth.historical_records()
    commits = [json.loads(raw)['source_commit'] for raw in records.values()]
    commits.extend((R13_SQUASH, vm.RELEASE_13_SCRIPTS, vm.LAPTOP_TOOLS_COMMIT, vm.TOOLS_V2_COMMIT,
                    r28.V4_COMMIT, TOOLS_V5_COMMIT))
    for commit in commits:
        if subprocess.run(['git', 'cat-file', '-e', commit + '^{commit}'], capture_output=True).returncode != 0:
            r28.git('fetch', '--no-tags', 'origin', commit)
    historical_tools(vm, records)


def historical_tools(vm, records):
    releases = {version: json.loads(raw) for version, raw in records.items()}
    for version, record in releases.items():
        source = record['source_commit']
        assert r28.git('rev-parse', source + '^{commit}').decode().strip() == source
        if version == '13':
            # R13 predates tree rows in the record. Its verified squash kept these exact inputs.
            r28.git('diff', '--exit-code', source, R13_SQUASH, '--', *R13_IMAGE_PATHS)
        else:
            for row in record['source_trees']:
                assert r28.git('rev-parse', source + ':' + row['path']).decode().strip() == row['tree'], \
                    f'STOP: R{version} image source differs at ' + row['path']

    pins = {
        1: (vm.LAPTOP_TOOLS_COMMIT, vm.LAPTOP_TOOLS, '13', '0c1c682fbe090dd6e0b0e1c336a3e4c20f1ca73e'),
        2: (vm.TOOLS_V2_COMMIT, vm.TOOLS_V2, '27', 'fcce0170e6247cf7305a6e0c45b4c4ec1f04956a'),
        4: (r28.V4_COMMIT, r28.TOOLS_V4, '27', r28.V4_TREE),
        5: (TOOLS_V5_COMMIT, TOOLS_V5, '28', TOOLS_V5_TREE),
    }
    tools, commands = {}, {}
    for version, (commit, fingerprint, release, tree) in pins.items():
        assert r28.git('rev-parse', commit + ':os/owner-tools').decode().strip() == tree, f'STOP: tools v{version} tree differs'
        for path in ('os/manifest/release.json', PAYLOAD + '/release.json'):
            assert vm.git_blob(commit, path) == records[release], f'STOP: tools v{version} release record differs'
        assert sha256(vm.git_blob(commit, PAYLOAD + '/SHA256SUMS')) == fingerprint, f'STOP: tools v{version} fingerprint differs'
        commands[version] = json.loads(vm.git_blob(commit, 'os/owner-tools/commands.json'))
        tools[version] = dict(version=version, commit=commit, fingerprint=fingerprint, release=release, tree=tree)

    # The historical preparation also uses the R13 policy probes from their own reviewed head.
    for name in ('guest.sh', 'inherited-homebrew.sh'):
        assert vm.git_blob(vm.RELEASE_13_SCRIPTS, 'os/tests/' + name)
    return tools, commands


def baseline_paths():
    tracked = r28.git('ls-files', '-z', '--', *INPUT_PATHSPECS).decode().split('\0')[:-1]
    paths = set(BASELINE_PATHS) | set(tracked)
    paths.update(f'os/manifest/releases/{version}.json' for version in registry_auth.BASELINE_RECORDS)
    return paths


def baseline_inputs():
    paths = baseline_paths()
    # Step 4 adds the host walk receipt that the hosted owner route requires.
    if pathlib.Path(HOST_WALK_RECEIPT).exists():
        paths.add(HOST_WALK_RECEIPT)
    return [dict(sha256=sha256(pathlib.Path(path).read_bytes()), path=path) for path in sorted(paths)]


def host_walk_paths():
    inherited = {row['path'] for row in read_json(PARENT_HOST_WALK)['sources']}
    gone = {path for path in inherited if not pathlib.Path(path).is_file()}
    tracked = r28.git('ls-files', '-z', '--', 'control/chrome/extension', 'control/chrome/packaging')
    paths = (inherited - gone) | baseline_paths() | {
        PARENT_HOST_WALK, probes.CONTROL_CHECKER, probes.CHROME_FIRST_USE, probes.POLKIT_REVIEW, probes.GH_LOCK,
        'os/config/usr/share/aresos/apps/browser.json', 'os/config/usr/share/aresos/apps/terminal.json',
        'os/config/usr/share/applications/aresos-mimeapps.list',
        'os/config/usr/share/applications/' + probes.PRISM_DESKTOP,
        'os/tests/test_release29_rehearsal.py', 'reviews/331-release-29/walk-host.py',
        *tracked.decode().split('\0')[:-1],
    }
    return sorted(paths), sorted(gone)


def check_host_receipt(receipt):
    assert receipt.get('probe_settings') == probes.receipt_settings(), 'STOP: R29 host walk probe settings differ'
    paths, gone = host_walk_paths()
    assert receipt.get('inherited_from') == PARENT_HOST_WALK and receipt.get('no_longer_bound') == gone, \
        'STOP: R29 host walk inheritance differs'
    sources = [row['path'] for row in receipt['sources']]
    missing = set(paths) - set(sources)
    assert not missing, 'STOP: R29 host walk is missing sources: ' + ', '.join(sorted(missing))
    assert sorted(sources) == paths, 'STOP: R29 host walk has duplicate or unexpected sources'


def installer_download(live, evidence=installer_inspect.EVIDENCE):
    observed = read_json(evidence / 'iso-download.json')
    assert observed['status'] == 'passed' and observed['filename'] == live['filename'] and observed['url'] == live['url'], \
        'STOP: missing pinned ISO download evidence'
    installer_inspect.validate_download(observed, live)
    return dict(filename=live['filename'], sha256=live['sha256'], bytes=live['bytes'])


def served_webui(evidence):
    assets = read_json(evidence / 'completion-selector-source.json')['sources']
    bundles = [row for row in assets if row['url'].endswith('/index.js')]
    maps = [row for row in assets if row['url'].endswith('/index.js.map')]
    assert len(bundles) == len(maps) == 1 and maps[0]['url'] == bundles[0]['url'] + '.map', \
        'STOP: missing or ambiguous served Web UI assets'
    hashes = dict(bundle_sha256=bundles[0]['sha256'], source_map_sha256=maps[0]['sha256'])
    assert hashes == ui_hashes(), 'STOP: served Web UI hashes differ'
    return hashes


def ui_hashes():
    return dict(bundle_sha256=installer_webui.UI_BUNDLE_SHA256, source_map_sha256=installer_webui.UI_SOURCE_MAP_SHA256)


def prepare(vm, *, qualifying=False):
    """Resolve historical inputs and check same-run registry and ISO evidence before starting the guest."""
    registry_auth.require_baseline_dispatch()
    if not qualifying:
        BASELINE_RECEIPT.unlink(missing_ok=True)
    records = registry_auth.historical_records()
    registry = registry_auth.check_baseline_registry(read_json(registry_auth.BASELINE_REGISTRY),
                                                    records, registry_auth.baseline_run())
    tools, commands = historical_tools(vm, records)
    base = stock_image.base()['reference']
    assert all(json.loads(raw)['base'] == base for raw in records.values()), 'STOP: historical stock reference differs'
    iso = installer_download(vm.td.LIVE)
    return SimpleNamespace(records=records, registry=registry, tools=tools, commands=commands,
                           inputs=baseline_inputs(), iso=iso)


def announced(record, version, source='.', *, guide=None):
    """Generate both release copies, history, manifests, commands and guide from the v5 line."""
    release = json.loads(record)
    reference = release['reference']
    assert re.fullmatch(r'ghcr\.io/ares-empire/aresos@sha256:[0-9a-f]{64}', reference), 'STOP: R29 requires an exact org digest'
    assert release['signature'] == dict(method='cosign keyless', identity=IDENTITY,
                                       issuer='https://token.actions.githubusercontent.com'), 'STOP: wrong R29 signature policy'
    assert release['daily_wheel'] is True and release['visibility'] == 'private' and record.endswith(b'\n')
    show = lambda path: r28.git('show', TOOLS_V5_COMMIT + ':' + path, source=source)
    assert r28.git('rev-parse', TOOLS_V5_COMMIT + ':os/owner-tools', source=source).decode().strip() == TOOLS_V5_TREE
    assert sha256(show(PAYLOAD + '/SHA256SUMS')) == TOOLS_V5
    history = json.loads(show('os/owner-tools/history.json'))
    assert history['tools_version'] == 5 and type(version) is int and version > 5
    assert reference not in {row['reference'] for row in history['releases']}, 'STOP: R29 reuses a historical digest'
    history['tools_version'] = version
    history['releases'].append(dict(reference=reference, identity=IDENTITY, daily_wheel=True))
    raw_history = (json.dumps(history, indent=2) + '\n').encode()
    payload = {'history.json': raw_history, 'release.json': record}
    rows = [dict(sha256=sha256(payload[name] if name in payload else show(PAYLOAD + '/' + name)), path=name)
            for name in (row['path'] for row in json.loads(show(PAYLOAD + '/SHA256.json')))]
    manifest = (json.dumps(rows, indent=2) + '\n').encode()
    sums = (''.join(row['sha256'] + '  ' + row['path'] + '\n' for row in rows)
            + sha256(manifest) + '  SHA256.json\n').encode()
    fingerprint = sha256(sums)
    bootstrap = r28.bootstrap_of(source)
    assert show('os/owner-tools/bootstrap.py') == r28.git('show', r28.V4_COMMIT + ':os/owner-tools/bootstrap.py', source=source)
    commands = json.loads(show('os/owner-tools/commands.json'))
    commands['install'] = bootstrap['command'](fingerprint)
    commands.update(bootstrap['lines'](fingerprint))
    header = r28.guide_line(fingerprint, version)
    if guide is None:
        lines = show(r28.GUIDE).decode().split('\n')
        assert (lines[0], lines[2]) == (r28.guide_line(TOOLS_V5, 5), TOOLS_V5)
        lines[0], lines[2] = header, fingerprint
        guide = '\n'.join(lines).encode()
    else:
        lines = guide.decode().splitlines()
        assert len(lines) >= 3 and (lines[0], lines[2]) == (header, fingerprint), 'STOP: the candidate guide fingerprint differs'
    files = {'os/owner-tools/history.json': raw_history,
             'os/owner-tools/commands.json': (json.dumps(commands, indent=2) + '\n').encode(),
             'os/manifest/release.json': record, r28.GUIDE: guide}
    files.update({PAYLOAD + '/' + name: raw for name, raw in
                  dict(payload, **{'SHA256.json': manifest, 'SHA256SUMS': sums}).items()})
    return dict(files=files, fingerprint=fingerprint, version=version, reference=reference, commands=commands)


def candidate_origin(destination, historical, record, version, source='.', *, guide=None):
    candidate = announced(record, version, source, guide=guide)
    # The alternate bundle changes its fingerprint without changing the target or version.
    mismatch = dict(json.loads(record), owner_review='Equal-version rehearsal fixture')
    alternate = announced((json.dumps(mismatch, indent=2) + '\n').encode(), version, source)
    assert alternate['fingerprint'] != candidate['fingerprint']
    destination.mkdir(parents=True, exist_ok=False)
    repo = destination / 'stand-in.git'
    subprocess.run(['git', 'clone', '--quiet', '--bare', str(historical['repository']), str(repo)], check=True)
    base = historical['commits']['announced']
    commits, hashes = {'v5': base}, {'v5': historical['hashes']['announced']}
    parent = base
    for key, made in (('mismatch', alternate), ('announced', candidate)):
        tree, hashes[key] = r28.tree_with(repo, base, made['files'])
        parent = commits[key] = r28.git('commit-tree', tree, '-p', parent, '-m', 'R29 rehearsal ' + key,
                                        env=tools_local.STANDIN_ENV, source=repo).decode().strip()
    r28.git('update-ref', 'refs/heads/main', commits['announced'], source=repo)
    bundle = destination / 'stand-in.bundle'
    r28.git('bundle', 'create', str(bundle.resolve()), 'main', source=repo)
    return dict(candidate, bundle=bundle, repository=repo, commits=commits, hashes=hashes,
                trees={key: rows['os/owner-tools'] for key, rows in hashes.items()},
                variants={'v5': (TOOLS_V5, 5), 'mismatch': (alternate['fingerprint'], version),
                          'announced': (candidate['fingerprint'], version)})


def candidate_equality(head, standin, source='.', *, allow_deferred=False):
    """Compare full published trees and guide, including modes, before the update route."""
    head = r28.git('rev-parse', '--verify', head + '^{commit}', source=source).decode().strip()
    paths = (*r28.BOUND, r28.GUIDE)
    current = {path: r28.git('ls-tree', head, '--', path, source=source).decode().split() for path in paths}

    def differences(key):
        return [path for path, (mode, kind) in zip(paths, (('040000', 'tree'), ('100644', 'blob'), ('100644', 'blob')))
                if current[path] != [mode, kind, standin['hashes'][key][path], path]]

    if not differences('v5'):
        assert allow_deferred, 'STOP: final qualification requires candidate equality before the walk'
        return dict(head=head, equal=False, deferred=True)
    differ = differences('announced')
    assert not differ, 'STOP: candidate differs from the rehearsed bundle or guide in ' + ', '.join(differ)
    return dict(head=head, equal=True, bound=standin['hashes']['announced'], fingerprint=standin['fingerprint'])


def prepare_candidate(vm, prepared, head):
    """Resolve the real candidate against the committed record before starting any guest."""
    record = r28.git('show', head + ':' + RECORD)
    assert pathlib.Path(RECORD).read_bytes() == record, 'STOP: candidate record differs from its commit'
    assert json.loads(record)['base'] == stock_image.base()['reference'], 'STOP: candidate base differs from R28'
    version = json.loads(r28.git('show', head + ':os/owner-tools/history.json'))['tools_version']
    historical = r28.standin_origin(vm.td.WORK / 'stand-in-28', prepared.records['28'])
    candidate = candidate_origin(vm.td.WORK / 'stand-in-29', historical, record, version,
                                 guide=r28.git('show', head + ':' + r28.GUIDE))
    equality = candidate_equality(head, candidate)
    return SimpleNamespace(historical=historical, candidate=candidate, equality=equality)


# Submitted to the serial root shell in the disposable guest. Read the installed files themselves
# and require the update journal to be archived after check/title confirms the new boot.
INSTALLED = """import hashlib,json,os,pathlib
home=pathlib.Path('/var/lib/ares')
entry=os.readlink(home/'at')
root=home/@DIRECTORY@
assert entry==root.name+'/at' and root.is_dir() and not root.is_symlink(), 'Wrong installed tools entry'
files={}
for path in root.rglob('*'):
    assert not path.is_symlink() and (path.is_file() or path.is_dir()), 'Unexpected installed tools file type'
    if path.is_file():
        files[path.relative_to(root).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
journal=home/'tools-update-intent.json'
outcome=home/'records'/'outcome-pending.json'
assert not journal.is_symlink(), 'Unexpected tools journal link'
print(json.dumps(dict(files=files, entry=entry,
    phase=json.loads(journal.read_text())['phase'] if journal.exists() else None,
    pending=outcome.exists() or outcome.is_symlink())))
"""


def installed_v5(vm, guest):
    return installed_tools(vm, guest, 'release-28-baseline-tools', TOOLS_V5, TOOLS_V5_COMMIT)


def installed_tools(vm, guest, stage, fingerprint, commit, repo='.'):
    source = INSTALLED.replace('@DIRECTORY@', repr('tools-' + fingerprint))
    observed = guest.capture_json(stage, vm.sw.framed('python3 -c ' + shlex.quote(source)))
    paths = r28.git('ls-tree', '-r', '--name-only', commit, PAYLOAD, source=repo).decode().splitlines()
    expected = {path.removeprefix(PAYLOAD + '/'): sha256(r28.git('show', commit + ':' + path, source=repo)) for path in paths}
    assert observed['entry'] == 'tools-' + fingerprint + '/at' and observed['files'] == expected, \
        'STOP: installed tools differ from ' + ('released v5' if fingerprint == TOOLS_V5 else 'the R29 candidate')
    assert observed['phase'] in (None, 'complete') and observed['pending'] is False, \
        'STOP: baseline tools or deployment change remains open'
    return observed


class CandidateWalk(r28.Walk):
    """Use the existing guest origin and the published folder and password-window lines."""

    def setup(self, stage):
        self.upload_bundle(stage)
        self.guest.command(stage + '-fetch', 'set -e\n' + tools_local.AS_ARES + 'git -C ' + tools_local.GUEST_ORIGIN
                           + ' fetch --quiet /run/aresos-standin.bundle refs/heads/main:refs/heads/rehearsal-29')
        self.advance_origin(stage)
        self.keyrings = self.capture(stage + '-keyrings', tools_local.KEYRINGS)

    def routine(self, stage, key):
        fingerprint, version = self.standin['variants'][key]
        commit = self.standin['commits'][key]
        action = self.bootstrap.ACTIONS['tools-routine']
        guide = r28.git('show', commit + ':' + r28.GUIDE, source=self.standin['repository']).decode().splitlines()
        assert (guide[0], guide[2]) == (r28.guide_line(fingerprint, version), fingerprint), 'STOP: guide and window differ'
        self.compared.append(dict(stage=stage, commit=commit, line_1=guide[0], label_8=fingerprint[:8]))
        self.vm.td.save(stage + '-owner-tools-line-1', self.compared[-1])
        out = self.caller(stage, ('folder', 'routine', 'no-ticket'), commit,
                          entries=dict(folder='tools-folder', routine='tools-routine'))
        self.window(stage, out, fingerprint, action, 'password')
        done = self.result(stage, out)
        self.lines_are(done, dict(folder=self.bootstrap.tools_folder(fingerprint), routine=self.bootstrap.tools_routine(fingerprint)))
        assert done['folder']['status'] == 0, 'STOP: the candidate folder route failed'
        response = done['routine']
        messages = response['stdout'].splitlines()
        passes = [line for line in messages if line.startswith('PASS ')]
        if key == 'announced':
            assert response['status'] == 0 and passes == ['PASS install', 'PASS check', 'PASS title'] \
                and 'manifest SHA256 ' + fingerprint in messages, 'STOP: the candidate routine did not install, check and title'
            assert done['no_ticket']['status'] != 0, 'STOP: sudo kept a ticket after the window'
        else:
            assert response['status'] != 0 and not passes and any(
                line.startswith('STOP: Installed tools are version ' + str(self.standin['version'])
                                + '; refusing version ' + str(version) + ' (downgrade or same version)')
                for line in messages), 'STOP: the version refusal did not happen at install'
        return messages

    def install(self):
        self.setup('r29-setup')
        initial = self.state('r29-before-tools')
        assert initial['entry'] == 'tools-' + TOOLS_V5 + '/at'
        fingerprint, version = self.standin['fingerprint'], self.standin['version']
        messages = self.routine('r29-tools', 'announced')
        assert 'Tools updated from version 5 to ' + str(version) in messages, 'STOP: the candidate did not replace v5'
        receipt = self.capture('r29-tools-receipt', self.vm.diagnostic_reader(initial['records'], 'tools-update'))
        self.vm.td.save('r29-tools-receipt', receipt)
        assert (receipt['status'], receipt['previous_version'], receipt['tools_version']) == ('passed', 5, version)
        assert (receipt['previous_manifest'], receipt['manifest']) == (TOOLS_V5, fingerprint)
        assert receipt['source'] == receipt['finished_from'] == 'folder' and receipt['caller'] == dict(login_uid=1001, terminal=False)
        installed = self.state('r29-after-tools')
        assert installed['entry'] == 'tools-' + fingerprint + '/at' and installed['journal']['phase'] == 'complete'
        command = tools_local.AS_ARES + 'git -C ' + self.bootstrap.CHECKOUT + ' checkout --quiet '
        for key, suffix in (('announced', 'identical'), ('mismatch', 'mismatch'), ('v5', 'v5')):
            stage = 'r29-tools-' + suffix
            if key != 'announced':
                self.guest.command(stage + '-checkout', command + '--detach ' + self.standin['commits'][key])
            messages = self.routine(stage, key)
            if key == 'announced':
                assert 'Tools already installed; nothing changed' in messages, 'STOP: the identical bundle was not a no-op'
            final = self.state(stage + '-rechecked')
            # Each invocation can leave diagnostics and a private bootstrap copy.
            for field in ('tools', 'entry', 'toolsets', 'journal'):
                assert final[field] == installed[field], 'STOP: the routine replay changed installed tools at ' + field
        self.guest.command('r29-tools-candidate-checkout', command + 'main')
        return receipt


def terminal(guest, stage, vm):
    r28.end_foot(guest, stage, vm)
    return probes.open_terminal(guest, stage, vm)


SAVE_GATE = '''import json,subprocess
command=@COMMAND@
state=json.loads(subprocess.check_output(command+['status'],text=True))
mode,reason=state.get('state'),state.get('reason')
closed=state.get('ready') is False and 'jvm_pid' in state and state['jvm_pid'] is None
if closed and (mode,reason)==('RECOVERY','quit'):
    message=subprocess.check_output(command+['explain'],text=True).splitlines()
    closed='Minecraft was closed. Nothing is wrong.' in message
print(json.dumps(dict(state=mode,reason=reason,safe=closed and (mode=='SETUP' or (mode,reason)==('RECOVERY','quit')))))
'''


def save_gate(vm, guest, stage):
    # The rehearsal stays in SETUP. An open or indeterminate world needs the
    # guide's normal close and acknowledgement before the owner can continue.
    source = r28.program(SAVE_GATE, command=[*r28.AS_ARES, '/usr/libexec/aresos-desktop'])
    state = guest.capture_json(stage + '-save-gate', vm.sw.framed('python3 -c ' + shlex.quote(source)))
    vm.td.save(stage + '-save-gate', state)
    assert state['safe'] is True, 'STOP: get Help before restarting R28 without a confirmed normal Minecraft close'


def shape(vm, guest, stage, stock, order, running, retained, *, staged=False, queued=False, snapshot=None):
    snapshot = vm.kb.deployment_snapshot(guest, stage) if snapshot is None else snapshot
    identities, booted = vm.deployment_shape(snapshot, stock, order, staged=staged, queued=queued)
    assert booted == running, 'STOP: wrong booted release at ' + stage
    assert len(set(identities.values())) == len(order), 'STOP: duplicate deployment identity at ' + stage
    assert all(identities.get(digest) == identity for digest, identity in retained.items()), \
        'STOP: retained deployment changed at ' + stage
    rows = dict(zip(order, snapshot['rpm']['deployments']))
    assert rows[order[-1]]['container-image-reference'] == stock['container-image-reference'], 'STOP: corrected stock origin changed'
    slots = snapshot['bootc']['status']
    other = next(digest for digest in order[int(staged):] if digest != booted)
    expected = {'booted': booted, 'staged': order[0] if staged else None, 'rollback': other}
    for name, digest in expected.items():
        slot = slots.get(name)
        assert bool(slot) == (digest is not None), 'STOP: unexpected bootc ' + name + ' slot'
        if slot:
            ostree = slot['ostree']
            assert slot['image']['imageDigest'] == digest and \
                (ostree['checksum'], ostree['deploySerial'], ostree['stateroot']) == identities[digest], \
                'STOP: bootc disagrees with the ' + name + ' deployment at ' + stage
            reference = rows[digest]['container-image-reference'].removeprefix('ostree-unverified-registry:').removeprefix(
                'ostree-image-signed:docker://')
            assert slot['image']['image']['image'] == reference and reference.endswith('@' + digest) and slot['pinned'] is rows[digest]['pinned'], \
                'STOP: bootc reference or pin disagrees with ' + name + ' at ' + stage
    return identities


def title(vm, console, stage, order, *, staged=False):
    lines = vm.result_lines(console.run('title', stage + '-title'))
    assert 'pin yes; transaction idle' in lines and 'Previous title INVALID; use this record until the next reorder' in lines, \
        'STOP: title did not refresh the pinned deployment state'
    label = 'Boot menu after the update finishes at shutdown (expected):' if staged else 'Boot menu at the next start:'
    menus = [line.removeprefix(label).strip().split('; ') for line in lines if line.startswith(label)]
    assert len(menus) == 1 and len(menus[0]) == len(order) and all(
        digest.split(':')[1][:12] in row for digest, row in zip(order, menus[0])), 'STOP: title shows the wrong boot order'
    return lines


def stage_candidate(vm, guest, console, route, release, confirmed, daily_password, candidate):
    assert route['stock_digest'] == stock_image.base()['digest']
    d28, d29 = (reference.split('@')[1] for reference in (release, candidate['reference']))
    d27, stock_digest, stock = route['new_digest'], route['stock_digest'], route['stock']
    kept = r28.home(guest, 'r29-starting-28', vm, plant=True, write_saves=True)
    assert kept['planted'], 'STOP: starting R28 did not plant the apps fixture'
    probes.session(guest, 'r29-starting-28', vm, '28')
    probes.control(guest, 'r29-starting-28', vm)
    sites = probes.stage_sites(guest, 'r29-starting-28', vm)
    console.select()
    walk = CandidateWalk(vm, guest, daily_password, candidate, bootstrap=SimpleNamespace(**r28.bootstrap_of()))
    receipt = walk.install()
    before = [d28, d27, stock_digest]
    shape(vm, guest, 'r29-after-tools-shape', stock, before, d28, confirmed)
    installed_tools(vm, guest, 'r29-candidate-tools', candidate['fingerprint'], candidate['commits']['announced'], candidate['repository'])

    console.commands = candidate['commands']
    update = console.run('update', 'r29-update', allow_stop=True)
    if update['status'] == 'stopped':
        shape(vm, guest, 'r29-update-refused', stock, before, d28, confirmed)
        raise AssertionError('STOP: update was refused; keep the console result and get Help')
    lines = vm.result_lines(update)
    assert 'Signed exact release staged ' + candidate['reference'] in lines and 'Running release stays as rollback ' + release in lines, \
        'STOP: update did not name the exact staged and retained releases'
    retirement = [line for line in lines if line.endswith(' is removed when the update finishes at shutdown')]
    assert retirement == ['Older AresOS ' + route['new'] + ' is removed when the update finishes at shutdown'], \
        'STOP: update did not name R27 as the sole retirement'
    assert 'pin yes; transaction idle' in lines, 'STOP: staging did not report pinned stock and an idle transaction'
    staged = shape(vm, guest, 'r29-update-staged', stock, [d29, d28, d27, stock_digest], d28, confirmed, staged=True)
    title(vm, console, 'r29-update', [d29, d28, stock_digest], staged=True)
    guest.media_absent('r29-before-export')
    export = console.run('export', 'r29-update-export')
    assert 'Tools stick absent: records copied to /run/ares-records with SHA256 readback' in vm.result_lines(export), \
        'STOP: no-stick export did not report SHA256 readback'
    save_gate(vm, guest, 'r29-update-reboot')
    console.run('reboot', 'r29-update-reboot')
    vm.td.save('r29-tools-walk', dict(receipt=receipt, compared=walk.compared, dialogs=walk.dialogs))
    return dict(home=kept, before=confirmed, staged=staged, sites=sites)


def boot_console(vm, guest, password, stage, commands, *, no_foot=False):
    vm.keyboard(guest, stage, 'de')
    console = vm.Console(guest, commands=commands)
    console.login(password, stage)
    console.become_root(password, stage)
    if no_foot:
        r28.no_foot(console, guest, stage, vm, reopen=probes.open_terminal)
    else:
        terminal(guest, stage, vm)
    checked = console.run('check', stage + '-check')
    return console, vm.result_lines(checked)


def confirm(vm, guest, console, stage, lines, change, reference, order, candidate):
    fresh = title(vm, console, stage, order)
    expected = change + ' to ' + reference + ' confirmed after the restart'
    assert expected in lines + fresh, 'STOP: the exact ' + change.lower() + ' was not confirmed'
    installed_tools(vm, guest, stage + '-tools', candidate['fingerprint'], candidate['commits']['announced'], candidate['repository'])
    return expected


def recover_update(vm, guest, password, stage, snapshot, stock, r28_order, r29_order, update, candidate, *, retry):
    """Follow the failed-update card when the running system is still R28."""
    ds = [row['container-image-reference-digest'] for row in snapshot['rpm']['deployments']]
    applied = ds == r29_order
    order = r29_order if applied else r28_order
    running = r29_order[1]
    retained = {digest: update['staged'][digest] for digest in order} if applied else update['before']
    shape(vm, guest, stage + '-recovery', stock, order, running, retained, queued=applied, snapshot=snapshot)
    console, lines = boot_console(vm, guest, password, stage + '-recovery', candidate['commands'])
    title(vm, console, stage + '-recovery', order)
    r28.home_unchanged(update['home'], r28.home(guest, stage + '-recovery', vm, write_saves=True), prism_started=True)
    change = 'Update to ' + candidate['reference']
    if not applied:
        assert change + ' was not applied: the deployments are as before it, and nothing is waiting' in lines, \
            'STOP: failed update has an unrecognized outcome; get Help'
        raise AssertionError('STOP: R29 was not applied; keep the result and get Help')
    assert change + ' is in place and has not started yet' in lines and any(line.endswith('this start was not the default') for line in lines), \
        'STOP: could not confirm the staged update is in place; get Help'
    assert retry, 'STOP: R29 still did not start after the recovery restart; get Help'
    save_gate(vm, guest, stage + '-recovery-reboot')
    console.run('reboot', stage + '-recovery-reboot')


def complete_candidate(vm, audit, password, hashed, route, release, qualifying, update):
    td, candidate = vm.td, qualifying.candidate
    d28, d29 = (reference.split('@')[1] for reference in (release, candidate['reference']))
    stock, stock_digest = route['stock'], route['stock_digest']
    first, back = [d29, d28, stock_digest], [d28, d29, stock_digest]
    retained = {digest: update['staged'][digest] for digest in first}
    r28_order = [d28, route['new_digest'], stock_digest]
    receipt = dict(status='not-qualifying', equality=qualifying.equality, tools=candidate['fingerprint'], staged=d29)
    assert audit.windows_default is True, 'STOP: Windows must remain the firmware default'
    # Each start_installed is the VM's audited one-time F12 -> Bazzite selection.
    for stage in ('release-29', 'release-29-retry'):
        guest = td.start_installed(password, hashed, stage)
        try:
            snapshot = vm.kb.deployment_snapshot(guest, stage)
            booted = vm.sw.booted_digest(snapshot['bootc'])
            if stage == 'release-29':
                receipt['first_booted'] = booted
                if booted != d29:
                    td.save('release-29-deployment-walk', receipt)
            if booted == d28:
                recover_update(vm, guest, password, stage, snapshot, stock, r28_order, first, update, candidate,
                               retry=stage == 'release-29')
                continue
            shape(vm, guest, stage, stock, first, d29, retained, snapshot=snapshot)
            console, lines = boot_console(vm, guest, password, stage, candidate['commands'], no_foot=True)
            updated = confirm(vm, guest, console, stage, lines, 'Update', candidate['reference'], first, candidate)
            r28.home_unchanged(update['home'], r28.home(guest, stage, vm, write_saves=True), prism_started=True)
            probes.session(guest, stage, vm, '29')
            probes.first_use(guest, stage, vm, update['sites'])
            probes.control(guest, stage, vm, expected_sites=update['sites'])
            previous = console.run('previous', 'r29-previous')
            assert 'Previous AresOS queued for the next start ' + release in vm.result_lines(previous)
            shape(vm, guest, 'r29-previous-queued', stock, back, d29, retained, queued=True)
            title(vm, console, 'r29-previous', back)
            console.run('reboot', 'r29-previous-reboot')
            break
        finally:
            vm.finish(guest, audit, stage)

    stage = 'previous-28'
    guest = td.start_installed(password, hashed, stage)
    try:
        shape(vm, guest, stage, stock, back, d28, retained)
        console, lines = boot_console(vm, guest, password, stage, candidate['commands'])
        returned = confirm(vm, guest, console, stage, lines, 'Return', release, back, candidate)
        r28.home_unchanged(update['home'], r28.home(guest, stage, vm, write_saves=True), prism_started=True)
        probes.session(guest, stage, vm, '28')
        probes.control(guest, stage, vm)
        probes.checked_sites(guest, stage, vm, update['sites'])
        forward = console.run('forward', 'r29-forward')
        assert 'Newest installed AresOS starts next ' + candidate['reference'] in vm.result_lines(forward)
        shape(vm, guest, 'r29-forward-queued', stock, first, d28, retained, queued=True)
        title(vm, console, 'r29-forward', first)
        save_gate(vm, guest, 'r29-forward-reboot')
        console.run('reboot', 'r29-forward-reboot')
    finally:
        vm.finish(guest, audit, stage)

    stage = 'final-29'
    guest = td.start_installed(password, hashed, stage)
    try:
        shape(vm, guest, stage, stock, first, d29, retained)
        console, lines = boot_console(vm, guest, password, stage, candidate['commands'])
        forwarded = confirm(vm, guest, console, stage, lines, 'Forward', candidate['reference'], first, candidate)
        r28.home_unchanged(update['home'], r28.home(guest, stage, vm, write_saves=True), prism_started=True)
        probes.session(guest, stage, vm, '29')
        probes.control(guest, stage, vm, expected_sites=update['sites'])
        print('CONTROL_CHROME_SITES_REBOOT_PASS')
        r28.game_scope(guest, stage, vm)
        console.logout(stage + '-logout')
    finally:
        vm.finish(guest, audit, stage)
    td.marker(audit, 'final-unattended-windows')
    td.marker(audit, 'final-detached-windows', detached=True)
    first_start_passed = receipt['first_booted'] == d29
    td.save('release-29-deployment-walk', dict(receipt, status='passed' if first_start_passed else 'not-qualifying',
        booted=d29, retired=route['new_digest'], identities=retained, home_preserved=True,
        confirmations=[updated, returned, forwarded], protected_disk_audits=True,
        chrome_sites_sha256=update['sites'], control_checks=list(probes.SERVICE_CHECKS + probes.CHROME_CHECKS),
        game_scope_passed=True))
    assert first_start_passed, 'STOP: R29 did not boot on the first unattended start'


def rehearsal(vm, audit, media, password, hashed, daily_password, version_2, prepared, *, qualifying=None):
    """Reuse the R28 route through first confirmation and retain the baseline evidence."""
    assert qualifying is None or qualifying.equality['equal'] is True, 'STOP: candidate equality is required before rehearsal'
    td = vm.td
    record = prepared.records['28']
    standin = qualifying.historical if qualifying else r28.standin_origin(td.WORK / 'stand-in-28', record)
    assert standin['fingerprint'] == TOOLS_V5, 'STOP: stand-in differs from released v5'
    real = r28.real_commit(TOOLS_V5_COMMIT, standin)
    assert real['equal'] is True
    r27, release = (json.loads(prepared.records[version])['reference'] for version in ('27', '28'))
    boot = SimpleNamespace(**r28.bootstrap_of())
    route, staged, walk, _ = r28.stage_update(vm, audit, media, password, hashed, daily_password,
        version_2, r27, release, standin, commands=prepared.commands, bootstrap=boot)
    old = json.loads(prepared.records['13'])['reference']
    assert (route['old'], route['new']) == (old, r27), 'STOP: the historical route used different releases'
    assert route['stock_digest'] == stock_image.base()['digest'], 'STOP: wrong corrected stock digest'

    guest = td.start_installed(password, hashed, 'release-28')
    try:
        before_check = terminal if qualifying else None
        console, identities = r28.confirm_boot(vm, guest, password, route, release,
                                               commands=prepared.commands[5], before_check=before_check)
        digest = release.split('@')[1]
        expected = [digest, route['new_digest'], route['stock_digest']]
        snapshot = vm.kb.deployment_snapshot(guest, 'release-28-confirmed')
        confirmed, booted = vm.deployment_shape(snapshot, route['stock'], expected)
        assert booted == digest and confirmed == identities == {key: staged[key] for key in expected}, \
            'STOP: R28, retained R27 or pinned stock identity changed'
        for slot, image_digest in zip(('booted', 'rollback'), expected[:2]):
            observed = snapshot['bootc']['status'][slot]
            ostree = observed['ostree']
            assert observed['image']['imageDigest'] == image_digest and \
                (ostree['checksum'], ostree['deploySerial'], ostree['stateroot']) == confirmed[image_digest], \
                'STOP: bootc disagrees with the confirmed ' + slot + ' deployment'
        installed = installed_v5(vm, guest)
        if qualifying:
            assert served_webui(td.EVIDENCE) == ui_hashes()
            update = stage_candidate(vm, guest, console, route, release, confirmed, daily_password, qualifying.candidate)
        else:
            console.logout('release-28-baseline-logout')
    finally:
        vm.finish(guest, audit, 'release-28')
    if qualifying:
        assert baseline_inputs() == prepared.inputs, 'STOP: baseline inputs changed during the rehearsal'
        complete_candidate(vm, audit, password, hashed, route, release, qualifying, update)
        return
    td.marker(audit, 'final-unattended-windows')
    td.marker(audit, 'final-detached-windows', detached=True)

    assert baseline_inputs() == prepared.inputs, 'STOP: baseline inputs changed during the rehearsal'
    receipt = dict(status='passed', commit=prepared.registry['commit'], registry=prepared.registry, inputs=prepared.inputs,
        iso=prepared.iso, webui=served_webui(td.EVIDENCE), tools=list(prepared.tools.values()), booted=release,
        deployments=expected, identities=confirmed, stock_pinned=True, transaction_idle=True, r13_retired=True,
        tools_phase=installed['phase'], outcome_pending=False, protected_disk_audits=True)
    td.save('release-29-baseline-walk', dict(real=real, compared=walk.compared, stages=walk.stages, dialogs=walk.dialogs))
    BASELINE_RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_RECEIPT.write_text(json.dumps(receipt, indent=2) + '\n')
    print('PASS historical R29 baseline through confirmed R28 with tools v5')


def check_receipt(vm, receipt):
    """Require the reviewed preflight artifact again when the historical inputs change."""
    assert receipt['status'] == 'passed' and receipt['inputs'] == baseline_inputs(), \
        'STOP: rerun the historical R29 baseline preflight on the current inputs'
    registry = receipt['registry']
    old_run = {key: registry[key] for key in ('commit', 'run_id', 'attempt')}
    assert receipt['commit'] == old_run['commit']
    records = registry_auth.historical_records()
    registry_auth.check_baseline_registry(registry, records, old_run)
    tools, _ = historical_tools(vm, records)
    release = json.loads(records['28'])['reference']
    digest_27 = json.loads(records['27'])['reference'].split('@')[1]
    expected = [release.split('@')[1], digest_27, stock_image.base()['digest']]
    ids = receipt['identities']
    assert receipt['booted'] == release and receipt['deployments'] == expected and set(ids) == set(expected)
    for identity in ids.values():
        checksum, serial, stateroot = identity
        assert re.fullmatch('[0-9a-f]{64}', checksum) and type(serial) is int and serial >= 0
        assert re.fullmatch('[a-zA-Z0-9_-]+', stateroot)
    assert all(receipt[key] is True for key in ('stock_pinned', 'r13_retired', 'transaction_idle', 'protected_disk_audits'))
    assert receipt['tools'] == list(tools.values()) and receipt['tools_phase'] in (None, 'complete')
    assert receipt['outcome_pending'] is False
    live = vm.td.LIVE
    assert receipt['iso'] == dict(filename=live['filename'], sha256=live['sha256'], bytes=live['bytes'])
    assert receipt['webui'] == ui_hashes()


if __name__ == '__main__':
    import owner_vm

    action, receipt_path = sys.argv[1:]
    assert action == 'check-receipt'
    check_receipt(owner_vm, read_json(receipt_path))
    print('PASS recorded historical R29 baseline matches the current inputs')
