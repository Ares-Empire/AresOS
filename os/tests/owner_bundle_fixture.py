"""Copy the reviewed manifest entries, never an import-contaminated source tree."""
import hashlib
import json
import pathlib
import re
import shutil


def copy_bundle(source, destination):
    source, destination = pathlib.Path(source), pathlib.Path(destination)
    raw = (source / 'SHA256.json').read_bytes()
    rows = json.loads(raw)
    assert isinstance(rows, list) and rows
    names = []
    for row in rows:
        assert list(row) == ['sha256', 'path'] and re.fullmatch('[0-9a-f]{64}', row['sha256'])
        name = pathlib.PurePosixPath(row['path'])
        assert not name.is_absolute() and name.parts and '..' not in name.parts and '\\' not in row['path']
        assert name.as_posix() == row['path']
        assert row['path'] not in names and row['path'] not in ('SHA256.json', 'SHA256SUMS')
        names.append(row['path'])
    sums = ''.join(row['sha256'] + '  ' + row['path'] + '\n' for row in rows)
    sums += hashlib.sha256(raw).hexdigest() + '  SHA256.json\n'
    assert (source / 'SHA256SUMS').read_bytes() == sums.encode()
    assert not destination.exists() and not destination.is_symlink()
    destination.mkdir(parents=True)
    for name in names + ['SHA256.json', 'SHA256SUMS']:
        origin, target = source / name, destination / name
        assert origin.is_file() and not origin.is_symlink()
        if name in names:
            expected = rows[names.index(name)]['sha256']
            assert hashlib.sha256(origin.read_bytes()).hexdigest() == expected
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(origin, target)
    return hashlib.sha256(sums.encode()).hexdigest()
