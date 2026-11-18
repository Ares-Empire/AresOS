#!/usr/bin/python3
"""Package 311: Fedora's labwc rebuilt with one patch, from exact inputs (labwc.lock.json).

  stage.py fetch <lock folder> <inputs>             labwc-inputs stage: download every input and check it
  stage.py build <lock folder> <inputs> <out>       labwc stage, on the locked fedora:44: the RPM and nothing else
  stage.py install <rpm folder> <lock folder>       final stage: our RPM replaces Fedora's labwc
  stage.py resolve <lock folder> <resolved> <out>   check_build=resolve: a candidate from resolve-download.sh's folder

fedora:44 has no Python, so the pinned AresOS base fetches the inputs and install-inputs.sh installs them before
this file runs there. Anything that differs from the lock stops the build with one line that starts with LABWC_REFUSED.
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
SOURCE_FILE = 'source.src.rpm'
MANIFEST = pathlib.Path('/usr/share/aresos/manifest')
KOJI = 'https://kojipkgs.fedoraproject.org/packages/'
BASE_REFERENCE = re.compile(r'registry\.fedoraproject\.org/fedora@sha256:[0-9a-f]{64}')
SHA256 = re.compile(r'[0-9a-f]{64}')
NEVRA = re.compile(r'[A-Za-z0-9._+-]+-(?:[0-9]+:)?[A-Za-z0-9._+~^]+-[A-Za-z0-9._+~^]+\.(?:x86_64|noarch)')
# The two lines of Fedora's spec this package edits. Each must be there exactly once.
RELEASE_LINE = 'Release:    %autorelease\n'
SOURCE_LINE = 'Source:     %{forgesource}\n'
# The braces matter: %autorelease takes the rest of its line as arguments.
RELEASE_EDIT = 'Release:    %{autorelease}.aresos1\n'
DIST = '.fc44'
# labwc links this library: the headers it builds against must be the build the image runs.
WLROOTS, WLROOTS_DEVEL = 'wlroots0.19', 'wlroots0.19-devel'


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
        # rpm -q says "package x is not installed" on stdout.
        detail = ((result.stderr.strip() or result.stdout.strip()).splitlines() or ['no message'])[-1]
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


def split_nevra(nevra):
    """(name, version, release, arch); the epoch is not part of what this file compares."""
    match = re.fullmatch(r'(.+)-(?:[0-9]+:)?([^-]+)-([^-]+)\.([^.]+)', nevra)
    if not match:
        raise Refusal(f'{nevra!r} is not an exact NEVRA')
    return match.groups()


def file_name(nevra):
    """Koji's file for a package: its name carries no epoch."""
    return re.sub(r'-[0-9]+:', '-', nevra, count=1) + '.rpm'


def validate_lock(lock):
    """The lock's exact shape. Returns the lock, or raises Refusal naming the first thing wrong."""
    def need(condition, message):
        if not condition:
            raise Refusal(f'{LOCK_NAME}: {message}')

    need(isinstance(lock, dict) and set(lock) == {'base', 'source', 'patch', 'result', 'build_dependencies'},
         'expected exactly base, source, patch, result and build_dependencies')
    base, source, patch, result, dependencies = (lock['base'], lock['source'], lock['patch'], lock['result'],
                                                 lock['build_dependencies'])
    need(isinstance(base, dict) and set(base) == {'reference', 'packages'}, 'base needs exactly reference and packages')
    need(isinstance(base['reference'], str) and BASE_REFERENCE.fullmatch(base['reference']),
         'base.reference must be fedora pinned by digest')
    packages = base['packages']
    need(isinstance(packages, list) and packages and all(isinstance(n, str) and NEVRA.fullmatch(n) for n in packages),
         'base.packages must list the exact NEVRA of every package in the base')
    need(packages == sorted(set(packages)), 'base.packages must be sorted and without repeats')
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
        need(isinstance(url, str) and url.startswith(KOJI) and url.endswith(f'/{file_name(nevra)}'),
             f'{nevra}: the url must be its exact file on kojipkgs.fedoraproject.org')
        need(isinstance(digest, str) and SHA256.fullmatch(digest), f'{nevra}: not a SHA-256')
        names.append(nevra)
    need(names == sorted(set(names)), 'build_dependencies must be sorted and without repeats')
    need(len([name for name in names if split_nevra(name)[0] == WLROOTS_DEVEL]) == 1,
         f'build_dependencies must hold exactly one {WLROOTS_DEVEL}')
    return lock


def load_lock(folder):
    path = pathlib.Path(folder) / LOCK_NAME
    try:
        lock = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise Refusal(f'{LOCK_NAME} cannot be read: {error}') from error
    return validate_lock(lock)


def require_same_wlroots(lock, runtime):
    """Guard 1: the headers labwc is built against are the wlroots build the image runs."""
    devel = next(entry['nevra'] for entry in lock['build_dependencies']
                 if split_nevra(entry['nevra'])[0] == WLROOTS_DEVEL)
    if split_nevra(devel)[1:3] != split_nevra(runtime)[1:3]:
        raise Refusal(f'the locked {devel} is not the same build as the image\'s {runtime}')


def image_wlroots(lock_folder):
    """The wlroots0.19 that os/packages.lock.json puts in the image."""
    path = pathlib.Path(lock_folder).parent / 'packages.lock.json'
    try:
        packages = [entry['nevra'] for entry in json.loads(path.read_text())['packages']]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise Refusal(f'{path.name} cannot be read: {error}') from error
    found = [nevra for nevra in packages if split_nevra(nevra)[0] == WLROOTS]
    if len(found) != 1:
        raise Refusal(f'{path.name} must hold exactly one {WLROOTS}, it holds {found}')
    return found[0]


def check_patch(lock, lock_folder):
    patch = pathlib.Path(lock_folder) / lock['patch']['file']
    if not patch.is_file():
        raise Refusal(f'the patch {patch.name} is missing')
    require_sha256(patch, lock['patch']['sha256'], 'the patch')
    return patch


def fetch_inputs(lock_folder, inputs):
    """Every input, checked against the lock, for the labwc stage (which has no Python until they are installed)."""
    lock_folder, inputs = pathlib.Path(lock_folder), pathlib.Path(inputs)
    lock = load_lock(lock_folder)
    check_patch(lock, lock_folder)
    require_same_wlroots(lock, image_wlroots(lock_folder))
    (inputs / 'rpms').mkdir(parents=True)
    fetch(lock['source']['url'], inputs / SOURCE_FILE)
    require_sha256(inputs / SOURCE_FILE, lock['source']['sha256'], 'the source package')
    for entry in lock['build_dependencies']:
        target = inputs / 'rpms' / file_name(entry['nevra'])
        fetch(entry['url'], target)
        check_dependency(target, entry)
    print(f'LABWC_INPUTS {len(lock["build_dependencies"])} build dependencies')


def check_dependency(path, entry):
    require_sha256(path, entry['sha256'], f'build dependency {entry["nevra"]}')
    actual = file_nevra(path)
    if actual != entry['nevra']:
        raise Refusal(f'build dependency {entry["nevra"]} is really {actual}')


def expected_environment(lock):
    """The locked base with the locked packages on top. A locked package replaces its older copy in the base."""
    locked = {entry['nevra'] for entry in lock['build_dependencies']}
    replaced = {(split_nevra(nevra)[0], split_nevra(nevra)[3]) for nevra in locked}
    kept = {nevra for nevra in lock['base']['packages'] if (split_nevra(nevra)[0], split_nevra(nevra)[3]) not in replaced}
    return kept | locked


def require_environment(lock):
    """Exactly the locked build environment: another base or any other package stops the build here."""
    actual = {nevra for nevra in installed_packages() if not nevra.startswith('gpg-pubkey-')}
    expected = expected_environment(lock)
    if actual != expected:
        raise Refusal(f'the build environment drifted: outside the lock {sorted(actual - expected)}, '
                      f'missing {sorted(expected - actual)}')


def edit_spec(spec, patch_name):
    """The smallest edit of Fedora's spec: the release suffix and one Patch line."""
    text = spec.read_text()
    for line in (RELEASE_LINE, SOURCE_LINE):
        if text.count(line) != 1:
            raise Refusal(f"Fedora's spec does not have exactly one line {line.strip()!r}")
    text = text.replace(RELEASE_LINE, RELEASE_EDIT).replace(SOURCE_LINE, f'{SOURCE_LINE}Patch0:     {patch_name}\n')
    spec.write_text(text)


def build(lock_folder, inputs, out):
    lock_folder, inputs, out = pathlib.Path(lock_folder), pathlib.Path(inputs), pathlib.Path(out)
    lock = load_lock(lock_folder)
    patch = check_patch(lock, lock_folder)
    source = inputs / SOURCE_FILE
    if not source.is_file():
        raise Refusal(f'the source package is missing from {inputs}')
    require_sha256(source, lock['source']['sha256'], 'the source package')
    wanted = {file_name(entry['nevra']): entry for entry in lock['build_dependencies']}
    present = sorted(path.name for path in (inputs / 'rpms').glob('*'))
    if present != sorted(wanted):
        raise Refusal(f'the inputs are not the locked build dependencies: outside the lock '
                      f'{sorted(set(present) - set(wanted))}, missing {sorted(set(wanted) - set(present))}')
    for name, entry in wanted.items():
        check_dependency(inputs / 'rpms' / name, entry)
    require_environment(lock)

    work = pathlib.Path(tempfile.mkdtemp(prefix='aresos-labwc-'))
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
    runtime = query('rpm', '-q', '--qf', '%{NEVRA}\\n', WLROOTS).split()
    if len(runtime) != 1:
        raise Refusal(f'the image must hold exactly one {WLROOTS}, it holds {runtime}')
    require_same_wlroots(lock, runtime[0])
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
    return nevra, f'{KOJI}{name}/{version}/{release}/data/signed/{key[1][-8:].lower()}/{arch}/{file_name(nevra)}'


def resolve(lock_folder, resolved, out):
    """A fresh candidate from what resolve-download.sh found on fedora:44. Changes nothing the image build reads."""
    lock_folder, resolved, out = pathlib.Path(lock_folder), pathlib.Path(resolved), pathlib.Path(out)
    lock = load_lock(lock_folder)
    out.mkdir(parents=True, exist_ok=True)
    downloads = resolved / 'downloads'
    listing = resolved / 'base-packages.txt'
    if not listing.is_file() or not sorted(downloads.glob('*.rpm')):
        raise Refusal(f"the build dependencies did not resolve on fedora:44 from Fedora's repositories ({resolved})")
    base_packages = sorted(set(listing.read_text().split()))
    work = pathlib.Path(tempfile.mkdtemp(prefix='aresos-labwc-resolve-'))
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
    candidate = dict(lock, base=dict(lock['base'], packages=base_packages), build_dependencies=candidates)
    validate_lock(candidate)
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
    same_base = base_packages == lock['base']['packages']
    if not same_base:
        print(f'BASE_CHANGED {sorted(set(base_packages) ^ set(lock["base"]["packages"]))}')
    try:
        require_same_wlroots(candidate, image_wlroots(lock_folder))
        same_wlroots = True
    except Refusal as refusal:
        print(f'WLROOTS_DIFFERS {refusal}')
        same_wlroots = False
    current = fresh == locked and same_base and same_wlroots and not unavailable
    print('LABWC_LOCK_CURRENT' if current else 'LABWC_LOCK_DIFFERS')
    shutil.rmtree(work)


def main(argv):
    commands = {'fetch': (fetch_inputs, 2), 'build': (build, 3), 'install': (install, 2), 'resolve': (resolve, 3)}
    if len(argv) < 2 or argv[1] not in commands or len(argv) != commands[argv[1]][1] + 2:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        commands[argv[1]][0](*argv[2:])
    except Refusal as refusal:
        print(f'LABWC_REFUSED {refusal}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
