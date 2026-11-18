#!/usr/bin/python3
"""Package 311: Fedora's labwc rebuilt with one patch, from exact inputs (labwc.lock.json).

  stage.py build <lock folder> <out folder>      the Containerfile's labwc stage: the RPM and nothing else
  stage.py install <rpm folder> <lock folder>    the final stage: our RPM replaces Fedora's labwc
  stage.py resolve <lock folder> <out folder>    check_build=resolve: a fresh candidate for the build dependencies

Anything that differs from the lock stops the build with one line that starts with LABWC_REFUSED.
"""
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

LOCK_NAME = 'labwc.lock.json'
MANIFEST = pathlib.Path('/usr/share/aresos/manifest')
KOJI ='https://kojipkgs.fedoraproject.org/packages/'
SHA256 = re.compile(r'[0-9a-f]{64}')
NEVRA = re.compile(r'[A-Za-z0-9._+-]+-(?:[0-9]+:)?[A-Za-z0-9._+~^]+-[A-Za-z0-9._+~^]+\.(?:x86_64|noarch)')
# The two lines of Fedora's spec this package edits. Each must be there exactly once.
RELEASE_LINE = 'Release:    %autorelease\n'
SOURCE_LINE = 'Source:     %{forgesource}\n'
# The braces matter: %autorelease takes the rest of its line as arguments.
RELEASE_EDIT = 'Release:    %{autorelease}.aresos1\n'
DIST = '.fc44'
# What rpmbuild itself needs; the spec's own BuildRequires come from the source package.
BUILD_TOOLS = ('rpm-build', 'redhat-rpm-config')


class Refusal(Exception):
    """The inputs or the result are not what the lock says."""


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def require_sha256(path, expected, what):
    actual = sha256(path)
    if actual != expected:
        raise Refusal(f'{what} has SHA-256 {actual}, the lock says {expected}')


def query(*command):
    """The output of a read-only command, or a refusal that names the command."""
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        detail = (result.stderr.strip().splitlines() or ['no message'])[-1]
        raise Refusal(f'{" ".join(command[:3])} failed: {detail}')
    return result.stdout


def fetch(url, target):
    result = subprocess.run(['curl', '-fsSL', '--proto', '=https', '--tlsv1.2', '--retry', '3', '-o', str(target), url])
    if result.returncode != 0:
        raise Refusal(f'could not download {url} (curl exit {result.returncode})')


def file_nevra(path):
    return query('rpm', '-qp', '--nosignature', '--qf', '%{NEVRA}', str(path))


def installed_packages():
    return set(query('rpm', '-qa', '--qf', '%{NEVRA}\\n').split())


def validate_lock(lock):
    """The lock's exact shape. Returns the lock, or raises Refusal naming the first thing wrong."""
    def need(condition, message):
        if not condition:
            raise Refusal(f'{LOCK_NAME}: {message}')

    need(isinstance(lock, dict) and set(lock) == {'source', 'patch', 'result', 'build_dependencies'},
         'expected exactly source, patch, result and build_dependencies')
    source, patch, result, dependencies = (lock['source'], lock['patch'], lock['result'], lock['build_dependencies'])
    need(isinstance(source, dict) and set(source) == {'url', 'sha256'}, 'source needs exactly url and sha256')
    need(isinstance(source['url'], str) and source['url'].startswith(KOJI) and source['url'].endswith('.src.rpm'),
         'source.url must be a source package on kojipkgs.fedoraproject.org')
    need(isinstance(source['sha256'], str) and SHA256.fullmatch(source['sha256']), 'source.sha256 is not a SHA-256')
    need(isinstance(patch, dict) and set(patch) == {'file', 'sha256'}, 'patch needs exactly file and sha256')
    need(isinstance(patch['file'], str) and re.fullmatch(r'[0-9A-Za-z][0-9A-Za-z.-]*\.patch', patch['file']),
         'patch.file must be a plain .patch file name')
    need(isinstance(patch['sha256'], str) and SHA256.fullmatch(patch['sha256']), 'patch.sha256 is not a SHA-256')
    need(isinstance(result, dict) and set(result) == {'nevra', 'replaces'}, 'result needs exactly nevra and replaces')
    need(result['nevra'] == 'labwc-0.9.6-1.fc44.aresos1.x86_64', 'result.nevra is not the reviewed build')
    need(result['replaces'] == 'labwc-0.9.6-1.fc44.x86_64', "result.replaces is not Fedora's labwc")
    need(isinstance(dependencies, list) and dependencies, 'build_dependencies must list every build dependency')
    names = []
    for entry in dependencies:
        need(isinstance(entry, dict) and set(entry) == {'nevra', 'url', 'sha256'},
             'each build dependency needs exactly nevra, url and sha256')
        nevra, url, digest = entry['nevra'], entry['url'], entry['sha256']
        need(isinstance(nevra, str) and NEVRA.fullmatch(nevra), f'{nevra!r} is not an exact NEVRA')
        need(isinstance(url, str) and url.startswith(KOJI) and url.endswith(f'/{nevra}.rpm'),
             f'{nevra}: the url must be its exact file on kojipkgs.fedoraproject.org')
        need(isinstance(digest, str) and SHA256.fullmatch(digest), f'{nevra}: not a SHA-256')
        names.append(nevra)
    need(names == sorted(set(names)), 'build_dependencies must be sorted and without repeats')
    return lock


def load_lock(folder):
    path = pathlib.Path(folder) / LOCK_NAME
    try:
        lock = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise Refusal(f'{LOCK_NAME} cannot be read: {error}') from error
    return validate_lock(lock)


def install_build_dependencies(lock, folder):
    """Exactly the locked packages join the base: repositories stay off, so nothing newer can come in."""
    folder.mkdir()
    files, locked = [], set()
    for entry in lock['build_dependencies']:
        target = folder / f'{entry["nevra"]}.rpm'
        fetch(entry['url'], target)
        require_sha256(target, entry['sha256'], f'build dependency {entry["nevra"]}')
        actual = file_nevra(target)
        if actual != entry['nevra']:
            raise Refusal(f'build dependency {entry["nevra"]} is really {actual}')
        files.append(str(target))
        locked.add(entry['nevra'])
    before = installed_packages()
    result = subprocess.run(['dnf5', '--disable-repo=*', '--setopt=install_weak_deps=False',
                             '--setopt=localpkg_gpgcheck=True', 'install', '-y', *files])
    if result.returncode != 0:
        raise Refusal(f'the locked build dependencies do not install on this base (dnf5 exit {result.returncode}): '
                      'renew them with check_build=resolve')
    after = installed_packages()
    added, removed = after - before, before - after
    if added != locked or removed:
        raise Refusal(f'build dependencies drifted: outside the lock {sorted(added - locked)}, '
                      f'not installed {sorted(locked - added)}, replaced in the base {sorted(removed)}')


def edit_spec(spec, patch_name):
    """The smallest edit of Fedora's spec: the release suffix and one Patch line."""
    text = spec.read_text()
    for line in (RELEASE_LINE, SOURCE_LINE):
        if text.count(line) != 1:
            raise Refusal(f"Fedora's spec does not have exactly one line {line.strip()!r}")
    text = text.replace(RELEASE_LINE, RELEASE_EDIT).replace(SOURCE_LINE, f'{SOURCE_LINE}Patch0:     {patch_name}\n')
    spec.write_text(text)


def build(lock_folder, out):
    lock_folder, out = pathlib.Path(lock_folder), pathlib.Path(out)
    lock = load_lock(lock_folder)
    patch = lock_folder / lock['patch']['file']
    if not patch.is_file():
        raise Refusal(f'the patch {patch.name} is missing')
    require_sha256(patch, lock['patch']['sha256'], 'the patch')
    work = pathlib.Path(tempfile.mkdtemp(prefix='aresos-labwc-'))
    source = work / 'source.src.rpm'
    fetch(lock['source']['url'], source)
    require_sha256(source, lock['source']['sha256'], 'the source package')
    install_build_dependencies(lock, work / 'dependencies')

    top = work / 'rpmbuild'
    subprocess.run(['rpm', '--define', f'_topdir {top}', '--nosignature', '-i', str(source)], check=True)
    shutil.copyfile(patch, top / 'SOURCES' / patch.name)
    spec = top / 'SPECS/labwc.spec'
    edit_spec(spec, patch.name)
    subprocess.run(['rpmbuild', '-bb', '--define', f'_topdir {top}', '--define', f'dist {DIST}', str(spec)], check=True)

    nevra = lock['result']['nevra']
    built = top / 'RPMS/x86_64' / f'{nevra}.rpm'
    if not built.is_file() or file_nevra(built) != nevra:
        raise Refusal(f'the build did not produce {nevra}')
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        raise Refusal(f'{out} is not empty: the stage outputs the RPM and nothing else')
    shutil.copyfile(built, out / built.name)
    shutil.rmtree(work)
    print(f'LABWC_BUILT {nevra} {sha256(out / built.name)}')


def require_only_labwc(lines, nevra):
    """Exactly one labwc, the locked one: Fedora's and ours side by side would be a broken image."""
    if lines != [nevra]:
        raise Refusal(f'installed labwc is {lines}, the lock says exactly [{nevra!r}]')


def install(rpm_folder, lock_folder):
    rpm_folder, lock_folder = pathlib.Path(rpm_folder), pathlib.Path(lock_folder)
    lock = load_lock(lock_folder)
    nevra, fedora = lock['result']['nevra'], lock['result']['replaces']
    files = sorted(rpm_folder.iterdir())
    if [path.name for path in files] != [f'{nevra}.rpm']:
        raise Refusal(f'{rpm_folder} must hold exactly {nevra}.rpm, it holds {[path.name for path in files]}')
    if file_nevra(files[0]) != nevra:
        raise Refusal(f'{files[0].name} is really {file_nevra(files[0])}')
    labwc_query = ('rpm', '-q', '--qf', '%{NEVRA}\\n', 'labwc')
    current = query(*labwc_query).split()
    if current != [fedora]:
        raise Refusal(f"expected Fedora's {fedora} before the swap, found {current}")
    before = installed_packages()
    # The one unsigned package in the image: this exact file, named and checked above, with every repository off.
    # Every other local install keeps localpkg_gpgcheck=True (os/build.sh).
    result = subprocess.run(['dnf5', '--disable-repo=*', '--setopt=install_weak_deps=False',
                             '--setopt=localpkg_gpgcheck=False', 'install', '-y', str(files[0])])
    if result.returncode != 0:
        raise Refusal(f'{nevra} did not install (dnf5 exit {result.returncode})')
    require_only_labwc(query(*labwc_query).split(), nevra)
    after = installed_packages()
    if after - before != {nevra} or before - after != {fedora}:
        raise Refusal(f'the swap changed other packages: added {sorted(after - before)}, '
                      f'removed {sorted(before - after)}')
    verify = subprocess.run(['rpm', '-V', 'labwc'], capture_output=True, text=True)
    if verify.returncode != 0 or verify.stdout.strip():
        raise Refusal(f'rpm -V labwc is not clean: {verify.stdout.strip() or verify.stderr.strip()}')
    # The packages stage listed Fedora's labwc here; the list must name what the image really holds.
    (MANIFEST / 'packages.txt').write_text('\n'.join(sorted(after)) + '\n')
    shutil.copyfile(lock_folder / LOCK_NAME, MANIFEST / LOCK_NAME)
    print(f'LABWC_INSTALLED {nevra} replaces {fedora}')


def koji_url(path):
    """Fedora's signed copy of a downloaded package on Koji, which keeps every build's files."""
    fields = query('rpm', '-qp', '--nosignature', '--qf', '%{SOURCERPM}\\t%{ARCH}\\t%{NEVRA}\\t%{RSAHEADER:pgpsig}',
                   str(path)).split('\t')
    source, arch, nevra, signature = fields
    name, version, release = source.removesuffix('.src.rpm').rsplit('-', 2)
    key = re.search(r'Key ID ([0-9a-f]{16})', signature, re.I)
    if not key:
        raise Refusal(f'{nevra} carries no Fedora signature: {signature}')
    return nevra, f'{KOJI}{name}/{version}/{release}/data/signed/{key[1][-8:].lower()}/{arch}/{nevra}.rpm'


def resolve(lock_folder, out):
    """A fresh resolution against this base, for review. Changes nothing the image build reads."""
    lock_folder, out = pathlib.Path(lock_folder), pathlib.Path(out)
    lock = load_lock(lock_folder)
    out.mkdir(parents=True, exist_ok=True)
    work = pathlib.Path(tempfile.mkdtemp(prefix='aresos-labwc-resolve-'))
    source = work / 'source.src.rpm'
    fetch(lock['source']['url'], source)
    require_sha256(source, lock['source']['sha256'], 'the source package')
    wanted = [line.strip() for line in query('rpm', '-qp', '--nosignature', '--requires', str(source)).splitlines()
              if line.strip() and not line.startswith('rpmlib(')]
    specs = [*BUILD_TOOLS, *wanted]
    print('Requested: ' + ', '.join(specs))
    downloads = work / 'downloads'
    subprocess.run(['dnf5', '--disable-repo=*', '--enable-repo=fedora', '--enable-repo=updates',
                    '--setopt=install_weak_deps=False', '--setopt=skip_if_unavailable=False', '--setopt=gpgcheck=True',
                    'download', '--resolve', f'--destdir={downloads}', *specs], check=True)
    candidates, unavailable = [], []
    check = work / 'koji'
    check.mkdir()
    for path in sorted(downloads.glob('*.rpm')):
        nevra, url = koji_url(path)
        digest = sha256(path)
        target = check / path.name
        try:
            fetch(url, target)
            require_sha256(target, digest, url)
        except Refusal as refusal:
            unavailable.append(f'{nevra}: {refusal}')
        target.unlink(missing_ok=True)
        candidates.append(dict(nevra=nevra, url=url, sha256=digest))
    candidates.sort(key=lambda entry: entry['nevra'])
    candidate = dict(lock, build_dependencies=candidates)
    (out / 'candidate-labwc.lock.json').write_text(json.dumps(candidate, indent=2) + '\n')
    locked = {entry['nevra']: entry['sha256'] for entry in lock['build_dependencies']}
    fresh = {entry['nevra']: entry['sha256'] for entry in candidates}
    print(f'Resolved {len(fresh)} build dependencies; the lock has {len(locked)}')
    for nevra in sorted(set(fresh) - set(locked)):
        print(f'NEW {nevra}')
    for nevra in sorted(set(locked) - set(fresh)):
        print(f'GONE {nevra}')
    for nevra in sorted(n for n in set(fresh) & set(locked) if fresh[n] != locked[n]):
        print(f'CHANGED {nevra}')
    for line in unavailable:
        print(f'NOT_ON_KOJI {line}')
    print('LABWC_LOCK_CURRENT' if fresh == locked and not unavailable else 'LABWC_LOCK_DIFFERS')
    shutil.rmtree(work)


def main(argv):
    commands = {'build': build, 'install': install, 'resolve': resolve}
    if len(argv) != 4 or argv[1] not in commands:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        commands[argv[1]](argv[2], argv[3])
    except Refusal as refusal:
        print(f'LABWC_REFUSED {refusal}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
