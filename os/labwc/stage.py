#!/usr/bin/python3
"""Package 311: Fedora's labwc rebuilt with one patch, from exact inputs (labwc.lock.json).

  stage.py fetch <lock folder> <inputs>             labwc-inputs stage: download every input and check it
  stage.py build <lock folder> <inputs> <out>       labwc stage, on the locked fedora:44: the RPM and nothing else,
                                                    once its binaries match the lock's normalized and loaded pins
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
import types

LOCK_NAME = 'labwc.lock.json'
CONTAINERFILE = 'Containerfile'
# Any spelling of the line that starts the labwc stage: what it names must then be exactly the locked reference.
LABWC_STAGE = re.compile(r'^[ \t]*FROM[ \t]+(.+?)[ \t]+AS[ \t]+labwc[ \t]*$', re.IGNORECASE | re.MULTILINE)
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
# 311d: the RPM is not byte-reproducible, so the binaries are pinned without the three sections that vary between
# builds of the same inputs. Everything that stays in the file is pinned: never add a section here to make a pin hold.
VARYING_SECTIONS = ('.note.gnu.build-id', '.gnu_debuglink', '.gnu_debugdata')
PINNED_BINARIES = ('/usr/bin/labnag', '/usr/bin/labwc')
# 311e: the normalized pins cover the sections, the loaded pins the bytes the loader maps (loaded_image.py).
PIN_KINDS = ('normalized_sha256', 'loaded_sha256')
LOADED_IMAGE = 'loaded_image.py'
PIN_RENEWAL = ('LABWC_PINS_KEPT a candidate keeps the lock\'s result.normalized_sha256 and result.loaded_sha256, and no '
               'build ever writes either. After a change to the patch or the locked build environment, run podman build '
               '--no-cache --target labwc twice: each run prints LABWC_NORMALIZED and LABWC_LOADED lines and stops with '
               'LABWC_REFUSED. If both runs print the same hashes, review the change and write them into '
               'result.normalized_sha256 and result.loaded_sha256 by hand.')


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
    need(isinstance(result, dict) and set(result) == {'nevra', 'replaces', *PIN_KINDS},
         'result needs exactly nevra, replaces, normalized_sha256 and loaded_sha256')
    need(result['nevra'] == 'labwc-0.9.6-1.fc44.aresos1.x86_64', 'result.nevra is not the reviewed build')
    need(result['replaces'] == 'labwc-0.9.6-1.fc44.x86_64', "result.replaces is not Fedora's labwc")
    for kind in PIN_KINDS:
        pins = result[kind]
        need(isinstance(pins, dict) and set(pins) == set(PINNED_BINARIES),
             f'result.{kind} needs exactly {", ".join(PINNED_BINARIES)}')
        need(all(isinstance(pin, str) and SHA256.fullmatch(pin) for pin in pins.values()),
             f'result.{kind} holds something that is not a SHA-256')
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


def require_locked_base(lock, lock_folder):
    """The labwc stage is built on the image the lock records, the one check_build=resolve resolves against.

    The environment check in build() cannot see this: two images can hold the same packages and build differently.
    """
    path = pathlib.Path(lock_folder).parent / CONTAINERFILE
    try:
        found = LABWC_STAGE.findall(path.read_text())
    except (OSError, ValueError) as error:
        raise Refusal(f'{CONTAINERFILE} cannot be read: {error}') from error
    locked = lock['base']['reference']
    if found != [locked]:
        raise Refusal(f'the labwc stage must be built from the locked {locked}, {CONTAINERFILE} says {found}')


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
    require_locked_base(lock, lock_folder)
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


def normalized_sha256(binary):
    """The SHA-256 of a copy of this ELF file without VARYING_SECTIONS. The file itself is not changed.

    objcopy rewrites the file from its sections and recomputes program header fields, so a match means the sections
    are the same, not the whole file: bytes outside every section and some header fields are not part of this hash.
    """
    with tempfile.TemporaryDirectory(prefix='aresos-labwc-normalize-') as folder:
        copy = pathlib.Path(folder) / 'binary'
        shutil.copyfile(binary, copy)
        removals = [argument for section in VARYING_SECTIONS for argument in ('--remove-section', section)]
        query('objcopy', *removals, str(copy))
        return sha256(copy)


def loaded_image_module():
    """loaded_image.py from beside this file: python3 -I keeps this folder off the import path.

    It is compiled from its source here, so a __pycache__ that came along in the build context cannot stand in for it.
    """
    path = pathlib.Path(__file__).with_name(LOADED_IMAGE)
    try:
        source = path.read_bytes()
    except OSError as error:
        raise Refusal(f'{LOADED_IMAGE} cannot be read: {error}') from error
    module = types.ModuleType(path.stem)
    exec(compile(source, str(path), 'exec'), module.__dict__)
    return module


def unpack_pinned_binaries(rpm, folder):
    """The pinned binaries from the RPM's own payload, under folder."""
    members = [f'.{path}' for path in PINNED_BINARIES]
    payload = subprocess.Popen(['rpm2cpio', str(rpm)], stdout=subprocess.PIPE)
    result = subprocess.run(['cpio', '-idm', '--quiet', '--no-absolute-filenames', *members], stdin=payload.stdout,
                            cwd=folder, capture_output=True, text=True)
    payload.stdout.close()
    if payload.wait() != 0 or result.returncode != 0:
        detail = result.stderr.strip() or 'rpm2cpio failed'
        raise Refusal(f'the payload of {pathlib.Path(rpm).name} cannot be unpacked: {detail}')


def require_pinned_binaries(rpm, lock):
    """The code in this RPM is the reviewed code: its sections and the bytes the loader maps both match the lock."""
    image = loaded_image_module()
    normalized, loaded = {}, {}
    with tempfile.TemporaryDirectory(prefix='aresos-labwc-payload-') as folder:
        unpack_pinned_binaries(rpm, folder)
        for path in PINNED_BINARIES:
            binary = pathlib.Path(folder) / path.lstrip('/')
            if binary.is_symlink() or not binary.is_file():
                raise Refusal(f'the RPM holds no file {path}')
            normalized[path] = normalized_sha256(binary)
            try:
                loaded[path] = image.loaded_sha256(binary)
            except image.LoadedImageRefused as refusal:
                raise Refusal(f'the loaded image of {path} cannot be pinned: {refusal}') from refusal
    for path in PINNED_BINARIES:
        print(f'LABWC_NORMALIZED {path} {normalized[path]}', flush=True)
    for path in PINNED_BINARIES:
        print(f'LABWC_LOADED {path} {loaded[path]}', flush=True)
    wrong = []
    for name, actual, pins in (('normalized', normalized, lock['result']['normalized_sha256']),
                               ('loaded', loaded, lock['result']['loaded_sha256'])):
        differing = [f'{path} is {actual[path]}, the lock says {pins[path]}'
                     for path in PINNED_BINARIES if actual[path] != pins[path]]
        if differing:
            wrong.append(f'the {name} SHA-256 of {"; ".join(differing)}')
    if wrong:
        raise Refusal('; '.join(wrong))


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
    require_pinned_binaries(built, lock)
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
    print(PIN_RENEWAL)
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
