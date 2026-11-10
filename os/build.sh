#!/usr/bin/bash
set -euo pipefail

if [[ $1 == packages ]]; then
    mkdir -p /usr/share/aresos/manifest /tmp/ares-rpms
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
    raise SystemExit('Package resolution differs from reviewed packages.lock.json')
pathlib.Path('/usr/share/aresos/manifest/packages.lock.json').write_text(json.dumps(actual, indent=2) + '\n')
PY
    dnf5 --disable-repo='*' --setopt=install_weak_deps=False --setopt=localpkg_gpgcheck=True install -y /tmp/ares-rpms/*.rpm
    rpm -qa --qf '%{NEVRA}\n' | sort > /usr/share/aresos/manifest/packages.txt
    grep -E '^(kernel|kmod-nvidia|akmod-nvidia|nvidia|libnvidia|xorg-x11-drv-nvidia)' /tmp/base-packages.txt > /tmp/drivers-before
    grep -E '^(kernel|kmod-nvidia|akmod-nvidia|nvidia|libnvidia|xorg-x11-drv-nvidia)' /usr/share/aresos/manifest/packages.txt > /tmp/drivers-after
    diff -u /tmp/drivers-before /tmp/drivers-after
    cp /tmp/drivers-after /usr/share/aresos/manifest/kernel-nvidia.txt
    dnf5 clean all
    rm -rf /tmp/ares-rpms
    exit 0
fi

# Use the same declaration at build and boot: local /etc/passwd changes from
# the installer otherwise hide new accounts in the image's /usr/etc/passwd.
systemd-sysusers /usr/lib/sysusers.d/aresos.conf
passwd --lock ares
passwd --lock root
chmod 0755 /usr/bin/aresos-session /usr/bin/aresos-terminal /usr/libexec/aresos-audit /usr/libexec/aresos-keyboard /usr/libexec/aresos-shell

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

# Ares never belongs to wheel. Also remove upstream NOPASSWD update grants.
python3 - <<'PY'
import pathlib, re
for path in [pathlib.Path('/etc/sudoers'), *pathlib.Path('/etc/sudoers.d').glob('*')]:
    if path.is_file():
        lines = path.read_text().splitlines(keepends=True)
        if any('NOPASSWD' in line and re.search(r'uupd|update|upgrade|bootc|ostree|topgrade|flatpak|brew', line, re.I) for line in lines):
            if path.name == 'sudoers':
                raise SystemExit('Unexpected updater grant in main sudoers; review required')
            path.unlink()
PY
for command in uupd ujust topgrade bazzite-updater bazzite-portal bazaar plasma-discover gnome-software flatpak brew; do
    path=$(command -v "$command" || true)
    [[ -z $path ]] || chmod 0700 "$(readlink -f "$path")"
done
# Upstream's interactive setup appends brew to PATH even when shellenv fails.
# Keep it for the recovery owner, but never evaluate it as the daily account.
for script in /etc/profile.d/brew.sh /etc/profile.d/brew-bash-completion.sh; do
    sed -i '1a if [ "$(id -u)" = 1001 ]; then return 0; fi' "$script"
done
for entry in /usr/share/applications/*.desktop; do
    if grep -Eiq '(^Exec=.*(uupd|ujust|topgrade|bazzite-(updater|portal)|bazaar|plasma-discover|gnome-software)|update|upgrade|rebase)' "$entry"; then
        rm -f "$entry"
    fi
done
python3 /usr/libexec/aresos-audit --output /usr/share/aresos/manifest/updaters.json
rm -rf /tmp/aresos /tmp/base-packages.txt /tmp/drivers-before /tmp/drivers-after
