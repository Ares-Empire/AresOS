"""Hash every installed runtime input. Qualification data is intentionally separate."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def inputs(root=ROOT):
    control = root / 'control'
    for directory in ['aresos_control', 'generated', 'settings', 'packaging', 'chrome/extension', 'chrome/packaging']:
        base = control / directory
        if not base.is_dir():
            raise ValueError('Missing installed runtime directory: ' + directory)
        for path in sorted(base.rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts:
                yield path
    for name in ['launch.py', 'requirements.lock', 'chrome/native_host.py', 'chrome/build.py']:
        yield control / name


def build_hash(root=ROOT):
    digest = hashlib.sha256()
    for path in sorted(inputs(root)):
        digest.update(str(path.relative_to(root)).encode() + b'\0')
        digest.update(path.read_bytes() + b'\0')
    return digest.hexdigest()


if __name__ == '__main__':
    print(build_hash())
