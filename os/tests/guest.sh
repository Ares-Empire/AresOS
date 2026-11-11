#!/usr/bin/bash
set -euxo pipefail
test -d /sys/firmware/efi
systemctl is-active --quiet greetd.service
test "$(systemctl get-default)" = graphical.target
pgrep -u ares -x labwc
pgrep -u ares -x foot
test "$(id -u ares)" = 1001
test "$(id -g ares)" = 1001
python3 - <<'PY'
import subprocess
password = subprocess.check_output(['getent', 'shadow', 'ares'], text=True).split(':')[1]
assert password.startswith(('!', '*')), 'Daily account password is not locked'
print('ARESOS_DAILY_ACCOUNT_LOCKED')
PY
# Owner, 2026-11-09: the daily account is an administrator behind its own
# password. The image sets none, so it stays locked and sudo cannot succeed.
if id -nG ares | grep -qw wheel; then
    echo 'Daily account is in wheel'
else
    echo 'Daily account is not in wheel'
    exit 1
fi
# Root can successfully list a policy; that exit status alone is not a grant.
sudo_policy=$(LC_ALL=C sudo -l -U ares 2>&1 || true)
printf '%s\n' "$sudo_policy"
if grep -Eq 'NOPASSWD|!authenticate' <<< "$sudo_policy"; then
    echo 'Daily account has a passwordless sudo rule'
    exit 1
fi
grep -Eq '^User ares may run the following commands on .+:$' <<< "$sudo_policy"
grep -Eq '^[[:space:]]+\(ALL\) ALL$' <<< "$sudo_policy"
grep -Eq 'timestamp_timeout=0' <<< "$sudo_policy"
if runuser -u ares -- sudo -n true; then
    echo 'Daily account ran sudo without a password'
    exit 1
fi
# The OS image, firmware and store stay out of the daily path; apps do not.
for executable in uupd ujust topgrade bazzite-updater bazzite-portal bazaar plasma-discover gnome-software; do
    path=$(command -v "$executable" || true)
    [[ -z $path ]] || runuser -u ares -- test ! -x "$path"
done
runuser -u ares -- test -x /usr/bin/flatpak
runuser -u ares -- test -x /usr/bin/brew
for unit in sddm gdm lightdm; do
    if systemctl is-active --quiet "$unit.service"; then
        echo "Competing display manager is active: $unit"
        exit 1
    fi
done
if pgrep -x 'kwin_wayland|plasmashell|gnome-shell|powerdevil|gsd-power'; then
    echo 'Competing desktop or power process is running'
    exit 1
fi
# `at update` unmasks exactly ostree's and bootc's staging finalizers: the
# image masks them and bootc cannot stage a release while they are masked
# (os/release/update.sh, package 27). Either may therefore be the image's mask
# or unmasked by that route: the image's /usr/etc mask with this deployment's
# /etc link removed, static and inactive. Every other listed unit stays masked.
finalizer_unmasked_by_update() {
    [[ $1 == ostree-finalize-staged.service || $1 == bootc-finalize-staged.service ]] || return 1
    [[ $(readlink "/usr/etc/systemd/system/$1") == /dev/null ]] || return 1
    if [[ -e /etc/systemd/system/$1 || -L /etc/systemd/system/$1 ]]; then return 1; fi
    [[ $(systemctl is-enabled "$1" 2>/dev/null || true) == static ]] || return 1
    [[ $(systemctl show -P ActiveState "$1") == inactive ]]
}
while read -r unit; do
    finalizer_unmasked_by_update "$unit" || test "$(systemctl is-enabled "$unit" 2>/dev/null || true)" = masked
done < /usr/share/aresos/policy/masked-system-units.txt
while read -r unit; do
    test "$(systemctl --global is-enabled "$unit" 2>/dev/null || true)" = masked
done < /usr/share/aresos/policy/masked-user-units.txt
# The image's own updater audit (aresos-audit --live), which accepts besides
# its allowlist only the finalizers unmasked by the update route, as above.
python3 - <<'PY'
import importlib.machinery, importlib.util, json, os, pathlib
loader = importlib.machinery.SourceFileLoader('aresos_audit', '/usr/libexec/aresos-audit')
audit = importlib.util.module_from_spec(importlib.util.spec_from_loader('aresos_audit', loader))
loader.exec_module(audit)
allowlist = json.loads(pathlib.Path('/usr/share/aresos/policy/updater-allowlist.json').read_text())
units = audit.inventory(live=True)
pathlib.Path('/run/aresos-updaters.json').write_text(json.dumps(units, indent=2) + '\n')


def unmasked_by_update(unit):
    name = unit['name']
    image_mask = '/usr/etc/systemd/system/' + name
    return (unit['scope'] == 'system' and name in ('ostree-finalize-staged.service', 'bootc-finalize-staged.service')
            and unit['state'] == 'static' and unit.get('active_state') in (None, 'inactive')
            and unit.get('sub_state') in (None, 'dead')
            and os.path.islink(image_mask) and os.readlink(image_mask) == '/dev/null'
            and not os.path.lexists('/etc/systemd/system/' + name))


rejected = [unit for unit in audit.offenders(units, allowlist) if not unmasked_by_update(unit)]
if rejected:
    raise SystemExit('Unreviewed unmasked updater(s): ' + json.dumps(rejected))
print(f'Updater audit passed: {len(units)} system/user units inspected')
PY
for target in sleep suspend hibernate hybrid-sleep suspend-then-hibernate; do
    if systemctl start "$target.target"; then
        echo "Unexpectedly started $target.target"
        exit 1
    fi
done
# systemd 259 reports config-disabled sleep as "no"; "na" means unsupported.
test "$(busctl call org.freedesktop.login1 /org/freedesktop/login1 org.freedesktop.login1.Manager CanSuspend)" = 's "no"'
grep -qx AutomaticUpdatePolicy=none /etc/rpm-ostreed.conf
busctl call org.freedesktop.UPower /org/freedesktop/UPower org.freedesktop.UPower GetCriticalAction | grep -F '"Ignore"'
bootc status --json > /run/aresos-backend.json
python3 - <<'PY'
import json
status = json.load(open('/run/aresos-backend.json'))
assert status['status']['booted']['image'], status
print('Deployment backend: bootc (OSTree storage)')
PY
loginctl list-sessions
# polkit as the daily account's real active local session sees it (package 21
# reviews 2 and 3). Above all, the passwordless Flatpak app update no longer
# implies a system-wide runtime install, which needs the password.
session=$(loginctl list-sessions --no-legend | awk '$3 == "ares" && $4 == "seat0" {print $1; exit}')
loginctl show-session "$session" -p Active -p Remote -p Seat -p Class
test "$(loginctl show-session "$session" -p Active --value)" = yes
test "$(loginctl show-session "$session" -p Remote --value)" = no
subject=$(pgrep -u ares -x labwc | head -1)
test "$(cut -d: -f3 /proc/"$subject"/cgroup | grep -o 'session-[0-9]*\.scope')" = "session-$session.scope"
polkit_answer() {
    local status=0
    pkcheck --action-id "$1" --process "$subject" > /dev/null 2>&1 || status=$?
    printf 'polkit %s for ares: %s\n' "$1" "$status" >&2
    echo "$status"
}
# pkcheck: 0 authorized, 1 not authorized, 2 needs authentication.
test "$(polkit_answer org.freedesktop.Flatpak.app-update)" = 0
test "$(polkit_answer org.freedesktop.Flatpak.runtime-update)" = 0
test "$(polkit_answer org.freedesktop.Flatpak.runtime-install)" = 2
test "$(polkit_answer org.freedesktop.Flatpak.app-install)" = 2
test "$(polkit_answer org.freedesktop.systemd1.manage-units)" = 2
test "$(polkit_answer org.freedesktop.login1.power-off)" = 0
test "$(polkit_answer org.freedesktop.login1.set-reboot-to-firmware-setup)" = 1
test "$(polkit_answer com.redhat.tuned.switch_profile)" = 1
echo ARESOS_ACTIVE_SESSION_POLKIT_PASSED
echo ARESOS_GUEST_CHECKS_PASSED
