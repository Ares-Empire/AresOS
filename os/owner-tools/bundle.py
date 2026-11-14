"""Deterministic owner payload, used by Windows and the disposable VM harness.

No hardware queries, privilege changes, mounts or credentials in this module.
"""
import hashlib
import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAYLOAD = {'at': 'os/owner-tools/at', 'owner.py': 'os/owner-tools/owner.py',
           'media.py': 'os/owner-tools/media.py', 'release.json': 'os/manifest/release.json',
           'history.json': 'os/owner-tools/history.json'}
# rollback.sh, default-stock.sh and previous.sh left the payload in 22c: every
# reorder runs start-next.sh. They stay in os/release, byte-identical, for the
# older CI modes that read them.
for name in ('pause-stock-updates', 'pin-stock', 'system-keyboard', 'stock-session',
             'switch', 'verify', 'update', 'start-next'):
    PAYLOAD['release/' + name + '.sh'] = 'os/release/' + name + '.sh'


def manifest(root=ROOT):
    return [dict(sha256=hashlib.sha256((root / source).read_bytes()).hexdigest(), path=name)
            for name, source in sorted(PAYLOAD.items())]


def manifests(root=ROOT):
    rows = manifest(root)
    raw = (json.dumps(rows, indent=2) + '\n').encode()
    sums = ''.join(row['sha256'] + '  ' + row['path'] + '\n' for row in rows)
    sums += hashlib.sha256(raw).hexdigest() + '  SHA256.json\n'
    return raw, sums.encode()


def build(destination, root=ROOT):
    destination = pathlib.Path(destination)
    if destination.exists():
        raise ValueError('STOP: preserve existing bundle; use an empty destination')
    destination.mkdir(parents=True)
    for name, source in sorted(PAYLOAD.items()):
        target = destination / name
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(root / source, target)
    raw, sums = manifests(root)
    (destination / 'SHA256.json').write_bytes(raw)
    (destination / 'SHA256SUMS').write_bytes(sums)
    return hashlib.sha256(sums).hexdigest()


def check(destination, root=ROOT):
    destination = pathlib.Path(destination)
    expected, sums = manifests(root)
    assert (destination / 'SHA256.json').read_bytes() == expected, 'Regenerate the reviewed payload'
    assert (destination / 'SHA256SUMS').read_bytes() == sums, 'Regenerate the system-tool manifest'
    assert {p.relative_to(destination).as_posix() for p in destination.rglob('*') if p.is_file()} == set(PAYLOAD) | {'SHA256.json', 'SHA256SUMS'}
    for name, source in PAYLOAD.items():
        assert (destination / name).read_bytes() == (root / source).read_bytes(), 'Payload differs: ' + name
    return hashlib.sha256(sums).hexdigest()


if __name__ == '__main__':
    import sys
    if sys.argv[1:] == ['--refresh']:
        destination = ROOT / 'os/owner-tools/payload'
        if not destination.exists():
            build(destination)
        else:
            for name, source in PAYLOAD.items():
                target = destination / name
                assert not target.is_symlink()
                target.parent.mkdir(exist_ok=True)
                target.write_bytes((ROOT / source).read_bytes())
            raw, sums = manifests()
            (destination / 'SHA256.json').write_bytes(raw)
            (destination / 'SHA256SUMS').write_bytes(sums)
        print('PASS bundle manifest SHA256 ' + check(destination))
    else:
        print('PASS bundle manifest SHA256 ' + build(sys.argv[1]))
