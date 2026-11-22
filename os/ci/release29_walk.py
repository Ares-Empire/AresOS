"""Package 331's historical rehearsal through the first confirmed R28 boot."""
import hashlib
import json
import pathlib
import re
import shlex
import sys
from types import SimpleNamespace

import installer_inspect
import installer_webui
import registry_auth
import release28_walk as r28
import stock_image

TOOLS_V5_COMMIT = '6ae4da41934821e5bcfda855ce057bc355900161'
TOOLS_V5 = 'df89ac336e13db84934505551ba28163cbd60fa5b3b9fb0ec97b9585945896c6'
TOOLS_V5_TREE = '8f68ef346c33c2a388581f79797b8775df2135a6'
R13_SQUASH = '775be05b7f0d6971cbdc8a3bd1aea617fc008c4d'
R13_IMAGE_PATHS = ('os/Containerfile.keyboard', 'os/.containerignore', 'os/packages.lock.json',
                   'os/config', 'os/policy', 'os/manifest/base.json', 'os/keys', 'os/tests/audit.py')
BASELINE_RECEIPT = pathlib.Path('evidence/release-29-baseline.json')
HOST_WALK_RECEIPT = 'os/manifest/ci/331/host-walk.json'
PAYLOAD = 'os/owner-tools/payload'
# This tracks the historical route's checkout inputs. Image sources, released tools and
# old release records are checked at their pinned Git objects or against their record hashes.
BASELINE_PATHS = (
    '.gitattributes', '.github/workflows/os-image.yml', 'docs/install-tools/OwnerTools.psm1',
    'os/ci/disk_audit.py', 'os/ci/firmware_contract.py', 'os/ci/greeter.py', 'os/ci/grub_bls.py',
    'os/ci/install-tools.sh', 'os/ci/installer_inspect.py',
    'os/ci/installer_webui.py', 'os/ci/keyboard_diagnostic.py', 'os/ci/keyboard_entries.py',
    'os/ci/keyboard_proof.py', 'os/ci/keyboard_vm.py', 'os/ci/offline_webui.py',
    'os/ci/prepare_two_disks.py', 'os/ci/qmp.py', 'os/ci/registry_auth.py', 'os/ci/rehearsal_auth.py',
    'os/ci/release28_walk.py', 'os/ci/release29_walk.py', 'os/ci/reorder_probe.py',
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


def baseline_inputs():
    tracked = r28.git('ls-files', '-z', '--', *INPUT_PATHSPECS).decode().split('\0')[:-1]
    paths = set(BASELINE_PATHS) | set(tracked)
    paths.update(f'os/manifest/releases/{version}.json' for version in registry_auth.BASELINE_RECORDS)
    # Step 4 adds the host walk receipt that the hosted owner route requires.
    if pathlib.Path(HOST_WALK_RECEIPT).exists():
        paths.add(HOST_WALK_RECEIPT)
    return [dict(sha256=sha256(pathlib.Path(path).read_bytes()), path=path) for path in sorted(paths)]


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


def prepare(vm):
    """Resolve historical inputs and check same-run registry and ISO evidence before starting the guest."""
    registry_auth.require_baseline_dispatch()
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
    source = INSTALLED.replace('@DIRECTORY@', repr('tools-' + TOOLS_V5))
    observed = guest.capture_json('release-28-baseline-tools', vm.sw.framed('python3 -c ' + shlex.quote(source)))
    paths = r28.git('ls-tree', '-r', '--name-only', TOOLS_V5_COMMIT, PAYLOAD).decode().splitlines()
    expected = {path.removeprefix(PAYLOAD + '/'): sha256(vm.git_blob(TOOLS_V5_COMMIT, path)) for path in paths}
    assert observed['entry'] == 'tools-' + TOOLS_V5 + '/at' and observed['files'] == expected, \
        'STOP: installed tools differ from released v5'
    assert observed['phase'] in (None, 'complete') and observed['pending'] is False, \
        'STOP: baseline tools or deployment change remains open'
    return observed


def rehearsal(vm, audit, media, password, hashed, daily_password, version_2, prepared):
    """Reuse the R28 route through first confirmation and retain the baseline evidence."""
    td = vm.td
    record = prepared.records['28']
    standin = r28.standin_origin(td.WORK / 'stand-in-28', record)
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
        console, identities = r28.confirm_boot(vm, guest, password, route, release, commands=prepared.commands[5])
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
        console.logout('release-28-baseline-logout')
    finally:
        vm.finish(guest, audit, 'release-28')
    td.marker(audit, 'final-unattended-windows')
    td.marker(audit, 'final-detached-windows', detached=True)

    assert baseline_inputs() == prepared.inputs, 'STOP: baseline inputs changed during the rehearsal'
    receipt = dict(status='passed', commit=prepared.registry['commit'], registry=prepared.registry, inputs=prepared.inputs,
        iso=prepared.iso, webui=served_webui(td.EVIDENCE), tools=list(prepared.tools.values()), booted=release,
        deployments=expected, identities=confirmed, stock_pinned=True, transaction_idle=True, r13_retired=True,
        tools_phase=installed['phase'], outcome_pending=False, protected_disk_audits=True)
    td.save('release-29-baseline-walk', dict(real=real, compared=walk.compared, stages=walk.stages, dialogs=walk.dialogs))
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
