"""Package 18c, REVIEW-X1 #1: the vendored dependencies in the image are the locked wheels' own files.

build.sh installs control/requirements.lock with pip into /usr/lib/aresos-control/vendor and records every path there
in control.json ("vendor"). image-checks.sh holds the installed tree to that record, and check-image.sh holds the
record's wheels to the checkout's lock. This check closes the gap between the two: apart from the build, it derives
the vendored tree from the wheels themselves and requires the record, and the tree installed in the image, to be
exactly that tree: the same paths, contents and modes.

The derived tree is the whole of /usr/lib/aresos-control, not only vendor/ (RECHECK-X1 #1). build.sh writes nothing
else there (it requires the folder absent, then pip --target and the compile fill vendor/), and no other check binds
a file there to the checkout: check-image.sh holds the record's "files" (the code, config and managed files) to
build.sh's install map, and none of them is under this folder. So a sibling of vendor/, recorded or not, has no
source and fails, as an extra file inside vendor/ does.

    vendor_check.py fetch CONTROL_JSON WHEELS   on the runner: every recorded wheel from PyPI by its file name; its
                                                SHA-256 must be the record's, which check-image.sh tied to the lock
    vendor_check.py check CONTROL_JSON WHEELS   in a throwaway container of the built image, without network: the
                                                installed tree against the record, then /usr/lib/aresos-control
                                                replaced by the expected tree, written where the build installs it,
                                                compiled with the build's command and compared with the record

What pip writes besides the wheels' files, and the rule each follows (pip 26.0.1, the image's python3-pip):
- <dist-info>/INSTALLER: "pip\\n".
- <dist-info>/REQUESTED: empty. Every wheel is named in the lock (-r), so every one is requested.
- <dist-info>/direct_url.json: never; the wheels come from the index, not from a URL, so the expected tree has none.
- bin/<name> for each console_scripts entry point: pip's script template (SCRIPT below) after "#!/usr/bin/python3".
- <dist-info>/RECORD: the wheel's own RECORD rows, a row (sha256, size) for each file above, a row without hash for a
  wheel file its RECORD doesn't list; sorted, written as CSV with CRLF line ends.
Anything without a rule here stops the check rather than passing unchecked: a .data folder, gui_scripts, a link, a
member that leaves its folder, a wheel that holds one of the generated files, two wheels writing one path.

Bytecode is made at build time: pip runs with --no-compile, then compileall --invalidation-mode checked-hash compiles
the tree in place (build.sh). It is bound by compiling the expected sources with the image's own Python and the
build's exact command (COMPILE), at the same path, and comparing the bytes: a .pyc whose header names the right
source but whose code differs fails. Modes are build.sh's: folders and anything executable 0755, the rest 0644; a
wheel member is executable when its zip mode is a regular file with an execute bit (pip's rule).

Standard library only: the fetch runs under the runner's Python, the check under the image's.
"""
import base64
import csv
import hashlib
import importlib.metadata
import io
import json
import pathlib
import re
import shutil
import stat
import subprocess
import sys
import time
import urllib.request
import zipfile

DEPENDENCIES = 'usr/lib/aresos-control'
VENDOR = f'{DEPENDENCIES}/vendor'
# build.sh's compile step, word for word (os/tests/test_control_image.py pins the two together).
COMPILE = ['/usr/bin/python3', '-I', '-m', 'compileall', '-q', '--invalidation-mode', 'checked-hash']
COMPILE_ENV = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}
# pip 26's PipScriptMaker.script_template behind distlib's shebang for /usr/bin/python3.
SCRIPT = ('#!/usr/bin/python3\n'
          'import sys\n'
          'from {module} import {import_name}\n'
          "if __name__ == '__main__':\n"
          "    sys.argv[0] = sys.argv[0].removesuffix('.exe')\n"
          '    sys.exit({func}())\n')
INDEX = 'https://pypi.org/pypi/{name}/{version}/json'
FILES_HOST = 'https://files.pythonhosted.org/'
WHEEL_FILE = re.compile(r'[A-Za-z0-9_.+!-]+\.whl')


class Mismatch(Exception):
    """The image's vendored tree or its record is not what the locked wheels install."""


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def record_digest(data):
    return 'sha256=' + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode('ascii').rstrip('=')


def member_path(name):
    """A wheel member's path, refused unless it is plain and stays inside its folder."""
    parts = name.split('/')
    if name.startswith('/') or '\\' in name or any(part in ('', '.', '..') for part in parts):
        raise Mismatch(f'wheel member {name!r}: not a plain relative path')
    return name


def wheel_files(path):
    """{path under the vendor folder: (bytes, mode)}: what pip --target writes for one wheel (the rules above)."""
    with zipfile.ZipFile(path) as archive:
        members = [info for info in archive.infolist() if not info.filename.endswith('/')]
        names = [member_path(info.filename) for info in members]
        if len(set(names)) != len(names):
            raise Mismatch(f'{path.name}: a member is in the wheel twice')
        info_dirs = {name.split('/')[0] for name in names if name.split('/')[0].endswith('.dist-info')}
        if len(info_dirs) != 1:
            raise Mismatch(f'{path.name}: {len(info_dirs)} .dist-info folders')
        info_dir = info_dirs.pop()
        files = {}
        for info in members:
            if info.filename.split('/')[0].endswith('.data'):
                raise Mismatch(f'{path.name}: {info.filename}: no rule for a .data folder')
            # Zip writers may leave the file type out (Python's writestr does); a link or a folder has no rule.
            mode = info.external_attr >> 16
            if stat.S_IFMT(mode) not in (0, stat.S_IFREG):
                raise Mismatch(f'{path.name}: {info.filename}: not a regular file ({mode:o})')
            executable = bool(mode and stat.S_ISREG(mode) and mode & 0o111)
            files[info.filename] = (archive.read(info), 0o755 if executable else 0o644)
        record_text = files[f'{info_dir}/RECORD'][0].decode('utf-8')
        distribution = importlib.metadata.PathDistribution(zipfile.Path(archive, f'{info_dir}/'))
        generated = {}
        for entry in distribution.entry_points:
            if entry.group == 'gui_scripts':
                raise Mismatch(f'{path.name}: no rule for gui_scripts')
            if entry.group != 'console_scripts':
                continue
            if not entry.attr or re.fullmatch(r'(pip|easy_install)([-.0-9]*)', entry.name):
                raise Mismatch(f'{path.name}: no rule for the entry point {entry.name} = {entry.value}')
            script = SCRIPT.format(module=entry.module, import_name=entry.attr.split('.')[0], func=entry.attr)
            generated[f'../../bin/{member_path(entry.name)}'] = (script.encode(), 0o755)
    generated[f'{info_dir}/INSTALLER'] = (b'pip\n', 0o644)
    generated[f'{info_dir}/REQUESTED'] = (b'', 0o644)
    # pip --target installs under <home>/lib/python and moves bin/ beside it: RECORD names scripts as ../../bin/.
    installed = {name.replace('../../bin/', 'bin/', 1): value for name, value in generated.items()}
    clash = sorted(set(installed) & set(files))
    if clash:
        raise Mismatch(f'{path.name}: the wheel holds files pip generates: {clash}')
    rows = []
    for row in csv.reader(record_text.splitlines()):
        if not row:
            raise Mismatch(f'{path.name}: an empty RECORD line')
        rows.append((row[0], row[1] if len(row) > 1 else '', row[2] if len(row) > 2 else ''))
    listed = {row[0] for row in rows}
    rows += [(name, record_digest(data), str(len(data))) for name, (data, _) in generated.items()]
    rows += [(name, '', '') for name in files if name not in listed]
    text = io.StringIO()
    csv.writer(text).writerows(sorted(rows))
    files.update(installed)
    files[f'{info_dir}/RECORD'] = (text.getvalue().encode('utf-8'), 0o644)
    return files


def expected_sources(record, wheels):
    """The vendored tree before compiling, from the recorded wheels in the folder `wheels` (each one's SHA-256 the
    record's)."""
    tree, origin = {}, {}
    if not record.get('wheels'):
        raise Mismatch('control.json records no wheels')
    for wheel in record['wheels']:
        if not WHEEL_FILE.fullmatch(wheel['file']):
            raise Mismatch(f'not a wheel file name: {wheel["file"]!r}')
        path = pathlib.Path(wheels) / wheel['file']
        if sha256(path.read_bytes()) != wheel['sha256']:
            raise Mismatch(f'{wheel["file"]}: not the recorded SHA-256')
        for name, value in wheel_files(path).items():
            if name in tree:
                raise Mismatch(f'{name}: written by {origin[name]} and {wheel["file"]}')
            tree[name], origin[name] = value, wheel['file']
    return tree


def install(sources, vendor, python=COMPILE[0]):
    """Write the expected sources into a new vendor folder and compile them as the build does."""
    for name, (data, mode) in sorted(sources.items()):
        path = pathlib.Path(vendor) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        path.chmod(mode)
    subprocess.run([python, *COMPILE[1:], str(vendor)], env=COMPILE_ENV, check=True, timeout=600)


def tree_map(root):
    """Every path under /usr/lib/aresos-control as build.sh records it: {absolute path: {mode, sha256}}."""
    root = pathlib.Path(root)
    top = root / DEPENDENCIES
    found = {}
    for path in [top, *sorted(top.rglob('*'))]:
        name = '/' + path.relative_to(root).as_posix()
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode) or not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode)):
            raise Mismatch(f'{name}: neither a folder nor a regular file')
        mode = 0o755 if stat.S_ISDIR(info.st_mode) or info.st_mode & 0o111 else 0o644
        found[name] = dict(mode=f'{mode:04o}', sha256=None if stat.S_ISDIR(info.st_mode) else
                           sha256(path.read_bytes()))
    return found


def differences(recorded, actual):
    """The paths where two maps differ, each with what differs (at most 20)."""
    found = []
    for name in sorted(recorded.keys() | actual.keys()):
        if name not in actual:
            found.append(f'{name}: recorded, not derived')
        elif name not in recorded:
            found.append(f'{name}: derived, not recorded')
        elif recorded[name] != actual[name]:
            found.append(f'{name}: recorded {recorded[name]}, derived {actual[name]}')
    return found[:20]


def check(record, wheels, root='/', python=COMPILE[0]):
    """Installed tree == record == the tree the recorded wheels install, compiled with the build's command."""
    root = pathlib.Path(root)
    if root == pathlib.Path('/') and not pathlib.Path('/run/.containerenv').exists():
        raise SystemExit('vendor_check.py check replaces /usr/lib/aresos-control: only in a container')
    installed = tree_map(root)
    if installed != record['vendor']:
        raise Mismatch('the image differs from its record: ' + '; '.join(differences(record['vendor'], installed)))
    sources = expected_sources(record, wheels)
    # The whole folder goes, siblings of vendor/ included: the derived tree is everything build.sh puts there.
    shutil.rmtree(root / DEPENDENCIES)
    install(sources, root / VENDOR, python)
    derived = tree_map(root)
    if derived != record['vendor']:
        raise Mismatch('the record is not what the locked wheels install: ' +
                       '; '.join(differences(record['vendor'], derived)))
    bytecode = sum(name.endswith('.pyc') for name in derived)
    folders = sum(entry['sha256'] is None for entry in derived.values())
    return dict(paths=len(derived), wheels=len(record['wheels']), wheel_files=len(sources), bytecode=bytecode,
                folders=folders)


def download(url, attempts=3):
    """The bytes at an https URL; a reset or a server error is tried again, twice."""
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=60) as answer:
                return answer.read()
        except OSError as error:
            if attempt == attempts - 1:
                raise
            print(f'{url}: {error}; trying again', file=sys.stderr)
            time.sleep(5 * (attempt + 1))


def fetch(record, folder, get=download):
    """Each recorded wheel from PyPI: the file of that name in its release, with the recorded SHA-256 there and in
    the bytes that arrive. Returns their total size."""
    folder = pathlib.Path(folder)
    total = 0
    for wheel in record['wheels']:
        if not WHEEL_FILE.fullmatch(wheel['file']):
            raise Mismatch(f'not a wheel file name: {wheel["file"]!r}')
        release = json.loads(get(INDEX.format(name=wheel['name'], version=wheel['version'])))
        matches = [item for item in release['urls'] if item['filename'] == wheel['file']]
        if len(matches) != 1 or matches[0]['digests']['sha256'] != wheel['sha256']:
            raise Mismatch(f'{wheel["file"]}: not on PyPI with the recorded SHA-256')
        if not matches[0]['url'].startswith(FILES_HOST):
            raise Mismatch(f'{wheel["file"]}: served from {matches[0]["url"]}')
        data = get(matches[0]['url'])
        if sha256(data) != wheel['sha256']:
            raise Mismatch(f'{wheel["file"]}: the download is not the recorded SHA-256')
        (folder / wheel['file']).write_bytes(data)
        total += len(data)
    return total


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 3 or argv[0] not in ('fetch', 'check'):
        raise SystemExit(__doc__.split('\n\n')[1])
    mode, record_path, wheels = argv
    record = json.loads(pathlib.Path(record_path).read_text())
    began = time.monotonic()
    try:
        if mode == 'fetch':
            size = fetch(record, wheels)
            print(f'CONTROL_WHEELS_FETCHED {len(record["wheels"])} wheels, {size} bytes from PyPI, '
                  f'{time.monotonic() - began:.1f} s')
        else:
            found = check(record, wheels)
            print(f'CONTROL_VENDOR_FROM_WHEELS {found["paths"]} vendored paths: {found["wheel_files"]} files from '
                  f'{found["wheels"]} wheels and pip, {found["bytecode"]} bytecode, {found["folders"]} folders; '
                  f'{time.monotonic() - began:.1f} s')
    except Mismatch as error:
        print(f'vendor_check.py {mode}: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
