"""Deterministic owner payload, used by Windows and the disposable VM harness.

No hardware queries, privilege changes, mounts or credentials in this module.
"""
import hashlib
import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAYLOAD = {'at': 'os/owner-tools/at', 'owner.py': 'os/owner-tools/owner.py',
           'media.py': 'os/owner-tools/media.py', 'release.json': 'os/manifest/release.json'}
for name in ('pause-stock-updates', 'pin-stock', 'system-keyboard', 'stock-session',
             'switch', 'verify', 'rollback', 'default-stock'):
    PAYLOAD['release/' + name + '.sh'] = 'os/release/' + name + '.sh'


def manifest(root=ROOT):
    return {name: hashlib.sha256((root / source).read_bytes()).hexdigest()
            for name, source in sorted(PAYLOAD.items())}


def build(destination, root=ROOT):
    destination = pathlib.Path(destination)
    if destination.exists():
        raise ValueError('STOP: preserve existing bundle; use an empty destination')
    destination.mkdir(parents=True)
    for name, source in sorted(PAYLOAD.items()):
        target = destination / name
        target.parent.mkdir(exist_ok=True)
        shutil.copyfile(root / source, target)
    raw = (json.dumps(manifest(root), sort_keys=True, indent=2) + '\n').encode()
    (destination / 'SHA256.json').write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def check(destination, root=ROOT):
    destination = pathlib.Path(destination)
    expected = (json.dumps(manifest(root), sort_keys=True, indent=2) + '\n').encode()
    assert (destination / 'SHA256.json').read_bytes() == expected, 'Regenerate the reviewed payload'
    assert {p.relative_to(destination).as_posix() for p in destination.rglob('*') if p.is_file()} == set(PAYLOAD) | {'SHA256.json'}
    for name, source in PAYLOAD.items():
        assert (destination / name).read_bytes() == (root / source).read_bytes(), 'Payload differs: ' + name
    return hashlib.sha256(expected).hexdigest()


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
            (destination / 'SHA256.json').write_text(json.dumps(manifest(), sort_keys=True, indent=2) + '\n', newline='\n')
        print('PASS bundle manifest SHA256 ' + check(destination))
    else:
        print('PASS bundle manifest SHA256 ' + build(sys.argv[1]))
