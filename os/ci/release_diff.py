"""Release 27: compare the full rebuild with release 13; explain every difference.

Release 13 is release 6's image plus two keyboard files. Release 27 rebuilds the
reviewed Containerfile on the same pinned base. Every package, file and unit
difference must trace to a reviewed source change of packages 21 and 24 (or a
renewed pin), to a reviewed build step, or to a database the package
transaction regenerates. Anything else stops the release before publishing.
Each rule verifies content where the build is deterministic; the regenerated
databases are listed by path so a reviewer sees each one.
"""
import fnmatch
import gzip
import hashlib
import json
import os
import pathlib
import re
import stat
import subprocess

import image_diff

PREVIOUS = 'os/manifest/releases/13.json'
# Release 13's source on main (PR #12's squash). Its os/config, os/policy,
# audit and package lock describe release 13's image exactly: release 6's
# source plus the two keyboard files the overlay copied.
PREVIOUS_SOURCE = '775be05b7f0d6971cbdc8a3bd1aea617fc008c4d'
NEW = 'localhost/aresos:ci'

UTIL_LINUX = ('package 21 JUDGMENT-CALL 4: util-linux 2.41.5 to 2.41.6, '
              'which util-linux-script requires')
PACKAGE_REASONS = {
    'brightnessctl': 'package 21: brightness keys (brightnessctl)',
    'qrencode': 'package 21: qrencode',
    'util-linux-script': 'package 21: script (util-linux-script)',
    'liberation-fonts-all': "package 21: Google Chrome's only Fedora dependency",
    'google-chrome-stable': 'package 21: Google Chrome from its pinned RPM',
    'xdg-desktop-portal-wlr': 'package 21 JUDGMENT-CALL 10: vanished Fedora pin 0.8.4 renewed to 0.8.5',
    **{name: UTIL_LINUX for name in ('util-linux', 'util-linux-core', 'libblkid', 'libmount',
                                     'libuuid', 'libfdisk', 'libsmartcols', 'liblastlog2')},
}

# build.sh changes of packages 21 and 24, as exact effects on files.
CHROME_DEFAULTS = (b'# AresOS: Chrome updates arrive with AresOS releases, not from a repository.\n'
                   b'repo_add_once="false"\nrepo_reenable_on_distupgrade="false"\n')
CHROME_LINKS = {'usr/bin/google-chrome-stable': '/usr/lib/opt/google/chrome/google-chrome',
                'usr/bin/google-chrome': 'google-chrome-stable'}
# Release 13's build chmodded these 0700 and edited this profile script; this
# build leaves them as the base ships them (package 21: Flatpak and Homebrew
# are his apps; aresos.sh sets the daily PATH).
BASE_RESTORED = {'usr/bin/flatpak': 'package 21: flatpak is executable again',
                 'etc/profile.d/brew-bash-completion.sh': 'package 21: brew-bash-completion.sh no longer edited'}
BREW_GUARD = 'if [ "$(id -u)" = 1001 ]; then return 0; fi'
SUBID = 'ares:524288:65536'
SUBIDS_LINK = ('etc/systemd/system/multi-user.target.wants/aresos-subids.service',
               '/usr/lib/systemd/system/aresos-subids.service')
CONFIG_MODES = {'etc/sudoers.d/aresos-everyday': 0o440}
# build.sh's chmod 0755 line; other os/config files keep their checkout mode.
CHMOD_0755 = frozenset({'usr/bin/aresos-session', 'usr/bin/aresos-terminal', 'usr/bin/brew', 'usr/libexec/aresos-audit',
                        'usr/libexec/aresos-keyboard', 'usr/libexec/aresos-shell', 'usr/libexec/aresos-subids'})
# Rewritten by the package transaction itself (rpm, dnf5, ldconfig, file
# triggers, the SELinux module install of greetd-selinux) in every build. Their
# content is not compared; each changed path is listed in the result.
GENERATED = (
    ('usr/lib/sysimage/rpm/*', 'rpm database (package list compared separately)'),
    ('usr/lib/sysimage/libdnf5', 'dnf5 transaction history'),
    ('usr/lib/sysimage/libdnf5/*', 'dnf5 transaction history'),
    ('var/lib/dnf/*', 'dnf5 repository state'),
    ('var/cache/libdnf5', 'dnf5 cache directory'),
    ('var/cache/libdnf5/*', 'dnf5 cache directory'),
    ('var/log/dnf5.log*', 'dnf5 log'),
    ('etc/ld.so.cache', 'ldconfig cache (libraries changed)'),
    ('var/cache/ldconfig/aux-cache', 'ldconfig cache (libraries changed)'),
    ('usr/share/applications/mimeinfo.cache', 'desktop database trigger (Chrome desktop entry)'),
    ('usr/share/icons/*/icon-theme.cache', 'icon cache trigger (Chrome icons)'),
    ('usr/lib/fontconfig/cache/*', 'fontconfig cache trigger'),
    ('var/cache/fontconfig/*', 'fontconfig cache trigger'),
    ('run/*', 'build-time runtime leftovers (bootc lint: nonempty-run-tmp)'),
    ('etc/selinux/targeted/*', 'SELinux policy store rebuilt by the transaction'),
    ('var/lib/selinux/*', 'SELinux policy store rebuilt by the transaction'),
)


def git(*args, **kwargs):
    # The privileged diff runs as root in the runner's checkout; trust only it.
    return subprocess.check_output(['git', '-c', 'safe.directory=' + os.getcwd(), *args], **kwargs)


def git_bytes(commit, path):
    return git('show', commit + ':' + path)


def git_changed(commit, prefix):
    out = git('diff', '--name-only', '--no-renames', commit, 'HEAD', '--', prefix, text=True)
    return {line[len(prefix):].lstrip('/') for line in out.splitlines() if line}


def entry(root, rel):
    """One path's inventory value, exactly as image_diff.inventory records it."""
    path = pathlib.Path(root) / rel
    try:
        meta = path.lstat()
    except FileNotFoundError:
        return None
    value = dict(mode=stat.S_IMODE(meta.st_mode), uid=meta.st_uid, gid=meta.st_gid, kind=stat.S_IFMT(meta.st_mode))
    value['xattrs'] = {key: os.getxattr(path, key, follow_symlinks=False).hex()
                       for key in sorted(os.listxattr(path, follow_symlinks=False))}
    if stat.S_ISLNK(meta.st_mode):
        value['target'] = os.readlink(path)
    elif stat.S_ISREG(meta.st_mode):
        value['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        value['bytes'] = meta.st_size
    elif not stat.S_ISDIR(meta.st_mode):
        value['device'] = meta.st_rdev
    return value


def without(value, *keys):
    return None if value is None else {k: v for k, v in value.items() if k not in keys}


def same_meta(a, b, mode=True):
    # Ownership, type and mode; storage xattrs of rewritten files are not compared.
    keys = ('kind', 'uid', 'gid', 'mode') if mode else ('kind', 'uid', 'gid')
    return a is not None and b is not None and all(a.get(k) == b.get(k) for k in keys)


def polkit_transform(name, text):
    """build.sh's polkit edits (package 21 review fixes 2 and 3), applied to base bytes."""
    cached = re.compile(r'(<allow_(?:any|inactive|active)>\s*)auth_(admin|self)_keep(\s*</allow_)')
    text, _ = cached.subn(r'\1auth_\2\3', text)
    if name == 'org.freedesktop.Flatpak.policy':
        update = re.search(r'<action id="org\.freedesktop\.Flatpak\.app-update">.*?</action>', text, re.S)
        imply = re.compile(r'(<annotate key="org\.freedesktop\.policykit\.imply">)([^<]*)(</annotate>)')
        kept = 'org.freedesktop.Flatpak.runtime-update'
        text = text.replace(update.group(0), imply.sub(lambda m: m.group(1) + kept + m.group(3), update.group(0)))
    return text


def account_rows(raw):
    return [line.split(':') for line in raw.decode().splitlines() if line]


def accounts_explained(name, old, new):
    """Only build-date and wheel-membership differences of package 21's sysusers line."""
    a, b = account_rows(old), account_rows(new)
    if [r[0] for r in a] != [r[0] for r in b] or any(len(x) != len(y) for x, y in zip(a, b)):
        return False
    base = name.rstrip('-')
    for x, y in zip(a, b):
        if x == y:
            continue
        if base in ('etc/shadow',) and x[:2] + x[3:] == y[:2] + y[3:]:
            continue  # sp_lstchg: the day the account was created, i.e. the build date
        members = 3 if base in ('etc/group', 'etc/gshadow') else None
        if members is not None and x[0] == 'wheel' and x[:members] == y[:members]:
            before = [m for m in x[members].split(',') if m]
            after = [m for m in y[members].split(',') if m]
            if 'ares' not in before and sorted(after) == sorted(before + ['ares']):
                continue
        return False
    return True


def subids_explained(old, new):
    a = old.decode().splitlines() if old is not None else []
    b = new.decode().splitlines()
    return not any(line.startswith('ares:') for line in a) and sorted(b) == sorted(a + [SUBID])


class Classifier:
    def __init__(self, roots, packages, owned, policy):
        self.old_root, self.new_root, self.base_root = roots
        self.packages, self.owned, self.policy = packages, owned, policy
        self.config = git_changed(PREVIOUS_SOURCE, 'os/config')
        self.policy_files = git_changed(PREVIOUS_SOURCE, 'os/policy')
        self.unmasked = policy['unmasked']

    def read(self, which, rel):
        root = {'old': self.old_root, 'new': self.new_root, 'base': self.base_root}[which]
        path = pathlib.Path(root) / rel
        return path.read_bytes() if path.is_file() and not path.is_symlink() else None

    def classify(self, rel, before, after):
        """Return (rule, reason) or None when nothing explains the difference."""
        for rule in (self.config_rule, self.policy_rule, self.manifest_rule, self.build_rule,
                     self.package_rule, self.generated_rule):
            found = rule(rel, before, after)
            if found:
                return found
        return None

    def config_rule(self, rel, before, after):
        if rel not in self.config:
            # A new directory that only holds new os/config files.
            if after and after['kind'] == stat.S_IFDIR and before is None and any(
                    c.startswith(rel + '/') for c in self.config) and pathlib.Path('os/config', rel).is_dir():
                return ('config', 'directory of new os/config files (packages 21/24)')
            return None
        source = pathlib.Path('os/config') / rel
        if not source.exists():
            return None  # removed from os/config: release 27 must not carry it
        if after is None or after['kind'] != stat.S_IFREG:
            return None
        if after['sha256'] != hashlib.sha256(source.read_bytes()).hexdigest():
            return None
        mode = CONFIG_MODES.get(rel, 0o755 if os.access(source, os.X_OK) or rel in self.policy['executables'] else 0o644)
        if after['mode'] != mode or after['uid'] != 0 or after['gid'] != 0:
            return None
        return ('config', 'os/config changed since release 13 (packages 21/24); bytes equal the source')

    def policy_rule(self, rel, before, after):
        if not rel.startswith('usr/share/aresos/policy/'):
            return None
        name = rel[len('usr/share/aresos/policy/'):]
        if name not in self.policy_files or after is None:
            return None
        if after['sha256'] != hashlib.sha256((pathlib.Path('os/policy') / name).read_bytes()).hexdigest():
            return None
        return ('policy', 'os/policy changed since release 13 (package 21: Flatpak helpers unmasked)')

    def manifest_rule(self, rel, before, after):
        folder = 'usr/share/aresos/manifest/'
        if not rel.startswith(folder) or after is None:
            return None
        name = rel[len(folder):]
        data = self.read('new', rel)
        if name == 'packages.lock.json' and json.loads(data) == json.loads(pathlib.Path('os/packages.lock.json').read_text()):
            return ('manifest', 'package lock (package 21)')
        if name == 'google-chrome.lock.json' and data == pathlib.Path('os/google-chrome.lock.json').read_bytes():
            return ('manifest', 'Chrome pin (package 21)')
        if name == 'packages.txt' and data.decode().splitlines() == sorted(self.packages['new']):
            return ('manifest', 'installed package list (packages changed)')
        if name == 'updaters.json':
            return ('manifest', 'updater audit output (Flatpak helper units unmasked, aresos-subids added)')
        return None

    def build_rule(self, rel, before, after):
        base = entry(self.base_root, rel)
        if rel in CHROME_LINKS:
            if after and after['kind'] == stat.S_IFLNK and after['target'] == CHROME_LINKS[rel] and before is None:
                return ('build', 'package 21: direct Chrome command links into /usr/lib/opt')
            return None
        if rel == 'etc/default/google-chrome':
            if before is None and self.read('new', rel) == CHROME_DEFAULTS:
                return ('build', 'package 21: Chrome adds no repository')
            return None
        if rel == 'usr/lib/opt' and before is None and after and after['kind'] == stat.S_IFDIR:
            return ('build', 'package 21: Chrome kept in the image under /usr/lib/opt')
        if rel.startswith('usr/lib/opt/google'):
            if before is None and ('/opt/google' + rel[len('usr/lib/opt/google'):]) in self.owned['new']:
                return ('build', 'package 21: Chrome RPM files moved from /var/opt to /usr/lib/opt')
            return None
        if rel == 'var/opt' and after is None and before and before['kind'] == stat.S_IFDIR \
                and not self.policy['old_has_children'](rel):
            return ('build', 'package 21: /var/opt (empty) removed from the image')
        if rel == 'etc/cron.daily' and after is None and before and before['kind'] == stat.S_IFDIR \
                and not self.policy['old_has_children'](rel):
            return ('build', "package 21: Chrome's daily job removed, leaving no empty cron.daily")
        if rel == SUBIDS_LINK[0]:
            if before is None and after and after['kind'] == stat.S_IFLNK and after['target'] == SUBIDS_LINK[1]:
                return ('build', 'package 21: aresos-subids.service enabled')
            return None
        if rel.endswith('.policy') and rel.startswith('usr/share/polkit-1/actions/'):
            old, new, original = self.read('old', rel), self.read('new', rel), self.read('base', rel)
            if None not in (old, new, original) and old == original and same_meta(after, base) \
                    and new.decode() == polkit_transform(pathlib.PurePosixPath(rel).name, original.decode()):
                return ('build', 'package 21: polkit defaults made uncached (and the Flatpak app-update implication)')
            return None
        if rel in BASE_RESTORED:
            if after == base and before != base and before is not None:
                if rel == 'etc/profile.d/brew-bash-completion.sh':
                    old, original = self.read('old', rel).decode().splitlines(), self.read('base', rel).decode().splitlines()
                    if old != original[:1] + [BREW_GUARD] + original[1:]:
                        return None
                elif not same_meta(before, base, mode=False) or before.get('sha256') != base.get('sha256')                         or before['mode'] != 0o700:
                    return None
                return ('build', BASE_RESTORED[rel])
            return None
        name = pathlib.PurePosixPath(rel).name
        if name in self.unmasked and rel.startswith(('etc/systemd/system/', 'etc/systemd/user/')):
            if rel.count('/') == 3 and before and before['kind'] == stat.S_IFLNK and before['target'] == '/dev/null' \
                    and after == base and (after is None or after.get('target') != '/dev/null'):
                return ('build', 'package 21: Flatpak helper unit no longer masked')
            if after == base and after is not None:
                return ('build', 'package 21: Flatpak helper unit keeps its base enablement')
            return None
        if rel in ('etc/group', 'etc/gshadow', 'etc/shadow', 'etc/group-', 'etc/gshadow-', 'etc/shadow-'):
            old, new = self.read('old', rel), self.read('new', rel)
            if old is not None and new is not None and same_meta(before, after) \
                    and accounts_explained(rel, old, new):
                return ('build', 'package 21: ares in wheel (sysusers); shadow creation dates are build dates')
            return None
        if rel in ('etc/subuid', 'etc/subgid'):
            new = self.read('new', rel)
            if new is not None and subids_explained(self.read('old', rel), new):
                return ('build', 'package 21: aresos-subids adds one range for ares')
            return None
        if rel in ('etc/subuid-', 'etc/subgid-'):
            primary = rel[:-1]
            if before is None and self.read('new', rel) == (self.read('old', primary) or b''):
                return ('build', "package 21: usermod's backup of the previous subid file")
            return None
        return None

    def package_rule(self, rel, before, after):
        path = '/' + rel
        if (before is not None and path in self.owned['old']) or (after is not None and path in self.owned['new']):
            return ('package', 'owned by a changed package')
        if before is None and after is not None and 'google-chrome' in pathlib.PurePosixPath(rel).name \
                and rel.startswith('usr/share/'):
            return ('package', "Chrome's install script (xdg-icon-resource / xdg-desktop-menu)")
        return None

    def generated_rule(self, rel, before, after):
        for pattern, reason in GENERATED:
            if fnmatch.fnmatchcase(rel, pattern):
                return ('generated', reason)
        return None


def arch(nevra):
    # gpg-pubkey entries have no architecture.
    tail = nevra.rsplit('-', 1)[-1]
    return tail.rsplit('.', 1)[1] if '.' in tail else ''


def package_diff(old, new, old_lock, new_lock):
    added, removed = sorted(set(new) - set(old)), sorted(set(old) - set(new))
    expected = sorted(set(new_lock) - set(old_lock))
    assert added == expected, 'STOP: added packages differ from the lock change: ' + repr(sorted(set(added) ^ set(expected)))
    rows = []
    for nevra in added + removed:
        name = (new.get(nevra) or old.get(nevra))
        assert name in PACKAGE_REASONS, 'STOP: unexplained package change: ' + nevra
        rows.append(dict(nevra=nevra, change='added' if nevra in added else 'removed', reason=PACKAGE_REASONS[name]))
    added_keys = {(new[n], arch(n)) for n in added}
    for nevra in removed:
        assert (old[nevra], arch(nevra)) in added_keys, 'STOP: removed package without its locked replacement: ' + nevra
    return rows, added, removed


def main(tools, run=None):
    """Compare release 13 with localhost/aresos:ci; write evidence/image-diff."""
    from build_tools import validate
    image_diff.TOOLS = validate(tools)
    command = image_diff.command
    evidence = pathlib.Path('evidence/image-diff')
    evidence.mkdir(parents=True)
    previous = json.loads(pathlib.Path(PREVIOUS).read_text())
    base_reference = json.loads(pathlib.Path('os/manifest/base.json').read_text())['reference']
    assert previous['base'] == base_reference, 'STOP: release 13 was built on another base'
    images = dict(old=previous['reference'], new=NEW, base=base_reference)
    mounts, roots, packages, names = [], {}, {}, {}
    try:
        for name, image in images.items():
            container = command('podman', 'create', '--pull=never', '--network=none', '--entrypoint=/usr/bin/true', image)
            mounts.append(container)
            roots[name] = pathlib.Path(command('podman', 'mount', container))
            if name != 'base':
                rows = command('podman', 'run', '--pull=never', '--network=none', '--read-only', '--rm',
                               '--entrypoint=/usr/bin/rpm', image, '-qa', '--qf', '%{NEVRA}\t%{NAME}\n').splitlines()
                names[name] = dict(row.split('\t') for row in rows)
                packages[name] = sorted(names[name])
        old_lock = [p['nevra'] for p in json.loads(git_bytes(PREVIOUS_SOURCE, 'os/packages.lock.json'))['packages']]
        new_lock = [p['nevra'] for p in json.loads(pathlib.Path('os/packages.lock.json').read_text())['packages']]
        new_lock.append(json.loads(pathlib.Path('os/google-chrome.lock.json').read_text())['nevra'])
        image_lock = json.loads((roots['old'] / 'usr/share/aresos/manifest/packages.lock.json').read_text())
        assert [p['nevra'] for p in image_lock['packages']] == old_lock, 'STOP: release 13 lock differs from its source'
        package_rows, added, removed = package_diff(names['old'], names['new'], old_lock, new_lock)
        (evidence / 'packages.json').write_text(json.dumps(dict(old=packages['old'], new=packages['new'], changes=package_rows), indent=2) + '\n')

        def owned(image, nevras):
            if not nevras:
                return set()
            output = command('podman', 'run', '--pull=never', '--network=none', '--read-only', '--rm',
                             '--entrypoint=/usr/bin/rpm', image, '-ql', *nevras)
            return {line for line in output.splitlines() if line.startswith('/')}
        ownership = dict(old=owned(images['old'], removed), new=owned(images['new'], added))

        inventories = {}
        for name in ('old', 'new'):
            inventories[name] = image_diff.inventory(roots[name])
            with gzip.open(evidence / (name + '-files.json.gz'), 'wt', encoding='utf-8') as stream:
                json.dump(inventories[name], stream, sort_keys=True)
                stream.write('\n')
        old, new = inventories['old'], inventories['new']
        changed = sorted(p for p in old.keys() | new.keys() if old.get(p) != new.get(p))

        def masked(root):
            return {line.strip() for name in ('masked-system-units.txt', 'masked-user-units.txt')
                    for line in (root / 'usr/share/aresos/policy' / name).read_text().splitlines() if line.strip()}
        unmasked = masked(roots['old']) - masked(roots['new'])
        assert unmasked <= {'flatpak-system-helper.service', 'flatpak-portal.service', 'flatpak-session-helper.service'}, \
            'STOP: unreviewed unit unmasked: ' + repr(sorted(unmasked))
        children = lambda rel: any(p.startswith(rel + '/') for p in old)
        policy = dict(unmasked=unmasked, executables=CHMOD_0755, old_has_children=children)
        classifier = Classifier((roots['old'], roots['new'], roots['base']), packages, ownership, policy)
        details, unexplained = {}, []
        for rel in changed:
            found = classifier.classify(rel, old.get(rel), new.get(rel))
            if found is None:
                unexplained.append(rel)
                details[rel] = dict(rule='UNEXPLAINED', before=old.get(rel), after=new.get(rel))
            else:
                details[rel] = dict(rule=found[0], reason=found[1], before=old.get(rel), after=new.get(rel))
        with gzip.open(evidence / 'classified-files.json.gz', 'wt', encoding='utf-8') as stream:
            json.dump(details, stream, sort_keys=True)
            stream.write('\n')
        units = {rel: dict(rule=row['rule'], reason=row.get('reason')) for rel, row in details.items()
                 if re.search(r'(^|/)systemd/', rel)}
        assert not any(row['rule'] == 'generated' for row in units.values()), 'STOP: a unit changed only as a generated file'
        counts = {}
        for row in details.values():
            key = row['rule'] + ': ' + row.get('reason', 'no rule')
            counts[key] = counts.get(key, 0) + 1
        generated = sorted(rel for rel, row in details.items() if row['rule'] == 'generated')

        configs = [json.loads(command('skopeo', 'inspect', '--config', 'containers-storage:' + images[n])) for n in ('old', 'new')]
        base_config = json.loads(command('skopeo', 'inspect', '--config', 'containers-storage:' + base_reference))
        base_ids = base_config['rootfs']['diff_ids']
        assert configs[0]['rootfs']['diff_ids'][:len(base_ids)] == base_ids, 'STOP: release 13 base ancestry differs'
        assert configs[1]['rootfs']['diff_ids'][:len(base_ids)] == base_ids, 'STOP: release 27 base ancestry differs'
        old_config, new_config = (dict(c['config']) for c in configs)
        old_labels, new_labels = old_config.pop('Labels'), new_config.pop('Labels')
        assert old_config == new_config, 'STOP: unrelated OCI runtime configuration changed'
        labels = {k: dict(before=old_labels.get(k), after=new_labels.get(k)) for k in sorted(old_labels.keys() | new_labels.keys())
                  if old_labels.get(k) != new_labels.get(k)}
        assert set(labels) <= {'org.opencontainers.image.revision', 'io.buildah.version'}, 'STOP: unexplained label change: ' + repr(sorted(labels))
        assert new_labels['org.opencontainers.image.source'] == 'https://github.com/Ares-Empire/AresOS'
        assert new_labels['org.opencontainers.image.revision'] == os.environ['GITHUB_SHA']
        result = dict(status='passed' if not unexplained else 'stopped', previous=images['old'], pinned_base=base_reference,
            previous_source=PREVIOUS_SOURCE, method='full rebuild compared with release 13; every difference classified',
            package_count=dict(old=len(packages['old']), new=len(packages['new'])), packages=package_rows,
            compared_files=[len(old), len(new)], changed_paths=len(changed), rules=dict(sorted(counts.items())),
            units=units, generated=generated, unexplained=unexplained[:500], unexplained_count=len(unexplained),
            labels=labels, base_ancestry_verified=True, runtime_config_equal=True,
            metadata_note='File mtimes/inodes are storage metadata, excluded as in release 13; full classified inventory in classified-files.json.gz.')
        (evidence / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        assert not unexplained, f'STOP: {len(unexplained)} unexplained image differences, first: {unexplained[:20]}'
        print(f'IMAGE_DIFF_PASSED: {len(changed)} changed paths, all explained: ' + json.dumps(counts, sort_keys=True))
    finally:
        for container in reversed(mounts):
            command('podman', 'unmount', container)
            command('podman', 'rm', container)
