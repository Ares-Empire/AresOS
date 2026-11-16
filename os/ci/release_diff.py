"""Releases 27 and 28: compare the full rebuild with the release before it; explain every difference.

Release 27 (package 27): release 13 is release 6's image plus two keyboard
files. Release 27 rebuilds the reviewed Containerfile on the same pinned base.
Every package, file and unit difference must trace to a reviewed source change
of packages 21 and 24 (or a renewed pin), to a reviewed build step, or to a
database the package transaction regenerates. Anything else stops the release
before publishing. Each rule verifies content where the build is
deterministic; the regenerated databases are listed by path so a reviewer sees
each one.

Release 28 (package 42) is compared with release 27 the same way, with its own
rules (Classifier28): each difference traces to a package merged since release
27 (named by its commit on main), a pinned input, or a reviewed build step.
"""
import collections
import fnmatch
import gzip
import hashlib
import json
import os
import pathlib
import posixpath
import re
import stat
import struct
import subprocess
import xml.etree.ElementTree as ET

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
    # Package 23 adds Java 25 to the lock; dnf resolved its three new
    # dependencies with it (run 42803572026, weak dependencies off).
    'java-25-openjdk-headless': 'package 23: Java 25, which Prism runs Minecraft 26.2 with',
    'java-25-openjdk-crypto-adapter': "package 23: Java 25's NSS crypto adapter, a dependency of java-25-openjdk-headless",
    'javapackages-filesystem': "package 23: Java's shared directories, a dependency of java-25-openjdk-headless",
    'tzdata-java': "package 23: Java's time zone data, a dependency of java-25-openjdk-headless",
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
# Found by release 27's second run (42817411051); each rule names exact paths.
# usr/lib/sysimage/rpm links to usr/share/rpm, where the rpm database file is.
RPM_DATABASE = 'usr/share/rpm/rpmdb.sqlite'
# build.sh's polkit edit writes through this policy link to its alternative.
POLKIT_LINK_TARGETS = {'usr/share/polkit-1/actions/org.fedoraproject.FirewallD1.desktop.policy.choice':
                       'usr/share/polkit-1/actions/org.fedoraproject.FirewallD1.policy'}
# Chrome's install script links its NSS names to the system libraries.
CHROME_NSS_LINKS = {'usr/lib/opt/google/chrome/' + name: '/lib64/' + target for name, target in (
    ('libnspr4.so.0d', 'libnspr4.so'), ('libnss3.so.1d', 'libnss3.so'), ('libnssutil3.so.1d', 'libnssutil3.so'),
    ('libplc4.so.0d', 'libplc4.so'), ('libplds4.so.0d', 'libplds4.so'), ('libsmime3.so.1d', 'libsmime3.so'),
    ('libssl3.so.1d', 'libssl3.so'))}
# Parent directories of Chrome's RPM files that its RPM does not own.
CHROME_DIRECTORIES = ('usr/lib/opt/google', 'usr/share/gnome-control-center', 'usr/share/gnome-control-center/default-apps')
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
        if rel in CHROME_NSS_LINKS:
            if before is None and after and after['kind'] == stat.S_IFLNK and after['target'] == CHROME_NSS_LINKS[rel] \
                    and (after['mode'], after['uid'], after['gid']) == (0o777, 0, 0):
                return ('package', "package 21: Chrome's install script links its NSS names to the system libraries")
            return None
        if rel in CHROME_DIRECTORIES:
            if before is None and after and after['kind'] == stat.S_IFDIR and (after['mode'], after['uid'], after['gid']) == (0o755, 0, 0):
                return ('package', "package 21: parent directory of Chrome's RPM files")
            return None
        if rel in POLKIT_LINK_TARGETS:
            link = entry(self.new_root, POLKIT_LINK_TARGETS[rel])
            old, new, original = self.read('old', rel), self.read('new', rel), self.read('base', rel)
            if link and link['kind'] == stat.S_IFLNK and link['target'] == pathlib.PurePosixPath(rel).name \
                    and None not in (old, new, original) and old == original and same_meta(after, base) \
                    and new.decode() == polkit_transform(pathlib.PurePosixPath(POLKIT_LINK_TARGETS[rel]).name, original.decode()):
                return ('build', 'package 21: polkit defaults made uncached, written through the policy link')
            return None
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
        if rel == RPM_DATABASE:
            if before and after and before['kind'] == after['kind'] == stat.S_IFREG and same_meta(before, after):
                return ('generated', 'rpm database (package list compared separately)')
            return None
        for pattern, reason in GENERATED:
            if fnmatch.fnmatchcase(rel, pattern):
                return ('generated', reason)
        return None


# --- Release 28 (package 42): the full rebuild compared with release 27. ---
PREVIOUS_28 = 'os/manifest/releases/27.json'
# Release 27's source on main (PR #35's squash). Its image trees equal the
# source_trees release 27 records, so its os/config, os/policy and locks
# describe release 27's image exactly (test_release28 checks the trees).
PREVIOUS_SOURCE_28 = '41b06513c1972ac4ccf395c169fdf261381243b0'
PACKAGE_REASONS_28 = {name: PACKAGE_REASONS[name] for name in (
    'java-25-openjdk-headless', 'java-25-openjdk-crypto-adapter', 'javapackages-filesystem', 'tzdata-java')}
# build.sh's chmod 0755 line since package 23 (the desktop, its Java wrapper and 23b's cover).
CHMOD_0755_28 = CHMOD_0755 | {'usr/libexec/aresos-desktop', 'usr/libexec/aresos-desktop-java', 'usr/libexec/aresos-cover'}
DESKTOP_COMMAND = ('usr/bin/aresos-desktop', '../libexec/aresos-desktop')
PRISM = 'usr/lib/prismlauncher'
PRISM_COMMAND = ('usr/bin/prismlauncher', '/usr/lib/prismlauncher/bin/prismlauncher')
PRISM_FILES = 'usr/share/aresos/manifest/prism-files.sha256'
MINECRAFT = 'usr/share/aresos/minecraft'
SCHEMAS = 'usr/share/glib-2.0/schemas/gschemas.compiled'
SCHEMA_OVERRIDE = 'usr/share/glib-2.0/schemas/zz-aresos.gschema.override'
FONT_CACHES = 'usr/lib/fontconfig/cache/'
FONT_CACHE_MAGIC = 0xfc02fc04
# fontconfig's cache header (FcCache) starts with its magic, version, file size
# and the offset of the folder's name, which follows the header. The sizes and
# the offset are intptr_t, so each format has its own layout. Fedora's
# /usr/bin/fc-cache is a script that runs fc-cache-32 (fontconfig.i686, in the
# base for Steam) and fc-cache-64, so every folder has a cache in both formats
# (release 28's dry run, run 43832912792).
FONT_CACHE_LAYOUTS = {'le64': ('<IiqQ', 64), 'le32d4': ('<IiiI', 40)}
# java-25-openjdk-headless installs its man pages here, but its file list names
# only the pages, not these folders (the pinned RPM's header, and rpm -ql in the
# dry run); rpm creates a missing parent folder of a file it installs, root's 0755.
JAVA_MAN_FOLDERS = ('usr/lib/jvm/java-25-openjdk/man', 'usr/lib/jvm/java-25-openjdk/man/man1')
# The unit folders whose drop-ins os/tests/audit.py lists as a unit's sources.
AUDIT_UNIT_FOLDERS = ('usr/lib/systemd/', 'usr/local/lib/systemd/', 'etc/systemd/')
ALTERNATIVES = 'etc/alternatives/'
ALTERNATIVES_ADMIN = 'etc/alternatives-admindir/'
CROWN = 'usr/share/themes/Ares-Crown/labwc'
RC_XML = 'usr/share/aresos/labwc/rc.xml'
# Release 27's regenerated databases, without the font caches: release 28
# rebuilds those on purpose (package 23b), and its own rule checks each one.
GENERATED_28 = tuple(row for row in GENERATED if 'fontconfig' not in row[0])


def root_owned(value, mode):
    return value['uid'] == 0 and value['gid'] == 0 and value['mode'] == mode


def file_sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def minecraft_pins(lock, lock_path='os/minecraft/desktop.lock.json'):
    """{image path: (sha256, size or None, reason)} for each input build.sh installs from os/minecraft/desktop.lock.json."""
    pins = {}
    for library in lock['fabric_loader']['libraries']:
        _, artifact, version = library['name'].split(':')
        pins[f'{MINECRAFT}/libraries/{artifact}-{version}.jar'] = (
            library['sha256'], library.get('size'), f"package 23: Fabric Loader library {library['name']} from its pin")
    for mod in lock['mods']:
        if 'url' in mod:
            reason = f"package 23: {mod['name']} {mod['version']} from its pin"
        else:
            # A release build accepts only the jar equal to its pin (build.sh configure).
            reason = 'package 23: the AresOS mod jar, built from this commit and equal to its pin'
        pins[f"{MINECRAFT}/mods/{mod['file']}"] = (mod['sha256'], mod.get('size'), reason)
    for component in lock['components']:
        pins[f"{MINECRAFT}/patches/{component['file']}"] = (
            component['sha256'], component.get('size'), f"package 23: Prism's {component['uid']} {component['version']} metadata from its pin")
    pins[f'{MINECRAFT}/desktop.lock.json'] = (file_sha256(lock_path), None, "package 23: the desktop's lock, os/minecraft/desktop.lock.json")
    return pins


GVDB_NONE = 0xffffffff


def gvdb_entries(data):
    """Every value in a little-endian GVDB file (glib's gschemas.compiled), by its full name.

    A nested hash table ('H') adds its name and '/' to its items' names; a
    value ('v') is its serialised GVariant bytes; a list ('L') becomes the
    sorted names of its children, one per line. Malformed data raises ValueError.
    """
    if data[:8] != b'GVariant' or len(data) < 24:
        raise ValueError('not a little-endian GVDB file')
    _, _, start, end = struct.unpack_from('<IIII', data, 8)
    entries = {}

    def table(start, end, prefix):
        if not 0 <= start <= end <= len(data) or end - start < 8:
            raise ValueError('GVDB table outside the file')
        bloom, buckets = struct.unpack_from('<II', data, start)
        first = start + 8 + 4 * (bloom & ((1 << 27) - 1)) + 4 * buckets
        count, rest = divmod(end - first, 24)
        if count < 0 or rest:
            raise ValueError('GVDB table has a partial item')
        items = [struct.unpack_from('<IIIHccII', data, first + 24 * i) for i in range(count)]
        names = {}

        def name(index, depth=0):
            if index not in names:
                if index >= count or depth > count:
                    raise ValueError('GVDB item parent outside its table')
                _, parent, key, size, *_ = items[index]
                if key + size > len(data):
                    raise ValueError('GVDB key outside the file')
                own = data[key:key + size].decode()
                names[index] = (name(parent, depth + 1) if parent != GVDB_NONE else '') + own
            return names[index]

        for index, (_, _, _, _, kind, _, value_start, value_end) in enumerate(items):
            full = prefix + name(index)
            if not value_start <= value_end <= len(data):
                raise ValueError('GVDB value outside the file')
            if kind == b'v':
                entries[full] = data[value_start:value_end]
            elif kind == b'H':
                table(value_start, value_end, full + '/')
            elif kind == b'L':
                children = struct.unpack_from(f'<{(value_end - value_start) // 4}I', data, value_start)
                entries[full + '/'] = '\n'.join(sorted(name(child) for child in children)).encode()
            elif kind == b'\0' and value_start == value_end == 0:
                # A name without a value: glib-compile-schemas writes the root of a schema without keys this way.
                entries[full + '/'] = b''
            else:
                raise ValueError(f'unknown GVDB item type {kind!r}')
    table(start, end, '')
    return entries


GV_FIXED = {'b': (1, '?'), 'y': (1, 'B'), 'n': (2, 'h'), 'q': (2, 'H'), 'i': (4, 'i'), 'u': (4, 'I'),
            'h': (4, 'i'), 'x': (8, 'q'), 't': (8, 'Q'), 'd': (8, 'd')}


def gv_type(signature, at=0):
    """The one complete type at `at` in a GVariant type string, and the index after it."""
    code = signature[at]
    if code in GV_FIXED or code in 'sogv':
        return code, at + 1
    if code in 'am':
        _, end = gv_type(signature, at + 1)
        return signature[at:end], end
    if code in '({':
        close, end = ')' if code == '(' else '}', at + 1
        while signature[end] != close:
            _, end = gv_type(signature, end)
        return signature[at:end + 1], end + 1
    raise ValueError('unknown GVariant type ' + signature)


def gv_members(signature):
    members, at = [], 1
    while at < len(signature) - 1:
        member, at = gv_type(signature, at)
        members.append(member)
    return members


def gv_align(signature):
    if signature in GV_FIXED:
        return GV_FIXED[signature][0]
    if signature in 'sog':
        return 1
    if signature == 'v':
        return 8
    if signature[0] in 'am':
        return gv_align(signature[1:])
    return max([gv_align(member) for member in gv_members(signature)], default=1)


def gv_fixed(signature):
    """The fixed size of a type, or None when its size varies."""
    if signature in GV_FIXED:
        return GV_FIXED[signature][0]
    if signature in 'sogv' or signature[0] in 'am':
        return None
    size = 0
    for member in gv_members(signature):
        member_size = gv_fixed(member)
        if member_size is None:
            return None
        size = -(-size // gv_align(member)) * gv_align(member) + member_size
    alignment = gv_align(signature)
    return max(1, -(-size // alignment) * alignment)


def gv_offset_size(size):
    return 0 if size == 0 else 1 if size <= 0xff else 2 if size <= 0xffff else 4 if size <= 0xffffffff else 8


def gvariant(signature, data):
    """Decode serialised GVariant bytes (normal form, little-endian) of one type.

    Strings are str, variants (type, value), maybes None or [value], arrays
    lists, tuples and dictionary entries tuples. Malformed data raises ValueError.
    """
    if signature in GV_FIXED:
        size, code = GV_FIXED[signature]
        if len(data) != size:
            raise ValueError(f'{signature} needs {size} bytes, got {len(data)}')
        return struct.unpack('<' + code, data)[0]
    if signature in 'sog':
        if not data or data[-1] != 0 or 0 in data[:-1]:
            raise ValueError('malformed GVariant string')
        return data[:-1].decode()
    if signature == 'v':
        split = data.rindex(b'\0')
        inner = data[split + 1:].decode()
        if not inner or gv_type(inner)[1] != len(inner):
            raise ValueError('malformed variant type ' + inner)
        return (inner, gvariant(inner, data[:split]))
    if signature[0] == 'm':
        member = signature[1:]
        if not data:
            return None
        return [gvariant(member, data if gv_fixed(member) is not None else data[:-1])]
    if signature[0] == 'a':
        member, size = signature[1:], gv_fixed(signature[1:])
        if size is not None:
            if len(data) % size:
                raise ValueError('array of fixed members has a partial member')
            return [gvariant(member, data[at:at + size]) for at in range(0, len(data), size)]
        if not data:
            return []
        width = gv_offset_size(len(data))
        table = int.from_bytes(data[-width:], 'little')
        count, rest = divmod(len(data) - table, width)
        if rest or table > len(data):
            raise ValueError('malformed array framing')
        values, start, alignment = [], 0, gv_align(member)
        for index in range(count):
            end = int.from_bytes(data[table + index * width:table + (index + 1) * width], 'little')
            start = -(-start // alignment) * alignment
            if not start <= end <= table:
                raise ValueError('malformed array member offset')
            values.append(gvariant(member, data[start:end]))
            start = end
        return values
    if signature[0] in '({':
        members = gv_members(signature)
        if gv_fixed(signature) is not None and len(data) != gv_fixed(signature):
            raise ValueError('fixed tuple of the wrong size')
        width, used, position, values = gv_offset_size(len(data)), 0, 0, []
        for index, member in enumerate(members):
            start = -(-position // gv_align(member)) * gv_align(member)
            size = gv_fixed(member)
            if size is not None:
                end = start + size
            elif index == len(members) - 1:
                end = len(data) - width * used
            else:
                used += 1
                end = int.from_bytes(data[len(data) - width * used:len(data) - width * (used - 1)], 'little')
            if not start <= end <= len(data):
                raise ValueError('malformed tuple member offset')
            values.append(gvariant(member, data[start:end]))
            position = end
        return tuple(values)
    raise ValueError('unknown GVariant type ' + signature)


def gv_text(signature, value):
    """GVariant text, as g_variant_print writes it without type annotations (doubles in Python's shortest form)."""
    if signature == 'b':
        return 'true' if value else 'false'
    if signature == 'y':
        return f'0x{value:02x}'
    if signature in GV_FIXED:
        return repr(value)
    if signature in 'sog':
        return "'" + value.replace('\\', '\\\\').replace("'", "\\'") + "'"
    if signature == 'v':
        return '<' + gv_text(*value) + '>'
    if signature[0] == 'm':
        return 'nothing' if value is None else 'just ' + gv_text(signature[1:], value[0])
    if signature.startswith('a{'):
        key, item = gv_members(signature[1:])
        return '{' + ', '.join(f'{gv_text(key, k)}: {gv_text(item, v)}' for k, v in value) + '}'
    if signature[0] == 'a':
        return '[' + ', '.join(gv_text(signature[1:], item) for item in value) + ']'
    members = gv_members(signature)
    return '(' + ', '.join(gv_text(m, v) for m, v in zip(members, value)) + (',' if len(members) == 1 else '') + ')'


def schema_key(raw):
    """A compiled key: (default as text, {extension code: value as text}), the per-desktop
    overrides ('d') as {desktop: value as text}."""
    signature, value = gvariant('v', raw)
    if signature[0] != '(':
        return gv_text(signature, value), {}
    members = gv_members(signature)
    extensions = {}
    for member, item in zip(members[1:], value[1:]):
        inner = gv_members(member)
        if len(inner) != 2 or inner[0] != 'y':
            raise ValueError('unknown schema key extension ' + member)
        code = chr(item[0])
        if code == 'd':
            extensions[code] = {desktop: gv_text(*override) for desktop, override in item[1]}
        else:
            extensions[code] = gv_text(inner[1], item[1])
    return gv_text(members[0], value[0]), extensions


def schema_overrides(text):
    """{(schema, key): [(desktop or '', value text)]} from a gschema override file."""
    settings, group = {}, None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('[') and line.endswith(']'):
            schema, _, desktop = line[1:-1].partition(':')
            group = (schema.strip(), desktop.strip())
            continue
        if group is None or '=' not in line:
            raise ValueError('malformed override line: ' + line)
        key, _, value = line.partition('=')
        settings.setdefault((group[0], key.strip()), []).append((group[1], value.strip()))
    return settings


def schema_changes(old, new, override):
    """Every compiled key that differs between two gschemas.compiled files, as rows.

    None unless each difference is a key the override file sets, its default
    and other extensions unchanged except what the override sets (a desktop's
    value, or the default itself for a group without a desktop), and every key
    of the override carries exactly the override's value in the new file.
    """
    settings = schema_overrides(override)
    before, after = gvdb_entries(old), gvdb_entries(new)
    for (schema, key), values in settings.items():
        if schema + '/' + key not in after:
            return None
        default, extensions = schema_key(after[schema + '/' + key])
        for desktop, value in values:
            if (extensions.get('d', {}).get(desktop) if desktop else default) != value:
                return None
    rows = []
    for name in sorted(before.keys() | after.keys()):
        if before.get(name) == after.get(name):
            continue
        schema, _, key = name.rpartition('/')
        if (schema, key) not in settings or name not in before or name not in after:
            return None
        (old_default, old_extensions), (new_default, new_extensions) = schema_key(before[name]), schema_key(after[name])
        values = settings[(schema, key)]
        desktops = dict(old_extensions.get('d', {}), **{desktop: value for desktop, value in values if desktop})
        defaults = [value for desktop, value in values if not desktop]
        if new_default != (defaults[-1] if defaults else old_default) or new_extensions.get('d', {}) != desktops:
            return None
        if {k: v for k, v in old_extensions.items() if k != 'd'} != {k: v for k, v in new_extensions.items() if k != 'd'}:
            return None
        rows.append(dict(schema=schema, key=key, before=gv_text(*gvariant('v', before[name])),
                         after=gv_text(*gvariant('v', after[name]))))
    return rows


def font_cache(data, layout='le64'):
    """(version, font folder) of a little-endian fontconfig cache file in one of FONT_CACHE_LAYOUTS; ValueError otherwise."""
    header, size_of_header = FONT_CACHE_LAYOUTS[layout]
    if len(data) < size_of_header:
        raise ValueError('too short for a fontconfig cache')
    magic, version, size, offset = struct.unpack_from(header, data, 0)
    if magic != FONT_CACHE_MAGIC or size != len(data) or not size_of_header <= offset < len(data):
        raise ValueError('not a fontconfig cache')
    end = data.find(b'\0', offset)
    if end < 0:
        raise ValueError('fontconfig cache folder name has no end')
    folder = data[offset:end].decode()
    if not folder.startswith('/'):
        raise ValueError('fontconfig cache folder is not absolute')
    return version, folder


def audit_changes(old, new, dropin):
    """The units whose sources differ between two updater audits (os/tests/audit.py's JSON), as rows.

    None unless both list the same units in the same order, every field but
    `sources` is equal (so no state, command or "suspicious" verdict changed),
    and each changed unit keeps its old sources in order and gains only paths
    for which dropin(scope, unit, path) is true.
    """
    try:
        before, after = json.loads(old), json.loads(new)
    except (TypeError, ValueError, UnicodeDecodeError):
        return None
    if not isinstance(before, list) or not isinstance(after, list) or len(before) != len(after):
        return None
    rows = []
    for unit_before, unit_after in zip(before, after):
        if not isinstance(unit_before, dict) or not isinstance(unit_after, dict) \
                or unit_before.keys() != unit_after.keys() or not {'scope', 'name', 'sources'} <= unit_before.keys() \
                or not isinstance(unit_before['sources'], list) or not isinstance(unit_after['sources'], list):
            return None
        if any(unit_before[key] != unit_after[key] for key in unit_before if key != 'sources'):
            return None
        old_sources, new_sources = unit_before['sources'], unit_after['sources']
        if old_sources == new_sources:
            continue
        added, kept = [], 0
        for source in new_sources:
            if kept < len(old_sources) and source == old_sources[kept]:
                kept += 1
            else:
                added.append(source)
        if kept != len(old_sources) or not all(isinstance(path, str) and dropin(unit_after['scope'], unit_after['name'], path)
                                               for path in added):
            return None
        rows.append(dict(scope=unit_after['scope'], unit=unit_after['name'], added=added))
    return rows


def alternatives_admin(raw):
    """(links {link path: alternative name}, targets) of an alternatives admin file, or None when malformed.

    The file names the master link, then pairs of slave name and link up to an
    empty line, then each alternative: its target (after an optional
    @family@), its priority and its slave targets (empty when missing).
    """
    try:
        lines = raw.decode().split('\n')
    except UnicodeDecodeError:
        return None
    if len(lines) < 4 or lines[0] not in ('auto', 'manual') or not lines[1].startswith('/'):
        return None
    links, at = {lines[1]: None}, 2
    while at + 1 < len(lines) and lines[at]:
        if not lines[at + 1].startswith('/'):
            return None
        links[lines[at + 1]] = lines[at]
        at += 2
    if at >= len(lines) or lines[at]:
        return None
    targets = []
    for line in lines[at + 1:]:
        found = re.fullmatch(r'(?:@[^@/]+@)?(/.*)', line)
        if found:
            targets.append(found.group(1))
        elif line and not re.fullmatch(r'-?[0-9]+', line):
            return None
    return (links, targets) if targets else None


def crown_digest(folder):
    """os/ci/image-checks.sh's Ares-Crown checksum: each file's SHA-256 and name, by name, hashed again."""
    files = sorted(pathlib.Path(folder).iterdir(), key=lambda path: path.name)
    return hashlib.sha256('\n'.join(f'{file_sha256(path)}  {path.name}' for path in files).encode()).hexdigest()


def crown_pin(checks='os/ci/image-checks.sh'):
    pins = re.findall(r"assert crown == '([0-9a-f]{64})'", pathlib.Path(checks).read_text())
    assert len(pins) == 1, 'STOP: image-checks.sh must pin the Ares-Crown theme exactly once'
    return pins[0]


def rc_xml_settings(raw):
    """Each setting of a labwc rc.xml as one canonical line: a keybind, mouse or window rule, or a whole other section."""
    lines = []
    for section in ET.fromstring(raw):
        if section.tag in ('keyboard', 'mouse', 'windowRules'):
            parts = list(section)
        else:
            parts = [section]
        for part in parts:
            part.tail = None
            lines.append(section.tag + ': ' + ET.canonicalize(ET.tostring(part, encoding='unicode'), strip_text=True))
    return lines


def rc_xml_changes(old, new):
    """The rc.xml settings release 28 adds and removes (comments and layout ignored)."""
    before, after = collections.Counter(rc_xml_settings(old)), collections.Counter(rc_xml_settings(new))
    return dict(added=sorted((after - before).elements()), removed=sorted((before - after).elements()))


class Classifier28:
    """Release 28's rules: each names the merged package, pin or reviewed build step behind a difference."""

    def __init__(self, roots, packages, owned, policy):
        self.old_root, self.new_root, self.base_root = (pathlib.Path(root) for root in roots)
        self.packages, self.owned, self.policy = packages, owned, policy
        self.config = git_changed(PREVIOUS_SOURCE_28, 'os/config')
        lock = json.loads(pathlib.Path('os/minecraft/desktop.lock.json').read_text())
        self.pins = minecraft_pins(lock)
        self.mod_pin = next(mod['sha256'] for mod in lock['mods'] if mod['file'] == 'aresos.jar' and 'url' not in mod)
        self.origins, self.prism, self.groups = {}, None, None
        self.schema_rows, self.font_caches, self.updater_rows = None, [], None

    def read(self, which, rel):
        root = {'old': self.old_root, 'new': self.new_root, 'base': self.base_root}[which]
        path = root / rel
        return path.read_bytes() if path.is_file() and not path.is_symlink() else None

    def classify(self, rel, before, after):
        """Return (rule, reason) or None when nothing explains the difference."""
        for rule in (self.config_rule, self.manifest_rule, self.minecraft_rule, self.prism_rule,
                     self.alternatives_rule, self.build_rule, self.package_rule, self.generated_rule):
            found = rule(rel, before, after)
            if found:
                return found
        return None

    def origin(self, rel):
        """The packages whose commits since release 27 changed os/config/<rel>: '23 (#36)', from each commit's subject."""
        if rel not in self.origins:
            subjects = git('log', '--no-merges', '--reverse', '--format=%s', PREVIOUS_SOURCE_28 + '..HEAD', '--',
                           'os/config/' + rel, text=True).splitlines()
            labels = []
            for subject in subjects:
                number = re.search(r'\(#([0-9]+)\)\s*$', subject)
                label = subject.split(':', 1)[0].strip() + (f' (#{number.group(1)})' if number else '')
                if label not in labels:
                    labels.append(label)
            self.origins[rel] = labels
        return self.origins[rel]

    def config_rule(self, rel, before, after):
        if rel not in self.config:
            # A new folder that holds new os/config files.
            if before is None and after and after['kind'] == stat.S_IFDIR and root_owned(after, 0o755) \
                    and not after['xattrs'] and any(c.startswith(rel + '/') for c in self.config) \
                    and pathlib.Path('os/config', rel).is_dir() and self.origin(rel):
                return ('config', 'new folder of os/config files from ' + ', '.join(self.origin(rel)))
            return None
        source = pathlib.Path('os/config') / rel
        if not source.is_file() or source.is_symlink() or after is None or after['kind'] != stat.S_IFREG:
            return None  # removed from os/config: release 28 must not carry it
        mode = CONFIG_MODES.get(rel, 0o755 if os.access(source, os.X_OK) or rel in self.policy['executables'] else 0o644)
        if after['sha256'] != file_sha256(source) or not root_owned(after, mode):
            return None
        if after['xattrs'] != (before['xattrs'] if before else {}) or not self.origin(rel):
            return None
        what = 'os/config file new' if before is None else 'os/config file changed'
        return ('config', f'{what} since release 27, bytes equal the source; from ' + ', '.join(self.origin(rel)))

    def prism_files(self):
        """{path: sha256} from the image's prism-files.sha256, or None unless it lists exactly
        the regular files under usr/lib/prismlauncher with their bytes."""
        if self.prism is None:
            listed, raw = {}, self.read('new', PRISM_FILES)
            for line in (raw or b'').decode().splitlines():
                found = re.fullmatch(r'([0-9a-f]{64})  /(usr/lib/prismlauncher/.+)', line)
                if not found or found.group(2) in listed:
                    listed = None
                    break
                listed[found.group(2)] = found.group(1)
            inventory = self.policy['inventory']
            actual = {rel: value['sha256'] for rel, value in inventory.items()
                      if rel.startswith(PRISM + '/') and value['kind'] == stat.S_IFREG}
            self.prism = listed if raw and listed and listed == actual else False
        return self.prism or None

    def manifest_rule(self, rel, before, after):
        folder = 'usr/share/aresos/manifest/'
        if not rel.startswith(folder) or after is None or after['kind'] != stat.S_IFREG or not root_owned(after, 0o644):
            return None
        name, data = rel[len(folder):], self.read('new', rel)
        if name == 'packages.lock.json' and json.loads(data) == json.loads(pathlib.Path('os/packages.lock.json').read_text()):
            return ('manifest', 'package lock (package 23: Java 25 and its three dependencies)')
        if name == 'packages.txt' and data.decode().splitlines() == sorted(self.packages['new']):
            return ('manifest', 'installed package list (package 23: Java 25 and its three dependencies)')
        if name == 'prism-files.sha256' and before is None and self.prism_files():
            return ('manifest', "package 23: Prism's bundled files with their SHA-256, exactly the files in usr/lib/prismlauncher")
        if name == 'aresos-mod.json' and before is None and json.loads(data) == dict(
                sha256=self.mod_pin, source_revision=os.environ['GITHUB_SHA'], pinned_sha256=self.mod_pin):
            return ('manifest', "package 23: the mod jar's record: its pin, built from this commit")
        if name == 'updaters.json' and before is not None and before['kind'] == stat.S_IFREG:
            # build.sh's last step runs the updater audit over the image's units.
            rows = audit_changes(self.read('old', rel), data, self.audit_dropin)
            if rows:
                for row in rows:
                    row['from'] = list(dict.fromkeys(label for path in row['added'] for label in self.origin(path[1:])))
                self.updater_rows = rows
                return ('manifest', 'updater audit output: only new os/config drop-ins joined units\' sources: ' + '; '.join(
                    f"{row['unit']} from {', '.join(row['from'])}" for row in rows))
        return None

    def audit_dropin(self, scope, unit, path):
        """True for a drop-in of `unit` that a merged package added to os/config since release 27, in the image as its source."""
        names = [unit]
        if '@' in unit and '@.' not in unit:
            names.append(unit.split('@', 1)[0] + '@.' + unit.rsplit('.', 1)[1])  # the template, as the audit reads it
        rel = path[1:] if path.startswith('/') else ''
        folder, _, file = rel.rpartition('/')
        if posixpath.normpath(rel) != rel or not file.endswith('.conf') \
                or folder not in {f'{prefix}{scope}/{name}.d' for prefix in AUDIT_UNIT_FOLDERS for name in names}:
            return False
        source, now = pathlib.Path('os/config') / rel, entry(self.new_root, rel)
        return rel in self.config and entry(self.old_root, rel) is None and source.is_file() and not source.is_symlink() \
            and now is not None and now['kind'] == stat.S_IFREG and now['sha256'] == file_sha256(source) and bool(self.origin(rel))

    def minecraft_rule(self, rel, before, after):
        if rel != MINECRAFT and not rel.startswith(MINECRAFT + '/'):
            return None
        if before is not None or after is None or after['xattrs']:
            return None
        if after['kind'] == stat.S_IFDIR:
            if rel[len(MINECRAFT):].lstrip('/') in ('', 'libraries', 'mods', 'patches') and root_owned(after, 0o755):
                return ('build', "package 23: folder of the desktop's pinned Minecraft inputs")
            return None
        pin = self.pins.get(rel)
        if pin and after['kind'] == stat.S_IFREG and root_owned(after, 0o644) and after['sha256'] == pin[0] \
                and pin[1] in (None, after['bytes']):
            return ('build', pin[2])
        return None

    def prism_rule(self, rel, before, after):
        if rel == PRISM_COMMAND[0]:
            if before is None and after and after['kind'] == stat.S_IFLNK and after['target'] == PRISM_COMMAND[1] \
                    and root_owned(after, 0o777):
                return ('build', "package 23: the prismlauncher command, a link into Prism's bundle")
            return None
        if rel != PRISM and not rel.startswith(PRISM + '/'):
            return None
        if before is not None or after is None or after['uid'] or after['gid'] or after['xattrs']:
            return None
        if after['kind'] == stat.S_IFLNK:
            # Relative links that stay inside the bundle, as Prism's tarball has them.
            target = posixpath.normpath(posixpath.join('/' + posixpath.dirname(rel), after['target']))
            if not after['target'].startswith('/') and target.startswith('/' + PRISM + '/'):
                return ('build', "package 23: link inside Prism's pinned bundle")
            return None
        if after['mode'] & 0o7022:
            return None  # no setuid, setgid or sticky bit, nothing group- or world-writable
        if after['kind'] == stat.S_IFDIR:
            return ('build', "package 23: folder of Prism's pinned bundle")
        files = self.prism_files()
        if after['kind'] == stat.S_IFREG and files and files.get(rel) == after['sha256']:
            return ('build', "package 23: file of Prism's pinned bundle, as prism-files.sha256 records it")
        return None

    def alternatives(self):
        """{alternative name: (links, targets)} of each new alternatives admin file whose targets
        are all files of added packages (Java's %post registers them)."""
        if self.groups is None:
            self.groups = {}
            folder = self.new_root / ALTERNATIVES_ADMIN
            for path in sorted(folder.iterdir()) if folder.is_dir() else ():
                rel = ALTERNATIVES_ADMIN + path.name
                if entry(self.old_root, rel) is not None or path.is_symlink() or not path.is_file():
                    continue
                parsed = alternatives_admin(path.read_bytes())
                if parsed and all(target in self.owned['new'] for target in parsed[1]):
                    self.groups[path.name] = parsed
        return self.groups

    def alternatives_rule(self, rel, before, after):
        if rel.startswith(ALTERNATIVES_ADMIN):
            if before is None and after and after['kind'] == stat.S_IFREG and root_owned(after, 0o644) \
                    and not after['xattrs'] and rel[len(ALTERNATIVES_ADMIN):] in self.alternatives():
                return ('package', 'package 23: alternatives record of an added package, every target a file of it')
            return None
        names = {name for group, (links, _) in self.alternatives().items() for name in [group, *links.values()] if name}
        if rel.startswith(ALTERNATIVES):
            if before is None and after and after['kind'] == stat.S_IFLNK and root_owned(after, 0o777) \
                    and rel[len(ALTERNATIVES):] in names and after['target'] in self.owned['new']:
                return ('package', 'package 23: alternatives link to a file of an added package')
            return None
        links = {link: name or group for group, (group_links, _) in self.alternatives().items()
                 for link, name in group_links.items()}
        if '/' + rel in links:
            name = links['/' + rel]
            chosen = entry(self.new_root, ALTERNATIVES + name)
            if before is None and after and after['kind'] == stat.S_IFLNK and root_owned(after, 0o777) \
                    and after['target'] == '/' + ALTERNATIVES + name and chosen and chosen['kind'] == stat.S_IFLNK \
                    and chosen['target'] in self.owned['new']:
                return ('package', f'package 23: the {name} command or file, through its alternatives link')
        return None

    def build_rule(self, rel, before, after):
        if rel == DESKTOP_COMMAND[0]:
            if before is None and after and after['kind'] == stat.S_IFLNK and after['target'] == DESKTOP_COMMAND[1] \
                    and root_owned(after, 0o777):
                return ('build', "package 23: the owner's aresos-desktop command (build.sh link)")
            return None
        if rel == SCHEMAS:
            return self.schema_rule(before, after)
        if rel.startswith(FONT_CACHES):
            return self.font_cache_rule(rel, before, after)
        if rel in ('etc/shadow', 'etc/shadow-'):
            old, new = self.read('old', rel), self.read('new', rel)
            if old is not None and new is not None and same_meta(before, after) and accounts_explained(rel, old, new):
                return ('build', 'systemd-sysusers at build: the accounts\' creation dates are the build date')
            return None
        return None

    def schema_rule(self, before, after):
        if not (before and after and before['kind'] == after['kind'] == stat.S_IFREG and same_meta(before, after)
                and before['xattrs'] == after['xattrs']):
            return None
        override = pathlib.Path('os/config') / SCHEMA_OVERRIDE
        if self.read('new', SCHEMA_OVERRIDE) != override.read_bytes():
            return None
        try:
            rows = schema_changes(self.read('old', SCHEMAS), self.read('new', SCHEMAS), override.read_text())
        except (ValueError, struct.error, UnicodeDecodeError):
            return None
        if not rows:
            return None
        self.schema_rows = rows
        return ('build', 'package 31: glib-compile-schemas compiled zz-aresos.gschema.override; only its keys changed: '
                + ', '.join(f"{row['schema']} {row['key']}" for row in rows))

    def image_folder(self, rel):
        """True when rel and each folder above it are folders (not links) in the new image."""
        parts = rel.split('/')
        return all((place := entry(self.new_root, '/'.join(parts[:depth]))) is not None and place['kind'] == stat.S_IFDIR
                   for depth in range(1, len(parts) + 1))

    def font_folder(self, folder):
        """The kind of a cache's font folder: 'folder' when it is a folder in the image under /usr, 'link' when it is a
        link release 27 has too, unchanged, to such a folder (fc-cache caches it under the link's own name, as it does
        the base's /usr/share/fonts/noto-cjk), else None."""
        rel = folder[1:]
        if not folder.startswith('/usr/') or posixpath.normpath(folder) != folder or not self.image_folder(posixpath.dirname(rel)):
            return None
        place = entry(self.new_root, rel)
        if place is not None and place['kind'] == stat.S_IFDIR:
            return 'folder'
        if place is not None and place['kind'] == stat.S_IFLNK and place == entry(self.old_root, rel):
            target = posixpath.normpath(posixpath.join(posixpath.dirname(folder), place['target']))
            if target.startswith('/usr/') and self.image_folder(target[1:]):
                return 'link'
        return None

    def font_cache_rule(self, rel, before, after):
        name = rel[len(FONT_CACHES):]
        found = re.fullmatch(r'([0-9a-f]{32})-(le64|le32d4)\.cache-([0-9]+)', name)
        if not found or after is None or after['kind'] != stat.S_IFREG or not root_owned(after, 0o644) or after['xattrs']:
            return None
        if before is not None and (before['kind'] != stat.S_IFREG or not root_owned(before, 0o644)):
            return None
        digest, layout, version = found.group(1), found.group(2), int(found.group(3))
        # Fedora's fc-cache runs fc-cache-32 and fc-cache-64: a folder cached in one format is cached in the other.
        other = entry(self.new_root, f"{FONT_CACHES}{digest}-{'le32d4' if layout == 'le64' else 'le64'}.cache-{version}")
        if other is None or other['kind'] != stat.S_IFREG:
            return None
        try:
            cache_version, folder = font_cache(self.read('new', rel), layout)
        except (ValueError, UnicodeDecodeError):
            return None
        if cache_version != version or hashlib.md5(folder.encode(), usedforsecurity=False).hexdigest() != digest:
            return None
        kind = self.font_folder(folder)
        if kind is None:
            return None
        self.font_caches.append(dict(path=rel, folder=folder, format=layout, folder_kind=kind,
                                     change='added' if before is None else 'rebuilt'))
        notes = (["32-bit, from fc-cache-32: Fedora's fc-cache runs both"] if layout == 'le32d4' else []) \
            + (['a new font folder'] if before is None else []) + (['a linked font folder release 27 has too'] if kind == 'link' else [])
        return ('build', 'package 23b: fc-cache --system-only --really-force rebuilt the system font cache'
                + (f" ({'; '.join(notes)})" if notes else ''))

    def package_rule(self, rel, before, after):
        if after is not None and '/' + rel in self.owned['new']:
            return ('package', 'file of a package added by package 23 (Java 25 and its dependencies)')
        if before is not None and '/' + rel in self.owned['old']:
            return ('package', 'file of a removed package')
        if rel in JAVA_MAN_FOLDERS:
            inventory = self.policy['inventory']
            if before is None and after and after['kind'] == stat.S_IFDIR and root_owned(after, 0o755) and not after['xattrs'] \
                    and any(path.startswith('/' + rel + '/') and inventory.get(path[1:], {}).get('kind') == stat.S_IFREG
                            for path in self.owned['new']):
                return ('package', "package 23: folder of java-25-openjdk-headless's man pages; its file list names only "
                        'the pages, so rpm creates the folder for them')
        return None

    def generated_rule(self, rel, before, after):
        if rel == RPM_DATABASE:
            if before and after and before['kind'] == after['kind'] == stat.S_IFREG and same_meta(before, after):
                return ('generated', 'rpm database (package list compared separately)')
            return None
        for pattern, reason in GENERATED_28:
            if fnmatch.fnmatchcase(rel, pattern):
                return ('generated', reason)
        return None

    def extra(self):
        """Release 28's own evidence, and the problems it finds."""
        problems = []
        crown = crown_digest(self.new_root / CROWN) if (self.new_root / CROWN).is_dir() else None
        pin = crown_pin()
        if crown != pin:
            problems.append(f'the Ares-Crown theme in the image ({crown}) is not the one image-checks.sh pins ({pin})')
        old_rc, new_rc = self.read('old', RC_XML), self.read('new', RC_XML)
        return dict(schemas=self.schema_rows, font_caches=sorted(self.font_caches, key=lambda row: row['path']),
                    updaters=self.updater_rows,
                    alternatives={name: sorted(targets) for name, (_, targets) in sorted(self.alternatives().items())},
                    theme=dict(image=crown, image_checks=pin, equal=crown == pin),
                    rc_xml=rc_xml_changes(old_rc, new_rc) if old_rc and new_rc else None), problems


RELEASES = {
    '27': dict(previous=PREVIOUS, previous_release='13', previous_source=PREVIOUS_SOURCE, reasons=PACKAGE_REASONS,
               classifier=Classifier, executables=CHMOD_0755, previous_chrome=False,
               unmasked={'flatpak-system-helper.service', 'flatpak-portal.service', 'flatpak-session-helper.service'}),
    '28': dict(previous=PREVIOUS_28, previous_release='27', previous_source=PREVIOUS_SOURCE_28, reasons=PACKAGE_REASONS_28,
               classifier=Classifier28, executables=CHMOD_0755_28, previous_chrome=True, unmasked=set()),
}


def arch(nevra):
    # gpg-pubkey entries have no architecture.
    tail = nevra.rsplit('-', 1)[-1]
    return tail.rsplit('.', 1)[1] if '.' in tail else ''


def package_diff(old, new, old_lock, new_lock, reasons=None):
    reasons = PACKAGE_REASONS if reasons is None else reasons
    added, removed = sorted(set(new) - set(old)), sorted(set(old) - set(new))
    expected = sorted(set(new_lock) - set(old_lock))
    assert added == expected, 'STOP: added packages differ from the lock change: ' + repr(sorted(set(added) ^ set(expected)))
    rows = []
    for nevra in added + removed:
        name = (new.get(nevra) or old.get(nevra))
        assert name in reasons, 'STOP: unexplained package change: ' + nevra
        rows.append(dict(nevra=nevra, change='added' if nevra in added else 'removed', reason=reasons[name]))
    added_keys = {(new[n], arch(n)) for n in added}
    for nevra in removed:
        assert (old[nevra], arch(nevra)) in added_keys, 'STOP: removed package without its locked replacement: ' + nevra
    return rows, added, removed


def main(tools, run=None, release='27', evidence='evidence/image-diff'):
    """Compare the release before `release` (13 for 27, 27 for 28) with localhost/aresos:ci; write evidence/image-diff."""
    profile = RELEASES[release]
    before_release, source = profile['previous_release'], profile['previous_source']
    from build_tools import validate
    image_diff.TOOLS = validate(tools)
    command = image_diff.command
    evidence = pathlib.Path(evidence)
    evidence.mkdir(parents=True)
    previous = json.loads(pathlib.Path(profile['previous']).read_text())
    base_reference = json.loads(pathlib.Path('os/manifest/base.json').read_text())['reference']
    assert previous['base'] == base_reference, f'STOP: release {before_release} was built on another base'
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
        old_lock = [p['nevra'] for p in json.loads(git_bytes(source, 'os/packages.lock.json'))['packages']]
        new_lock = [p['nevra'] for p in json.loads(pathlib.Path('os/packages.lock.json').read_text())['packages']]
        new_lock.append(json.loads(pathlib.Path('os/google-chrome.lock.json').read_text())['nevra'])
        image_lock = json.loads((roots['old'] / 'usr/share/aresos/manifest/packages.lock.json').read_text())
        assert [p['nevra'] for p in image_lock['packages']] == old_lock, f'STOP: release {before_release} lock differs from its source'
        if profile['previous_chrome']:
            # Release 27 already carries Chrome from its pin: only a renewed pin would add or remove it.
            old_lock.append(json.loads(git_bytes(source, 'os/google-chrome.lock.json'))['nevra'])
        package_rows, added, removed = package_diff(names['old'], names['new'], old_lock, new_lock, profile['reasons'])
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
        assert unmasked <= profile['unmasked'], \
            'STOP: unreviewed unit unmasked: ' + repr(sorted(unmasked))
        children = lambda rel: any(p.startswith(rel + '/') for p in old)
        policy = dict(unmasked=unmasked, executables=profile['executables'], old_has_children=children, inventory=new)
        classifier = profile['classifier']((roots['old'], roots['new'], roots['base']), packages, ownership, policy)
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
        problems = []
        if any(row['rule'] == 'generated' for row in units.values()):
            problems.append('a unit changed only as a generated file')
        counts = {}
        for row in details.values():
            key = row['rule'] + ': ' + row.get('reason', 'no rule')
            counts[key] = counts.get(key, 0) + 1
        generated = sorted(rel for rel, row in details.items() if row['rule'] == 'generated')
        extra = {}
        if hasattr(classifier, 'extra'):
            extra, found = classifier.extra()
            extra = dict(release=release, **extra)
            problems.extend(found)

        configs = [json.loads(command('skopeo', 'inspect', '--config', 'containers-storage:' + images[n])) for n in ('old', 'new')]
        base_config = json.loads(command('skopeo', 'inspect', '--config', 'containers-storage:' + base_reference))
        base_ids = base_config['rootfs']['diff_ids']
        if configs[0]['rootfs']['diff_ids'][:len(base_ids)] != base_ids:
            problems.append(f'release {before_release} base ancestry differs')
        if configs[1]['rootfs']['diff_ids'][:len(base_ids)] != base_ids:
            problems.append(f'release {release} base ancestry differs')
        old_config, new_config = (dict(c['config']) for c in configs)
        old_labels, new_labels = old_config.pop('Labels'), new_config.pop('Labels')
        runtime = {k: dict(before=old_config.get(k), after=new_config.get(k)) for k in sorted(old_config.keys() | new_config.keys())
                   if old_config.get(k) != new_config.get(k)}
        if runtime:
            problems.append('unrelated OCI runtime configuration changed: ' + ', '.join(runtime))
        labels = {k: dict(before=old_labels.get(k), after=new_labels.get(k)) for k in sorted(old_labels.keys() | new_labels.keys())
                  if old_labels.get(k) != new_labels.get(k)}
        if not set(labels) <= {'org.opencontainers.image.revision', 'io.buildah.version'}:
            problems.append('unexplained label change: ' + ', '.join(sorted(labels)))
        if new_labels.get('org.opencontainers.image.source') != 'https://github.com/Ares-Empire/AresOS'                 or new_labels.get('org.opencontainers.image.revision') != os.environ['GITHUB_SHA']:
            problems.append(f'release {release} source labels differ from this run')
        passed = not unexplained and not problems
        result = dict(status='passed' if passed else 'stopped', previous=images['old'], pinned_base=base_reference,
            previous_source=source, method=f'full rebuild compared with release {before_release}; every difference classified',
            package_count=dict(old=len(packages['old']), new=len(packages['new'])), packages=package_rows,
            compared_files=[len(old), len(new)], changed_paths=len(changed), rules=dict(sorted(counts.items())),
            units=units, generated=generated, unexplained=unexplained[:500], unexplained_count=len(unexplained),
            problems=problems, runtime_config_changes=runtime, labels=labels,
            base_ancestry_verified=f'release {before_release} base ancestry differs' not in problems and f'release {release} base ancestry differs' not in problems,
            runtime_config_equal=not runtime,
            metadata_note='File mtimes/inodes are storage metadata, excluded as in release 13; full classified inventory in classified-files.json.gz.',
            **extra)
        (evidence / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        assert not problems, 'STOP: ' + '; '.join(problems)
        assert not unexplained, f'STOP: {len(unexplained)} unexplained image differences, first: {unexplained[:20]}'
        print(f'IMAGE_DIFF_PASSED: {len(changed)} changed paths, all explained: ' + json.dumps(counts, sort_keys=True))
    finally:
        for container in reversed(mounts):
            command('podman', 'unmount', container)
            command('podman', 'rm', container)
