"""Control's state in a booted AresOS, for the release rehearsal (packages 18c and 18c-b).

Needs nothing but the image itself and its OpenSSL. Run it as
root in the booted guest, after the update from the previous release:

    python3 -I release_checks.py [check ...]        (or its text piped to: python3 -I - [check ...])

It prints one JSON object (every check with its values), the excluded-sites digest when checked,
then CONTROL_RELEASE_CHECKS_PASS, or
CONTROL_RELEASE_CHECKS_FAILED with the failed checks' names and exit status 1. Every check runs even when an
earlier one fails. With names, only those checks run. The check_build=control VM test runs it through the CI layer
(os/ci/control/actions.py), so the same file is proven there.

On the laptop systemd-sysusers creates aresos-tools at the first boot of the new release, where a taken 250 would
quietly become another number; the state folders in /var keep the owner they had. Only a rehearsal sees that.
"""
import grp
import hashlib
import json
import os
import pathlib
import pwd
import re
import stat
import struct
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

SERVICE_USER = 'aresos-tools'
SERVICE_ID = 250
UNIT = 'aresos-toold.service'
ROOT = pathlib.Path('/')
RECORD = 'usr/share/aresos/manifest/control.json'
SERVICE_CONFIG = 'usr/share/aresos/control/service.json'
PROXY_CONFIG = 'usr/share/aresos/control/proxy.json'
MANAGED = 'etc/claude-code'
# ostree keeps the image's own /etc in /usr/etc; /etc is the deployment's merge.
IMAGE_ETC = 'usr/etc'
STATE = {'var/lib/aresos-tools': 0o700, 'var/lib/aresos-operation-evidence': 0o700, 'run/aresos-tools': 0o711}
CHROME_ETC = 'etc/opt/chrome'
BUNDLE = 'usr/share/aresos/chrome'
CHROME_LINKS = {f'{CHROME_ETC}/policies/managed/aresos.json': f'/{BUNDLE}/policy.json',
                f'{CHROME_ETC}/native-messaging-hosts/org.aresos.chrome.json': f'/{BUNDLE}/native-host.json'}
KDE_HOST = f'{CHROME_ETC}/native-messaging-hosts/org.kde.plasma.browser_integration.json'
CHROME_ID = re.compile(r'(?<![a-z0-9])[a-p]{32}(?![a-z0-9])', re.ASCII)
SITES = 'var/lib/aresos-control/chrome-excluded-sites.json'
GH = 'usr/bin/gh'
GH_LOCK = 'usr/share/aresos/manifest/gh.lock.json'
CHROME_ACTION = 'usr/share/polkit-1/actions/org.aresos.control.chrome-loosen.policy'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def service_user():
    """aresos-tools has UID and GID 250, and nothing else has either."""
    user, group = pwd.getpwnam(SERVICE_USER), grp.getgrnam(SERVICE_USER)
    value = dict(uid=user.pw_uid, gid=user.pw_gid, group_gid=group.gr_gid, home=user.pw_dir, shell=user.pw_shell,
                 users_with_250=sorted({entry.pw_name for entry in pwd.getpwall() if entry.pw_uid == SERVICE_ID}),
                 groups_with_250=sorted({entry.gr_name for entry in grp.getgrall() if entry.gr_gid == SERVICE_ID}))
    ok = ((user.pw_uid, user.pw_gid, group.gr_gid) == (SERVICE_ID,) * 3
          and value['users_with_250'] == [SERVICE_USER] and value['groups_with_250'] == [SERVICE_USER])
    return ok, value


def unit(wait=90):
    """The unit is enabled and active, and its main process runs as aresos-tools."""
    deadline = time.monotonic() + wait
    while True:
        shown = subprocess.run(['systemctl', 'show', UNIT, '-p', 'ActiveState', '-p', 'SubState', '-p', 'MainPID',
                                '-p', 'NRestarts', '-p', 'UnitFileState'],
                               capture_output=True, text=True, timeout=30)
        value = dict(line.split('=', 1) for line in shown.stdout.splitlines() if '=' in line)
        if value.get('ActiveState') not in ('activating', 'reloading') or time.monotonic() > deadline:
            break
        time.sleep(1)
    pid = int(value.get('MainPID') or 0)
    status = pathlib.Path(f'/proc/{pid}/status')
    ids = {}
    if pid and status.exists():
        for line in status.read_text().splitlines():
            key, _, rest = line.partition(':')
            if key in ('Uid', 'Gid'):
                ids[key] = [int(field) for field in rest.split()]
    value['main_process_ids'] = ids
    ok = (value.get('ActiveState') == 'active' and value.get('SubState') == 'running'
          and value.get('UnitFileState') == 'enabled'
          and ids.get('Uid') == [SERVICE_ID] * 4 and ids.get('Gid') == [SERVICE_ID] * 4)
    return ok, value


def claude_code_files():
    """Agreed change 7: /etc/claude-code holds exactly its two files, equal to the image's (its /usr/etc copy and
    control.json's record), root-owned with the recorded mode; no managed-mcp.json."""
    record = json.loads((ROOT / RECORD).read_text())['files']
    expected = {name: entry for name, entry in record.items() if name.startswith('/' + MANAGED + '/')}
    folder = ROOT / MANAGED
    value = dict(present=sorted(path.name for path in folder.iterdir()), files={})
    ok = len(expected) == 2 and value['present'] == sorted(pathlib.PurePath(name).name for name in expected)
    for name, entry in sorted(expected.items()):
        path = ROOT / name.lstrip('/')
        image = ROOT / IMAGE_ETC / path.relative_to(ROOT / 'etc')
        info = path.lstat()
        row = dict(mode=f'{stat.S_IMODE(info.st_mode):04o}', owner=[info.st_uid, info.st_gid],
                   regular=stat.S_ISREG(info.st_mode), recorded=entry['sha256'],
                   sha256=sha256(path) if stat.S_ISREG(info.st_mode) else None,
                   image_sha256=sha256(image) if image.is_file() and not image.is_symlink() else None)
        value['files'][name] = row
        ok = ok and row['regular'] and row['owner'] == [0, 0] and row['mode'] == entry['mode'] and \
            row['sha256'] == row['image_sha256'] == entry['sha256']
    value['managed_mcp'] = (folder / 'managed-mcp.json').exists()
    return ok and not value['managed_mcp'], value


def folders():
    """The two folders the tools may use exist as folders of the owner (tmpfiles makes them only when missing)."""
    owner = json.loads((ROOT / SERVICE_CONFIG).read_text())['owner_uid']
    configured = json.loads((ROOT / PROXY_CONFIG).read_text())['folders']
    value = dict(owner_uid=owner, folders={})
    ok = len(configured) == 2
    for name in configured:
        path = ROOT / name.lstrip('/')
        info = path.lstat() if path.exists() or path.is_symlink() else None
        row = dict(exists=info is not None)
        if info:
            row.update(directory=stat.S_ISDIR(info.st_mode), link=stat.S_ISLNK(info.st_mode), uid=info.st_uid,
                       mode=f'{stat.S_IMODE(info.st_mode):04o}')
        value['folders'][name] = row
        ok = ok and bool(info) and row['directory'] and row['uid'] == owner
    return ok, value


def state_folders():
    """The service's state and socket folders, and everything in the state folders, belong to aresos-tools."""
    value = {}
    ok = True
    for name, mode in STATE.items():
        path = ROOT / name
        info = path.lstat()
        row = dict(directory=stat.S_ISDIR(info.st_mode), owner=[info.st_uid, info.st_gid],
                   mode=f'{stat.S_IMODE(info.st_mode):04o}', expected_mode=f'{mode:04o}')
        ok = ok and row['directory'] and row['owner'] == [SERVICE_ID] * 2 and row['mode'] == row['expected_mode']
        if name.startswith('var/'):
            entries, foreign = 0, []
            for folder, names, files in os.walk(path):
                for entry in names + files:
                    entries += 1
                    inner = os.lstat(os.path.join(folder, entry))
                    if (inner.st_uid, inner.st_gid) != (SERVICE_ID, SERVICE_ID):
                        foreign.append([os.path.relpath(os.path.join(folder, entry), path), inner.st_uid, inner.st_gid])
            row.update(entries=entries, not_owned=foreign[:20], not_owned_count=len(foreign))
            ok = ok and not foreign
        value['/' + name] = row
    return ok, value


def chrome_links():
    """The merged /etc and the image have the same two fixed links into /usr."""
    value = {}
    for name, expected in CHROME_LINKS.items():
        path = ROOT / name
        image = ROOT / IMAGE_ETC / path.relative_to(ROOT / 'etc')
        target = os.readlink(path) if path.is_symlink() else None
        image_target = os.readlink(image) if image.is_symlink() else None
        installed = (ROOT / expected.lstrip('/')).is_file()
        value['/' + name] = dict(target=target, image_target=image_target, expected=expected, installed=installed,
                                 ok=target == image_target == expected and installed)
    return all(row['ok'] for row in value.values()), value


def crx_fields(data):
    """Read the length-delimited fields in the shipped CRX3 header and RSA proof."""
    offset = 0

    def varint():
        nonlocal offset
        value = 0
        for shift in range(0, 70, 7):
            if offset == len(data):
                raise ValueError('truncated CRX3 field')
            byte = data[offset]
            offset += 1
            value |= (byte & 127) << shift
            if byte < 128:
                return value
        raise ValueError('oversized CRX3 field')

    fields = []
    while offset < len(data):
        tag, size = varint(), varint()
        if tag & 7 != 2 or offset + size > len(data):
            raise ValueError('invalid CRX3 field')
        fields.append((tag >> 3, data[offset:offset + size]))
        offset += size
    return fields


def crx_proof(data):
    """Verify the package with the embedded public key, independent of the image build's Python verifier."""
    if len(data) < 12 or data[:8] != b'Cr24\x03\0\0\0':
        raise ValueError('not CRX3')
    size = struct.unpack_from('<I', data, 8)[0]
    if not 0 < size < len(data) - 12:
        raise ValueError('invalid CRX3 header length')
    header = crx_fields(data[12:12 + size])
    if [tag for tag, _ in header] != [2, 10000]:
        raise ValueError('expected one CRX3 RSA proof')
    proof, signed = crx_fields(header[0][1]), header[1][1]
    if [tag for tag, _ in proof] != [1, 2]:
        raise ValueError('expected CRX3 public key and signature')
    public, signature = [value for _, value in proof]
    identity = hashlib.sha256(public).digest()[:16]
    if crx_fields(signed) != [(1, identity)]:
        raise ValueError('signed CRX3 ID differs from public key')
    extension_id = identity.hex().translate(str.maketrans('0123456789abcdef', 'abcdefghijklmnop'))
    signed_bytes = b'CRX3 SignedData\0' + struct.pack('<I', len(signed)) + signed + data[12 + size:]
    with tempfile.TemporaryDirectory(prefix='control-crx-') as folder:
        key, sig = pathlib.Path(folder) / 'key.der', pathlib.Path(folder) / 'signature'
        key.write_bytes(public)
        sig.write_bytes(signature)
        result = subprocess.run([str(ROOT / 'usr/bin/openssl'), 'dgst', '-sha256', '-keyform', 'DER',
                                 '-verify', str(key), '-signature', str(sig)],
                                input=signed_bytes, capture_output=True, timeout=30)
    return extension_id, result.returncode == 0


def chrome_bundle():
    """The policy, update manifest, native host, record and signed package all name the same ID."""
    record = json.loads((ROOT / RECORD).read_bytes())['chrome_extension']
    folder = ROOT / BUNDLE
    policy = json.loads((folder / 'policy.json').read_bytes())['ExtensionSettings']
    host = json.loads((folder / 'native-host.json').read_bytes())
    ns = '{http://www.google.com/update2/response}'
    apps = ET.parse(folder / 'update.xml').getroot().findall(ns + 'app')
    identity, verified = crx_proof((folder / 'extension.crx').read_bytes())
    value = dict(policy=sorted(policy), update=[app.get('appid') for app in apps], host=host['allowed_origins'],
                 recorded=record['id'], package=identity, signature_verified=verified)
    check = apps[0].find(ns + 'updatecheck') if len(apps) == 1 else None
    return (verified and value['policy'] == value['update'] == [identity] and record['id'] == identity
            and value['host'] == [f'chrome-extension://{identity}/']
            and policy[identity].get('update_url') == f'file:///{BUNDLE}/update.xml'
            and check is not None and check.get('codebase') == f'file:///{BUNDLE}/extension.crx'), value


def chrome_other_ids():
    """No stale or foreign IDs in the merged Chrome configuration. The base ships the KDE host."""
    identity = json.loads((ROOT / RECORD).read_bytes())['chrome_extension']['id']
    folder = ROOT / CHROME_ETC
    foreign = {}

    def unreadable(error):
        raise error

    for parent, directories, files in os.walk(folder, onerror=unreadable):
        for name in sorted(directories + files):
            path = pathlib.Path(parent) / name
            rel = path.relative_to(ROOT).as_posix()
            ids = set(CHROME_ID.findall(name))
            if path.is_symlink():
                target = os.readlink(path)
                ids.update(CHROME_ID.findall(target))
                path = ROOT / target.lstrip('/') if target.startswith('/') else path.parent / target
                if not path.is_file():
                    raise ValueError(f'Chrome configuration link has no regular target: /{rel}')
            if path.is_file():
                content = path.read_bytes()
                image = ROOT / IMAGE_ETC / pathlib.PurePath(KDE_HOST).relative_to('etc')
                if not (rel == KDE_HOST and image.is_file() and content == image.read_bytes()):
                    ids.update(CHROME_ID.findall(content.decode(errors='replace')))
                    if path.suffix == '.json':
                        # Scan the decoded strings too, since policy may escape characters in an ID.
                        ids.update(CHROME_ID.findall(json.dumps(json.loads(content))))
            if ids - {identity}:
                foreign['/' + rel] = sorted(ids - {identity})
    return not foreign, dict(foreign=foreign)


def chrome_sites():
    """Report the owner list's metadata and hash, without reporting any hosts."""
    path = ROOT / SITES
    info = path.lstat()
    regular = stat.S_ISREG(info.st_mode)
    gid = grp.getgrnam(SERVICE_USER).gr_gid
    value = dict(regular=regular, owner=[info.st_uid, info.st_gid], mode=f'{stat.S_IMODE(info.st_mode):04o}',
                 sha256=sha256(path) if regular else None)
    return regular and value['owner'] == [0, gid] and value['mode'] == '0640', value


def gh():
    """The binary matches the image lock and Control record before running --version as root."""
    record = json.loads((ROOT / RECORD).read_bytes())['gh']
    lock = json.loads((ROOT / GH_LOCK).read_bytes())
    pinned = re.fullmatch(r'gh-(\d+\.\d+\.\d+)-[^-]+\.x86_64', lock['nevra']).group(1)
    path = ROOT / GH
    value = dict(version=None, pinned_version=pinned, recorded=record,
                 pinned_sha256=lock['binary_sha256'], sha256=sha256(path))
    if value['sha256'] != value['pinned_sha256'] or record['binary_sha256'] != value['sha256']:
        return False, value
    result = subprocess.run([str(path), '--version'], capture_output=True, text=True, timeout=30)
    version = re.match(r'gh version (\S+)', result.stdout)
    value['version'] = version.group(1) if version else None
    return result.returncode == 0 and value['version'] == pinned == record['version'], value


def chrome_polkit():
    """The Chrome rule-loosening action equals the image's recorded file."""
    record = json.loads((ROOT / RECORD).read_bytes())['files']['/' + CHROME_ACTION]
    path = ROOT / CHROME_ACTION
    info = path.lstat()
    regular = stat.S_ISREG(info.st_mode)
    value = dict(regular=regular, mode=f'{stat.S_IMODE(info.st_mode):04o}',
                 sha256=sha256(path) if regular else None, recorded=record)
    return regular and value['mode'] == record['mode'] and value['sha256'] == record['sha256'], value


CHECKS = dict(service_user=service_user, unit=unit, claude_code_files=claude_code_files, folders=folders,
              state_folders=state_folders, chrome_links=chrome_links, chrome_bundle=chrome_bundle,
              chrome_other_ids=chrome_other_ids, chrome_sites=chrome_sites, gh=gh, chrome_polkit=chrome_polkit)


def run(names=None):
    results = {}
    for name in names or CHECKS:
        try:
            ok, value = CHECKS[name]()
        except Exception as error:
            ok, value = False, dict(error=f'{type(error).__name__}: {error}')
        results[name] = dict(ok=ok, value=value)
    return results


def main(argv):
    unknown = [name for name in argv if name not in CHECKS]
    if unknown:
        raise SystemExit(f'Unknown check: {unknown}; known: {list(CHECKS)}')
    results = run(argv)
    print(json.dumps(results, sort_keys=True), flush=True)
    sites_digest = results.get('chrome_sites', {}).get('value', {}).get('sha256')
    if sites_digest:
        print(f'CONTROL_CHROME_SITES_SHA256 {sites_digest}', flush=True)
    failed = [name for name, result in results.items() if not result['ok']]
    if failed:
        print('CONTROL_RELEASE_CHECKS_FAILED ' + ' '.join(failed), flush=True)
        return 1
    print('CONTROL_RELEASE_CHECKS_PASS', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
