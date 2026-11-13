"""Bind source bytes after Git's declared checkout conversion, never blob bytes.

An isolated index replays the repository attributes without checking out over
the owner's files or depending on this machine's autocrlf/global attributes.
The VM's independent check still hashes its actual checked-out files.
"""
import hashlib
import json
import os
import pathlib
import subprocess
import tempfile


def _names(paths):
    names = list(paths)
    assert names and len(names) == len(set(names)), 'Missing or duplicate source paths'
    for name in names:
        path = pathlib.PurePosixPath(name)
        assert (isinstance(name, str) and path.parts and not path.is_absolute()
                and path.as_posix() == name and '..' not in path.parts
                and '.git' not in path.parts and '\\' not in name and ':' not in name), 'Unsafe source path'
    return names


def _bytes(root, name):
    path = root / name
    assert path.is_file() and not path.is_symlink(), 'Missing or linked source: ' + name
    assert path.resolve().is_relative_to(root.resolve()), 'Source escapes repository'
    return path.read_bytes()


def _attributes(root, names):
    paths = {'.gitattributes'}
    for name in names:
        paths.update((parent / '.gitattributes').as_posix()
                     for parent in pathlib.PurePosixPath(name).parents
                     if (root / parent / '.gitattributes').is_file())
    return sorted(paths)


def records(root, paths, *, contents=None, attributes=None):
    """Replay add/checkout-index for current files or explicitly supplied blobs."""
    root = pathlib.Path(root)
    names = _names(paths)
    attributes = ({p: _bytes(root, p) for p in _attributes(root, names)}
                  if attributes is None else attributes)
    assert '.gitattributes' in attributes, 'Repository attributes are required'
    _names(attributes)
    data = {name: _bytes(root, name) for name in names} if contents is None else dict(contents)
    assert set(data) == set(names), 'Incomplete source snapshot'
    for name, raw in attributes.items():
        assert name not in data or data[name] == raw, 'Attribute snapshot disagrees'
        data[name] = raw
    scratch = root / '.work/14/source-checkouts'
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as temporary:
        base = pathlib.Path(temporary)
        tree, output = base / 'input', base / 'checkout'
        tree.mkdir(); output.mkdir()
        empty = base / 'empty-config'; empty.write_bytes(b'')
        # These settings apply only to the scratch Git process, never the real
        # repository or its pre-push hook. No network/credential operation runs.
        env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
        env.update(GIT_CONFIG_NOSYSTEM='1', GIT_ATTR_NOSYSTEM='1', GIT_CONFIG_GLOBAL=str(empty))

        def git(*args):
            result = subprocess.run(['git', '-c', 'core.autocrlf=false', '-c',
                                     'core.attributesFile=' + str(empty), '-C', str(tree), *args],
                                    env=env, capture_output=True, timeout=120)
            assert result.returncode == 0, 'Checkout replay failed: ' + result.stderr.decode(errors='replace')
            return result.stdout

        git('init', '-q', '--template=')
        for name, raw in data.items():
            path = tree / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        git('add', '--all', '--', '.')
        git('checkout-index', '--all', '--prefix=' + output.as_posix() + '/')
        return [dict(sha256=hashlib.sha256((output / name).read_bytes()).hexdigest(), path=name)
                for name in names]


def verify(root, rows, **kwargs):
    assert rows and all(list(row) == ['sha256', 'path'] for row in rows), 'Invalid source records'
    actual = records(root, [row['path'] for row in rows], **kwargs)
    mismatches = [row['path'] for row, replay in zip(rows, actual) if row != replay]
    assert not mismatches, 'Checkout source binding mismatch: ' + ', '.join(mismatches)
    return len(rows)


def verify_git(root, rows, ref='HEAD'):
    """Replay a committed tree, or the staged index when ref is None."""
    root = pathlib.Path(root)
    names = _names(row['path'] for row in rows)

    def blob(name):
        spec = ':' + name if ref is None else ref + ':' + name
        return subprocess.check_output(['git', '-C', str(root), 'show', spec], timeout=120)

    attrs = {name: blob(name) for name in _attributes(root, names)}
    return verify(root, rows, contents={name: blob(name) for name in names}, attributes=attrs)


def active_tables(root):
    """Current qualification, probe and preflight records; history stays intact."""
    root = pathlib.Path(root)
    # The newest VM rehearsal's bindings are current: package 27's once its
    # rehearsal passed and recorded them, before that package 16's.
    staged = root / 'os/manifest/ci/27/source-bindings.json'
    if not staged.exists():
        staged = root / 'os/manifest/ci/16/source-bindings.json'
    if staged.exists():
        record = json.loads(staged.read_text())
        return [(row['name'],row['sources']) for row in record['tables']]
    walk_path = root / 'os/manifest/ci/14/host-walk/result.json'
    walk = json.loads(walk_path.read_text())
    prep_path = root / walk['current_verification']
    prep = json.loads(prep_path.read_text())
    folder = prep_path.parent
    tables = [(walk_path.relative_to(root).as_posix(), walk['sources']),
              (prep_path.relative_to(root).as_posix(), prep['source_bindings'])]
    for name in ('probe-walk.json', 'walk.json'):
        path = folder / name
        tables.append((path.relative_to(root).as_posix(), json.loads(path.read_text())['sources']))
    if 'local_tool_bindings' in prep:
        tables.append(('preflight archived source tools',
                       [dict(sha256=row['sha256'], path=(folder / row['archive']).relative_to(root).as_posix())
                        for row in prep['local_tool_bindings']]))
    files = folder / 'files.json'
    if files.exists():
        tables.append((files.relative_to(root).as_posix(), json.loads(files.read_text())['files']))
    return tables


def merge(tables):
    """Replay shared sources once, refusing conflicting records across tables."""
    combined = {}
    for name, rows in tables:
        assert rows and all(list(row) == ['sha256', 'path'] for row in rows), 'Invalid table: ' + name
        _names(row['path'] for row in rows)
        for row in rows:
            path = row['path']
            assert path not in combined or combined[path] == row, 'Conflicting checkout record: ' + path
            combined[path] = row
    return [combined[path] for path in sorted(combined)]
