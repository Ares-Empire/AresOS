#!/usr/bin/bash
set -euo pipefail

# Package 23: build the AresOS mod jar from the repository at one exact commit.
# The Containerfile's `mod` stage runs this in the digest-pinned JDK image for
# every image build; os/ci/build-mod.sh runs it to set or renew the pin. The
# image's configure step accepts the jar only with its pinned SHA-256.
if [[ $1 == mod ]]; then
    revision=${2-} out=${3-}
    if [[ ! $revision =~ ^[0-9a-f]{40}$ ]]; then
        echo "The AresOS mod is built from an exact commit: pass --build-arg ARESOS_SOURCE_REVISION=<full commit> (got '$revision')" >&2
        exit 1
    fi
    [[ $out == /* ]]
    work=$(mktemp -d)
    curl -fsSL --proto '=https' --tlsv1.2 --retry 3 -o "$work/source.tar.gz" \
        "https://codeload.github.com/Ares-Empire/AresOS/tar.gz/$revision"
    mkdir "$work/source"
    tar -xzf "$work/source.tar.gz" -C "$work/source" --strip-components=1 --wildcards '*/mod/*'
    cd "$work/source/mod"
    version=$(sed -n 's/^version=//p' gradle.properties)
    [[ $version =~ ^[0-9A-Za-z.+-]+$ ]]
    GRADLE_USER_HOME="$work/gradle" ./gradlew --no-daemon --console=plain jar
    mkdir -p "$out"
    cp "build/libs/aresos-$version.jar" "$out/aresos.jar"
    echo "MOD_JAR_BUILT $(sha256sum "$out/aresos.jar" | cut -d' ' -f1) from $revision"
    rm -rf "$work"
    exit 0
fi

if [[ $1 == packages ]]; then
    mkdir -p /usr/share/aresos/manifest /tmp/ares-rpms /tmp/ares-chrome
    rpm -qa --qf '%{NEVRA}\n' | sort > /tmp/base-packages.txt
    mapfile -t packages < <(python3 - <<'PY'
import json
lock = json.load(open('/tmp/aresos/packages.lock.json'))
assert lock['packages'], 'An exact package lock is required'
print('\n'.join(p['nevra'] for p in lock['packages']))
PY
    )
    dnf5 --disable-repo='*' --enable-repo=fedora --enable-repo=updates \
        --setopt=install_weak_deps=False --setopt=skip_if_unavailable=False --setopt=gpgcheck=True \
        download --resolve --destdir=/tmp/ares-rpms "${packages[@]}"
    python3 - <<'PY'
import hashlib, json, pathlib, subprocess
packages = []
for path in sorted(pathlib.Path('/tmp/ares-rpms').glob('*.rpm')):
    nevra = subprocess.check_output(['rpm', '-qp', '--qf', '%{NEVRA}', str(path)], text=True)
    packages.append({'nevra': nevra, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
actual = {'packages': packages}
lock = json.loads(pathlib.Path('/tmp/aresos/packages.lock.json').read_text())
if actual != lock:
    print(json.dumps(actual, indent=2))
    raise SystemExit('Package resolution differs from reviewed packages.lock.json')
pathlib.Path('/usr/share/aresos/manifest/packages.lock.json').write_text(json.dumps(actual, indent=2) + '\n')
PY
    # Google Chrome is not in Fedora's repositories. Take Google's exact RPM
    # from its pin and accept it only when the bytes, the name and Google's
    # pinned signing key all match. No repository is added for it.
    chrome_url=$(python3 -c 'import json; print(json.load(open("/tmp/aresos/google-chrome.lock.json"))["url"])')
    curl -fsSL --proto '=https' --tlsv1.2 --retry 3 -o /tmp/ares-chrome/google-chrome.rpm "$chrome_url"
    python3 - <<'PY'
import hashlib, json, pathlib, subprocess
pin = json.loads(pathlib.Path('/tmp/aresos/google-chrome.lock.json').read_text())
key = pathlib.Path('/tmp/aresos') / pin['signing_key']['file']
assert hashlib.sha256(key.read_bytes()).hexdigest() == pin['signing_key']['sha256'], 'Google signing key differs from its pin'
package = pathlib.Path('/tmp/ares-chrome/google-chrome.rpm')
assert hashlib.sha256(package.read_bytes()).hexdigest() == pin['sha256'], 'Google Chrome RPM differs from its pin'
nevra = subprocess.check_output(['rpm', '-qp', '--nosignature', '--qf', '%{NEVRA}', str(package)], text=True)
assert nevra == pin['nevra'], f'Google Chrome RPM is {nevra}, pinned {pin["nevra"]}'
PY
    rpmkeys --import /tmp/aresos/keys/google-linux-signing-key.pub
    chrome_key=$(python3 -c 'import json; print(json.load(open("/tmp/aresos/google-chrome.lock.json"))["signing_key"]["fingerprint"])')
    rpmkeys --checksig --verbose /tmp/ares-chrome/google-chrome.rpm | tee /tmp/ares-chrome/checksig.txt
    grep -Eq "^[[:space:]]+Header OpenPGP .*signature, key fingerprint: $chrome_key: OK$" /tmp/ares-chrome/checksig.txt
    if grep -Eqv '^/tmp/ares-chrome/google-chrome\.rpm:$|: OK$' /tmp/ares-chrome/checksig.txt; then
        echo 'Google Chrome signature check reported a line that is not OK' >&2
        exit 1
    fi
    # Its install script adds Google's repository unless this file says not to.
    printf '# AresOS: Chrome updates arrive with AresOS releases, not from a repository.\nrepo_add_once="false"\nrepo_reenable_on_distupgrade="false"\n' \
        > /etc/default/google-chrome
    mkdir -p /var/opt
    dnf5 --disable-repo='*' --setopt=install_weak_deps=False --setopt=localpkg_gpgcheck=True install -y \
        /tmp/ares-rpms/*.rpm /tmp/ares-chrome/google-chrome.rpm
    # The key was needed only to verify this RPM; the image trusts no new key.
    rpmkeys --delete "$chrome_key"
    # /opt is /var/opt on bootc and is not replaced by an image update. Keep
    # Chrome in the image under /usr/lib/opt, as rpm-ostree does, with direct
    # commands; tmpfiles links /opt/google there at boot for anything else.
    test ! -e /usr/lib/opt/google
    mkdir -p /usr/lib/opt
    mv /var/opt/google /usr/lib/opt/google
    rmdir /var/opt
    update-alternatives --remove-all google-chrome
    ln -sfn /usr/lib/opt/google/chrome/google-chrome /usr/bin/google-chrome-stable
    ln -sfn google-chrome-stable /usr/bin/google-chrome
    # No side updater: Google's daily job re-adds its repository and key.
    rm -f /etc/cron.daily/google-chrome
    rmdir --ignore-fail-on-non-empty /etc/cron.daily
    if compgen -G '/etc/yum.repos.d/*google*' > /dev/null; then
        echo 'Google Chrome added a package repository' >&2
        exit 1
    fi
    cp /tmp/aresos/google-chrome.lock.json /usr/share/aresos/manifest/google-chrome.lock.json
    # Package 23: Prism Launcher's official Linux bundle and the desktop's
    # Fabric inputs, each from its pinned URL and accepted only with its pinned
    # SHA-256 and size (os/minecraft/desktop.lock.json). The AresOS mod jar is
    # built from this repository by os/ci/build-mod.sh, which already required
    # its pin; it is checked again here. Minecraft itself is never in the image:
    # Prism downloads it after the owner signs in.
    python3 - <<'PY'
import hashlib, json, os, pathlib, shutil, subprocess, tarfile
lock = json.loads(pathlib.Path('/tmp/aresos/minecraft/desktop.lock.json').read_text())
share = pathlib.Path('/usr/share/aresos/minecraft')
downloads = pathlib.Path('/tmp/ares-minecraft')
downloads.mkdir()

def fetch(entry, target):
    subprocess.run(['curl', '-fsSL', '--proto', '=https', '--tlsv1.2', '--retry', '3', '-o', str(target), entry['url']],
                   check=True)
    check(entry, target)

def check(entry, target):
    data = target.read_bytes()
    assert hashlib.sha256(data).hexdigest() == entry['sha256'], f'{target.name} differs from its pin'
    if 'size' in entry:
        assert len(data) == entry['size'], f'{target.name} has the wrong size'

prism = downloads / 'prism.tar.gz'
fetch(lock['prism'], prism)
root = pathlib.Path('/usr/lib/prismlauncher')
assert not root.exists()
with tarfile.open(prism) as archive:
    archive.extractall(root, filter='data')
# The bundle's own updater and portable mode stay out: updates come with AresOS
# releases, and Prism keeps his data in ~/.local/share/PrismLauncher.
for name in ('portable.txt', 'bin/prismlauncher_updater', 'shared/bin/prismlauncher_updater'):
    (root / name).unlink()
assert not list(root.rglob('*updater*')), list(root.rglob('*updater*'))
assert not (root / 'UserData').exists()
os.symlink('/usr/lib/prismlauncher/bin/prismlauncher', '/usr/bin/prismlauncher')
for folder in ('libraries', 'mods'):
    (share / folder).mkdir(parents=True)
for library in lock['fabric_loader']['libraries']:
    _, artifact, version = library['name'].split(':')
    fetch(library, share / 'libraries' / f'{artifact}-{version}.jar')
for mod in lock['mods']:
    if 'url' in mod:
        fetch(mod, share / 'mods' / mod['file'])
# Prism's own metadata for Minecraft and LWJGL, as local components (versions, natives and hashes fixed).
(share / 'patches').mkdir()
for component in lock['components']:
    fetch(component, share / 'patches' / component['file'])
shutil.copyfile('/tmp/aresos/minecraft/desktop.lock.json', share / 'desktop.lock.json')
manifest = []
for path in sorted(p for p in root.rglob('*') if p.is_file() and not p.is_symlink()):
    manifest.append(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path}')
pathlib.Path('/usr/share/aresos/manifest/prism-files.sha256').write_text('\n'.join(manifest) + '\n')
shutil.rmtree(downloads)
print(f'Prism {lock["prism"]["version"]}, Fabric Loader {lock["fabric_loader"]["version"]} and '
      f'{len(lock["mods"])} mods installed from their pins')
PY
    rpm -qa --qf '%{NEVRA}\n' | sort > /usr/share/aresos/manifest/packages.txt
    grep -E '^(kernel|kmod-nvidia|akmod-nvidia|nvidia|libnvidia|xorg-x11-drv-nvidia)' /tmp/base-packages.txt > /tmp/drivers-before
    grep -E '^(kernel|kmod-nvidia|akmod-nvidia|nvidia|libnvidia|xorg-x11-drv-nvidia)' /usr/share/aresos/manifest/packages.txt > /tmp/drivers-after
    diff -u /tmp/drivers-before /tmp/drivers-after
    cp /tmp/drivers-after /usr/share/aresos/manifest/kernel-nvidia.txt
    dnf5 clean all
    rm -rf /tmp/ares-rpms /tmp/ares-chrome
    exit 0
fi

# Package 23: the mod jar the `mod` stage built from this commit, accepted only
# with its pinned SHA-256 (a build without it, or with other bytes, stops here).
python3 - <<'PY'
import hashlib, json, pathlib, shutil
lock = json.loads(pathlib.Path('/tmp/aresos/minecraft/desktop.lock.json').read_text())
mod = next(mod for mod in lock['mods'] if mod['file'] == 'aresos.jar' and 'url' not in mod)
jar = pathlib.Path('/tmp/aresos/minecraft/aresos.jar')
assert jar.is_file(), 'The AresOS mod jar is missing: the Containerfile mod stage builds it'
digest = hashlib.sha256(jar.read_bytes()).hexdigest()
assert digest == mod['sha256'], f'The AresOS mod jar built from this commit is {digest}; desktop.lock.json pins {mod["sha256"]}'
target = pathlib.Path('/usr/share/aresos/minecraft/mods/aresos.jar')
assert not target.exists()
shutil.copyfile(jar, target)
target.chmod(0o644)
print(f'MOD_JAR_PINNED {digest}')
PY

# Use the same declaration at build and boot: local /etc/passwd changes from
# the installer otherwise hide new accounts in the image's /usr/etc/passwd.
systemd-sysusers /usr/lib/sysusers.d/aresos.conf
passwd --lock ares
passwd --lock root
chmod 0755 /usr/bin/aresos-session /usr/bin/aresos-terminal /usr/bin/brew /usr/libexec/aresos-audit \
    /usr/libexec/aresos-keyboard /usr/libexec/aresos-shell /usr/libexec/aresos-subids \
    /usr/libexec/aresos-desktop /usr/libexec/aresos-desktop-java
# The owner's command for the desktop (retry, status, reset-instance, forget-hub).
ln -sfn ../libexec/aresos-desktop /usr/bin/aresos-desktop
chmod 0440 /etc/sudoers.d/aresos-everyday
/usr/libexec/aresos-subids
systemctl enable aresos-subids.service

while read -r unit; do
    systemctl disable "$unit" 2>/dev/null || true
    ln -sfn /dev/null "/etc/systemd/system/$unit"
done < /usr/share/aresos/policy/masked-system-units.txt
mkdir -p /etc/systemd/user
while read -r unit; do
    systemctl --global disable "$unit" 2>/dev/null || true
    ln -sfn /dev/null "/etc/systemd/user/$unit"
done < /usr/share/aresos/policy/masked-user-units.txt

# Keep desktop packages to avoid disturbing the upstream graphics dependency set.
# Remove their launch definitions and mask their session/power services instead.
for dir in /usr/lib/systemd/user /usr/lib/systemd/system; do
    for file in "$dir"/plasma-* "$dir"/gnome-session* "$dir"/org.gnome.SettingsDaemon.Power*; do
        [[ -f $file ]] || continue
        scope=system
        [[ $dir == */user ]] && scope=user
        ln -sfn /dev/null "/etc/systemd/$scope/$(basename "$file")"
    done
done
rm -f /etc/systemd/system/display-manager.service
systemctl enable greetd.service getty@tty3.service
systemctl set-default graphical.target
rm -f /usr/share/wayland-sessions/*.desktop /usr/share/xsessions/*.desktop

mkdir -p /etc/xdg/autostart
for dir in /etc/xdg/autostart /usr/etc/xdg/autostart /usr/share/autostart /etc/skel/.config/autostart; do
    [[ -d $dir ]] || continue
    for file in "$dir"/*.desktop; do
        [[ -f $file ]] || continue
        printf '[Desktop Entry]\nType=Application\nHidden=true\n' > "/etc/xdg/autostart/$(basename "$file")"
    done
done
rm -rf /etc/skel/Desktop /etc/skel/.config/autostart

# Ares is in wheel behind its own password (owner, 2026-11-09). Remove the
# upstream NOPASSWD update grants as before, then refuse any passwordless rule
# that is left: admin rights need his password.
python3 - <<'PY'
import pathlib, re
paths = [pathlib.Path('/etc/sudoers'), *sorted(pathlib.Path('/etc/sudoers.d').glob('*'))]
for path in paths:
    if path.is_file():
        lines = path.read_text().splitlines(keepends=True)
        if any('NOPASSWD' in line and re.search(r'uupd|update|upgrade|bootc|ostree|topgrade|flatpak|brew', line, re.I) for line in lines):
            if path.name == 'sudoers':
                raise SystemExit('Unexpected updater grant in main sudoers; review required')
            path.unlink()
left = [f'{path}: {line.strip()}' for path in paths if path.is_file()
        for line in path.read_text().splitlines()
        if not line.lstrip().startswith('#') and re.search(r'NOPASSWD|!\s*authenticate', line)]
if left:
    raise SystemExit('Passwordless sudo rule needs review: ' + '; '.join(left))
PY
visudo --check
# No cached admin authorization (review 2): polkit lets the same process reuse
# an auth_*_keep authorization for a while, even with other parameters. Make
# every installed default uncached, for every account, and refuse leftovers.
python3 - <<'PY'
import pathlib, re
actions = pathlib.Path('/usr/share/polkit-1/actions')
cached = re.compile(r'(<allow_(?:any|inactive|active)>\s*)auth_(admin|self)_keep(\s*</allow_)')
changed = 0
for path in sorted(actions.glob('*.policy')):
    text = path.read_text()
    new, count = cached.subn(r'\1auth_\2\3', text)
    if count:
        path.write_text(new)
        changed += count
left = [path.name for path in actions.glob('*.policy') if re.search(r'_keep\s*</allow_', path.read_text())]
if left or not changed:
    raise SystemExit(f'polkit defaults still cached in {left} (changed {changed})')
print(f'polkit: {changed} cached defaults made uncached')
# Flatpak's passwordless app-update implies runtime-install, so an app update
# could install any system-wide runtime without the password (review 3). Keep
# the implied runtime-update: updates of installed apps stay passwordless and
# a new runtime asks for the password like any other system-wide install.
flatpak = actions / 'org.freedesktop.Flatpak.policy'
text = flatpak.read_text()
update = re.search(r'<action id="org\.freedesktop\.Flatpak\.app-update">.*?</action>', text, re.S)
imply = re.compile(r'(<annotate key="org\.freedesktop\.policykit\.imply">)([^<]*)(</annotate>)')
found = imply.findall(update.group(0)) if update else []
# Exactly the reviewed targets (Flatpak 1.18.4), or the build stops for review.
reviewed = ['org.freedesktop.Flatpak.runtime-install', 'org.freedesktop.Flatpak.runtime-update']
if len(found) != 1 or found[0][1].split() != reviewed:
    raise SystemExit(f'Flatpak app-update implication changed upstream; review required: {found}')
kept = 'org.freedesktop.Flatpak.runtime-update'
edited = text.replace(update.group(0), imply.sub(lambda m: m.group(1) + kept + m.group(3), update.group(0)))
after = re.search(r'<action id="org\.freedesktop\.Flatpak\.app-update">.*?</action>', edited, re.S)
if ([targets for _, targets, _ in imply.findall(after.group(0))] != [kept]
        or edited.replace(after.group(0), '') != text.replace(update.group(0), '')):
    raise SystemExit('Flatpak app-update implication edit did not leave exactly runtime-update')
flatpak.write_text(edited)
print(f'polkit: Flatpak app-update now implies only: {kept}')
PY
# The OS image, firmware and app store stay out of the daily account's reach.
# Flatpak and Homebrew are his apps now and stay executable.
for command in uupd ujust topgrade bazzite-updater bazzite-portal bazaar plasma-discover gnome-software; do
    path=$(command -v "$command" || true)
    [[ -z $path ]] || chmod 0700 "$(readlink -f "$path")"
done
# aresos.sh sets the daily account's PATH, Homebrew's included. Upstream's
# interactive setup would append Homebrew a second time.
sed -i '1a if [ "$(id -u)" = 1001 ]; then return 0; fi' /etc/profile.d/brew.sh
for entry in /usr/share/applications/*.desktop; do
    if grep -Eiq '(^Exec=.*(uupd|ujust|topgrade|bazzite-(updater|portal)|bazaar|plasma-discover|gnome-software)|update|upgrade|rebase)' "$entry"; then
        rm -f "$entry"
    fi
done
python3 /usr/libexec/aresos-audit --output /usr/share/aresos/manifest/updaters.json
rm -rf /tmp/aresos /tmp/base-packages.txt /tmp/drivers-before /tmp/drivers-after
