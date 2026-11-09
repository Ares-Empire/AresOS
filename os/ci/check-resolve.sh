#!/usr/bin/bash
# Runs inside the pinned base image (never a release layer). It inventories the
# inherited state package 21 changes and resolves exact RPM inputs for review:
# the Fedora package lock and the Google Chrome pin. It writes only /evidence.
set -uo pipefail
out=/evidence/resolve
mkdir -p "$out"
section() { printf '\n===== %s\n' "$*"; }
show() { for file in "$@"; do printf -- '--- %s\n' "$file"; cat "$file" 2>&1; done; }

{
    section packages
    rpm -q util-linux util-linux-core util-linux-script qrencode qrencode-libs brightnessctl polkit polkit-kde \
        wireplumber flatpak foot labwc xdg-utils cronie sudo shadow-utils podman distrobox liberation-fonts \
        liberation-fonts-common wget2-wget gnupg2 curl rpm dnf5 bazaar
    section filesystem
    ls -ld /opt /var/opt /home /usr/local 2>&1
    ls -la /opt/ /var/opt/ 2>&1
    section commands
    for command in brew flatpak wpctl brightnessctl script qrencode pkttyagent google-chrome crond xdg-open xdg-mime \
        getsubids newuidmap gpg curl node visudo setfacl usermod; do
        printf '%s: %s\n' "$command" "$(command -v "$command" || echo missing)"
    done
    ls -la /usr/bin/brew /usr/local/bin/brew 2>&1
    section polkit-agents
    rpm -ql polkit-kde 2>&1
    find / -xdev -name '*polkit*agent*' -not -path '/proc/*' 2>/dev/null
    section sudoers
    grep -v '^#' /etc/sudoers | grep -v '^$'
    show /etc/sudoers.d/* 2>/dev/null
    section polkit-rules
    show /etc/polkit-1/rules.d/* /usr/share/polkit-1/rules.d/*
    section polkit-wheel-mentions
    grep -rln wheel /etc/polkit-1 /usr/share/polkit-1 2>&1
    section polkit-actions-flatpak-systemd-rpmostree-fwupd-bazzite
    for file in /usr/share/polkit-1/actions/*.policy; do
        case $file in
            *Flatpak*|*systemd1*|*rpmostree*|*fwupd*|*bazzite*|*ublue*|*policykit*)
                printf -- '--- %s\n' "$file"
                grep -E 'action id=|<allow_(any|inactive|active)>' "$file" ;;
        esac
    done
    ls /usr/share/polkit-1/actions/
    section profile.d
    ls -la /etc/profile.d/
    show /etc/profile.d/brew.sh /etc/profile.d/brew-bash-completion.sh /etc/profile.d/flatpak.sh
    section bashrc
    show /etc/bashrc /etc/skel/.bashrc
    section user-environment-generators
    ls -la /usr/lib/systemd/user-environment-generators/
    show /usr/lib/systemd/user-environment-generators/60-flatpak
    section foot
    ls -la /etc/xdg/foot/
    grep -vE '^\s*(#|$)' /etc/xdg/foot/foot.ini
    rpm -qf /etc/xdg/foot/foot.ini
    section mimeapps
    find /etc/xdg /usr/share/applications /usr/local/share/applications -maxdepth 1 -name '*mimeapps.list' \
        -exec sh -c 'printf -- "--- %s\n" "$1"; grep -iE "http|html|Default|Added" "$1"' _ {} \;
    section xdg-utils
    grep -n 'BROWSER=\|mimeapps\|XDG_CURRENT_DESKTOP' /usr/bin/xdg-open | head -40
    grep -n 'mimeapps\|XDG_CURRENT_DESKTOP\|desktop_name' /usr/bin/xdg-mime | head -40
    section subid
    show /etc/subuid /etc/subgid
    grep -E '^(SUB_|UID_|GID_)' /etc/login.defs
    section accounts
    grep -E '^(wheel|ares)' /etc/group
    section cron
    ls -la /etc/cron.d /etc/cron.daily /etc/cron.hourly 2>&1
    systemctl is-enabled crond.service 2>&1
    section bazaar
    rpm -qR bazaar 2>&1
    rpm -ql bazaar 2>&1 | grep -vE '/locale/|/icons/' | head -60
    for file in $(rpm -ql bazaar | grep -E '/s?bin/'); do
        printf -- '--- %s\n' "$file"; strings "$file" 2>/dev/null | grep -iE 'rpm-ostree|bootc|ostree|uupd|pkexec' | head -20
    done
    section audio
    rpm -q wireplumber pipewire-utils
    section labwc-defaults
    ls -la /etc/xdg/labwc /usr/share/labwc 2>&1
} > "$out/inventory.txt" 2>&1

# Google Chrome: newest stable RPM in Google's own repository metadata.
chrome=/tmp/chrome
mkdir -p "$chrome"
repo=https://dl.google.com/linux/chrome/rpm/stable/x86_64
{
    section chrome-repo
    curl -fsSL --proto '=https' --tlsv1.2 -o "$chrome/repomd.xml" "$repo/repodata/repomd.xml"
    python3 - "$chrome" "$repo" <<'PY'
import gzip, json, pathlib, re, sys, urllib.request
import xml.etree.ElementTree as ET
folder, repo = pathlib.Path(sys.argv[1]), sys.argv[2]
ns = {'repo': 'http://linux.duke.edu/metadata/repo', 'common': 'http://linux.duke.edu/metadata/common',
      'rpm': 'http://linux.duke.edu/metadata/rpm'}
root = ET.parse(folder / 'repomd.xml').getroot()
primary = next(d for d in root.findall('repo:data', ns) if d.get('type') == 'primary')
location = primary.find('repo:location', ns).get('href')
raw = urllib.request.urlopen(repo + '/' + location, timeout=120).read()
tree = ET.fromstring(gzip.decompress(raw))
rows = []
for package in tree.findall('common:package', ns):
    name = package.find('common:name', ns).text
    version = package.find('common:version', ns)
    rows.append(dict(name=name, epoch=version.get('epoch'), ver=version.get('ver'), rel=version.get('rel'),
                     arch=package.find('common:arch', ns).text,
                     sha256=package.find('common:checksum', ns).text,
                     checksum_type=package.find('common:checksum', ns).get('type'),
                     location=package.find('common:location', ns).get('href'),
                     size=package.find('common:size', ns).get('package')))
print(json.dumps(rows, indent=1))
stable = [r for r in rows if r['name'] == 'google-chrome-stable']
assert stable, 'No google-chrome-stable in repository metadata'
newest = max(stable, key=lambda r: [int(x) for x in re.findall(r'\d+', r['ver'])])
(folder / 'newest.json').write_text(json.dumps(newest))
PY
    newest=$(python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); print(r["location"])' "$chrome/newest.json")
    expected=$(python3 -c 'import json,sys; r=json.load(open(sys.argv[1])); print(r["sha256"])' "$chrome/newest.json")
    curl -fsSL --proto '=https' --tlsv1.2 -o "$chrome/google-chrome.rpm" "$repo/$newest"
    printf 'url=%s/%s\nmetadata_sha256=%s\n' "$repo" "$newest" "$expected"
    sha256sum "$chrome/google-chrome.rpm"
    rpm -qp --qf 'nevra=%{NEVRA}\n' "$chrome/google-chrome.rpm"
    section chrome-key
    curl -fsSL --proto '=https' --tlsv1.2 -o "$out/linux_signing_key.pub" https://dl.google.com/linux/linux_signing_key.pub
    sha256sum "$out/linux_signing_key.pub"
    gpg --batch --show-keys --with-colons --with-fingerprint "$out/linux_signing_key.pub"
    section chrome-signature-before-import
    rpmkeys --checksig --verbose "$chrome/google-chrome.rpm"
    rpm -qp --qf 'RSAHEADER=%{RSAHEADER:pgpsig}\nSIGPGP=%{SIGPGP:pgpsig}\n' "$chrome/google-chrome.rpm"
    rpm -qp --qf '[OPENPGP=%{OPENPGP}\n]' "$chrome/google-chrome.rpm" 2>&1 | head -5
    section chrome-signature-after-import
    rpmkeys --import "$out/linux_signing_key.pub"
    rpm -q gpg-pubkey --qf '%{NAME}-%{VERSION}-%{RELEASE} %{SUMMARY}\n'
    rpmkeys --checksig --verbose "$chrome/google-chrome.rpm"
    echo "checksig exit=$?"
    section chrome-requires
    rpm -qpR "$chrome/google-chrome.rpm"
    section chrome-recommends
    rpm -qp --recommends --suggests --supplements --enhances "$chrome/google-chrome.rpm"
    section chrome-scripts
    rpm -qp --scripts --triggers "$chrome/google-chrome.rpm"
    section chrome-files
    rpm -qpl "$chrome/google-chrome.rpm" | grep -v '^/opt/google/chrome/locales/'
    rpm -qp --dump "$chrome/google-chrome.rpm" | awk '$5 ~ /^04/ || $5 ~ /^02/ {print}'
} > "$out/chrome.txt" 2>&1

# Fedora inputs: which Chrome requirements the base does not already satisfy.
{
    section unsatisfied-chrome-requirements
    rpm -qpR "$chrome/google-chrome.rpm" | sed 's/[[:space:]]*$//' | while read -r requirement; do
        case $requirement in rpmlib\(*) continue ;; esac
        rpm -q --whatprovides "$requirement" >/dev/null 2>&1 || printf '%s\n' "$requirement"
    done | tee "$chrome/unsatisfied.txt"
    section providers
    while read -r requirement; do
        printf -- '--- %s\n' "$requirement"
        dnf5 --disable-repo='*' --enable-repo=fedora --enable-repo=updates repoquery --latest-limit=1 \
            --whatprovides "$requirement" --qf '%{name}\n'
    done < "$chrome/unsatisfied.txt" | tee "$chrome/providers.txt"
    section transaction-preview
    dnf5 --disable-repo='*' --enable-repo=fedora --enable-repo=updates --setopt=install_weak_deps=False \
        install --assumeno util-linux-script qrencode brightnessctl "$chrome/google-chrome.rpm"
    section available
    dnf5 --disable-repo='*' --enable-repo=fedora --enable-repo=updates repoquery --showduplicates \
        --qf '%{full_nevra} %{repoid}\n' util-linux-script util-linux-core util-linux qrencode brightnessctl \
        liberation-fonts foot labwc greetd grim fcft libsfdo utf8proc wlroots0.19 xdg-desktop-portal-wlr \
        greetd-selinux
    section existing-lock-availability
    python3 -c 'import json; [print(p["nevra"]) for p in json.load(open("/tmp/aresos/packages.lock.json"))["packages"]]' |
        while read -r nevra; do
            if dnf5 --disable-repo='*' --enable-repo=fedora --enable-repo=updates repoquery -q "$nevra" | grep -q .; then
                printf 'available %s\n' "$nevra"
            else
                printf 'MISSING %s\n' "$nevra"
            fi
        done
} > "$out/fedora.txt" 2>&1

# Candidate lock: the existing exact inputs plus the new tools and Chrome's
# missing Fedora providers, resolved exactly as build.sh does.
names=()
while read -r nevra; do names+=("$nevra"); done < <(python3 -c 'import json; [print(p["nevra"]) for p in json.load(open("/tmp/aresos/packages.lock.json"))["packages"]]')
util=$(rpm -q --qf '%{VERSION}-%{RELEASE}' util-linux-core)
names+=("util-linux-script-$util.x86_64" qrencode brightnessctl)
while read -r provider; do
    case $provider in ''|---*) continue ;; esac
    names+=("$provider")
done < "$chrome/providers.txt"
{
    printf 'Requested: %s\n' "${names[*]}"
    rm -rf /tmp/ares-rpms
    mkdir -p /tmp/ares-rpms
    dnf5 --disable-repo='*' --enable-repo=fedora --enable-repo=updates \
        --setopt=install_weak_deps=False --setopt=skip_if_unavailable=False --setopt=gpgcheck=True \
        download --resolve --destdir=/tmp/ares-rpms "${names[@]}"
    echo "download exit=$?"
    python3 - <<'PY'
import hashlib, json, pathlib, subprocess
packages = []
for path in sorted(pathlib.Path('/tmp/ares-rpms').glob('*.rpm')):
    nevra = subprocess.check_output(['rpm', '-qp', '--qf', '%{NEVRA}', str(path)], text=True)
    name = subprocess.check_output(['rpm', '-qp', '--qf', '%{NAME}', str(path)], text=True)
    installed = subprocess.run(['rpm', '-q', name], capture_output=True, text=True)
    packages.append({'nevra': nevra, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    print(('UPGRADES-BASE ' + installed.stdout.strip()) if installed.returncode == 0 else 'new', nevra)
pathlib.Path('/evidence/resolve/candidate-packages.lock.json').write_text(json.dumps({'packages': packages}, indent=2) + '\n')
PY
    section install-preview
    dnf5 --disable-repo='*' --setopt=install_weak_deps=False install --assumeno /tmp/ares-rpms/*.rpm "$chrome/google-chrome.rpm"
} > "$out/candidate.txt" 2>&1
echo 'Resolution finished; see evidence/resolve/'
