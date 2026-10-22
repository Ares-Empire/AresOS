#!/usr/bin/bash
set -euxo pipefail
test -d /sys/firmware/efi
systemctl is-active --quiet greetd.service
test "$(systemctl get-default)" = graphical.target
pgrep -u ares -x labwc
pgrep -u ares -x foot
test "$(id -u ares)" = 1000
! id -nG ares | grep -qw wheel
# Root can successfully list an empty policy; that exit status is not a grant.
sudo_policy=$(LC_ALL=C sudo -l -U ares 2>&1 || true)
printf '%s\n' "$sudo_policy"
grep -Eq '^User ares is not allowed to run sudo on .+\.$' <<< "$sudo_policy"
for executable in uupd ujust topgrade bazzite-updater bazzite-portal bazaar plasma-discover gnome-software flatpak brew; do
    path=$(command -v "$executable" || true)
    [[ -z $path ]] || runuser -u ares -- test ! -x "$path"
done
for unit in sddm gdm lightdm; do
    ! systemctl is-active --quiet "$unit.service"
done
! pgrep -x 'kwin_wayland|plasmashell|gnome-shell|powerdevil|gsd-power'
while read -r unit; do
    test "$(systemctl is-enabled "$unit" 2>/dev/null || true)" = masked
done < /usr/share/aresos/policy/masked-system-units.txt
while read -r unit; do
    test "$(systemctl --global is-enabled "$unit" 2>/dev/null || true)" = masked
done < /usr/share/aresos/policy/masked-user-units.txt
python3 /usr/libexec/aresos-audit --live --output /run/aresos-updaters.json
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
echo ARESOS_GUEST_CHECKS_PASSED
