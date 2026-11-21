#!/usr/bin/bash
# Runs inside a locally built AresOS image as root, without network or
# systemd. Every line that starts with PASS is a checked package 21 decision.
set -euxo pipefail
pass() { set +x; printf 'PASS %s\n' "$*"; set -x; }
expect_failure() {
    # Run a command that must fail; keep its output as evidence.
    local output status=0
    output=$("$@" 2>&1) || status=$?
    printf '%s\n' "$output"
    if [[ $status == 0 ]]; then
        echo "Unexpectedly succeeded: $*"
        exit 1
    fi
    LAST_FAILURE=$output
    LAST_STATUS=$status
}

# --- Package 50: the finished console map, once Plymouth has released the VTs.
console_unit=/usr/lib/systemd/system/aresos-console-keymap.service
test -f "$console_unit"
test ! -L "$console_unit"
test "$(stat -c '%a %u %g' "$console_unit")" = '644 0 0'
test -x /usr/lib/systemd/systemd-vconsole-setup
python3 - "$console_unit" <<'CONSOLE_UNIT'
import configparser, sys
unit = configparser.ConfigParser(interpolation=None)
assert unit.read(sys.argv[1]), 'console keymap unit missing'
expected = {
    'Unit': {
        'Description': 'Finished console keymap after the boot splash',
        'Documentation': 'man:systemd-vconsole-setup.service(8) man:vconsole.conf(5)',
        'DefaultDependencies': 'no',
        'After': 'graphical.target plymouth-quit-wait.service systemd-vconsole-setup.service',
        'Conflicts': 'shutdown.target',
        'Before': 'shutdown.target',
    },
    'Service': {
        'Type': 'oneshot',
        'ExecStart': '/usr/lib/systemd/systemd-vconsole-setup /dev/tty3',
        'RemainAfterExit': 'yes',
        'TimeoutStartSec': '15s',
    },
    'Install': {'WantedBy': 'graphical.target'},
}
assert not unit.defaults(), 'unexpected console keymap defaults'
assert {section: dict(unit[section]) for section in unit.sections()} == {
    section: {key.lower(): value for key, value in entries.items()} for section, entries in expected.items()
}, 'console keymap unit differs from the reviewed boot-only setup'
CONSOLE_UNIT
test "$(systemctl --root=/ is-enabled aresos-console-keymap.service)" = enabled
# Package 25: the shutdown guard. Enabled; ordered after everything that must still be there while the home is
# saved, with every login session ordered before it; its stop is the supervisor's command, inside 85 s. The check
# build's VM proves the order at a real shutdown.
guardian=/usr/lib/systemd/system/aresos-guardian.service
test "$(systemctl --root=/ is-enabled aresos-guardian.service)" = enabled
test -L /etc/systemd/system/graphical.target.wants/aresos-guardian.service
test "$(stat -c '%U:%G %a' "$guardian")" = 'root:root 644'
for line in 'Wants=polkit.service' \
    'After=greetd.service user@1001.service user-runtime-dir@1001.service polkit.service getty@tty3.service' \
    'RequiresMountsFor=/var/home/ares' 'Type=oneshot' 'RemainAfterExit=yes' 'User=ares' \
    'Environment=XDG_RUNTIME_DIR=/run/user/1001' 'ExecStart=/usr/bin/true' \
    'ExecStop=/usr/libexec/aresos-desktop stop --reason shutdown' 'TimeoutStopSec=85' 'WantedBy=graphical.target'; do
    grep -qxF "$line" "$guardian"
done
test "$(grep -c '^Exec' "$guardian")" = 2
grep -qxF 'Before=aresos-guardian.service' /usr/lib/systemd/system/session-.scope.d/50-aresos-guardian.conf
pass 'the shutdown guard is enabled, keeps the desktop and tty3 available during its stop, and calls the supervisor within its 85 s limit'
console_link=/etc/systemd/system/graphical.target.wants/aresos-console-keymap.service
test "$(readlink "$console_link")" = "$console_unit"
test "$(stat -c '%a %u %g' "$console_link")" = '777 0 0'
pass 'console keymap unit: root-owned, bounded boot-only setup on tty3 after Plymouth, enabled without delaying login'

# --- The everyday account: wheel, a password it does not have yet.
systemd-tmpfiles --create /usr/lib/tmpfiles.d/aresos.conf
test -d /var/home/ares
# Package 18c: the image does not make the Control service user or his two
# folders at build; sysusers and tmpfiles make them at boot (checked below).
for database in passwd group; do
    for key in aresos-tools 250; do
        if getent "$database" "$key"; then
            echo "The image already has $database entry $key for the Control service"
            exit 1
        fi
    done
done
test ! -e /var/home/ares/Downloads
test ! -e /var/home/ares/Documents
getent group wheel
id -nG ares | grep -qw wheel
pass 'ares is in wheel'
password=$(getent shadow ares | cut -d: -f2)
case $password in '!'* | '*'*) ;; *) echo 'ares has a password in the image'; exit 1 ;; esac
pass 'the image sets no password for ares (locked)'
policy=$(LC_ALL=C sudo -l -U ares)
printf '%s\n' "$policy"
grep -Eq '^[[:space:]]+\(ALL\) ALL$' <<< "$policy"
grep -q 'timestamp_timeout=0' <<< "$policy"
if grep -Eq 'NOPASSWD|!authenticate' <<< "$policy"; then
    echo 'Passwordless sudo rule for ares'
    exit 1
fi
if grep -rhEv '^[[:space:]]*(#|$)' /etc/sudoers /etc/sudoers.d | grep -E 'NOPASSWD|!authenticate'; then
    echo 'Passwordless sudo rule in the image'
    exit 1
fi
visudo --check
test "$(stat -c '%a %u %g' /etc/sudoers.d/aresos-everyday)" = '440 0 0'
test "$(stat -c '%a %u %g' /etc/sudoers.d)" = '750 0 0'
pass 'sudo for ares: (ALL) ALL with a password, no remembered ticket, no passwordless rule'
expect_failure runuser -u ares -- sudo -n true
grep -q 'password is required' <<< "$LAST_FAILURE"
pass 'sudo as ares fails without a password'

# A successful sudo must leave nothing a later command can reuse, not even a
# child of the same shell that execs sudo -n (review 1). The throwaway
# password exists only in this check container and is kept out of the trace.
set +x
(umask 077 && head -c 18 /dev/urandom | base64 > /run/reuse-password)
printf 'ares:%s\n' "$(cat /run/reuse-password)" | chpasswd
set -x
# Root writes first, then hands it over: sticky /tmp would refuse root's write.
chown ares:ares /run/reuse-password
reuse_probe() {
    # One shell authenticates once; then a child keeps that shell as the
    # parent of sudo -n, as `exec` from a program it started would.
    # The child is not the last command, so bash cannot exec it in place.
    runuser -u ares -- /usr/bin/bash -c '
        sudo -S -p "" true < /run/reuse-password || exit 90
        /usr/bin/bash -c "exec sudo -n true"
        status=$?
        exit "$status"
    '
}
# Control: the earlier per-parent-process ticket does let that child in, so
# this probe can see reuse.
printf 'Defaults:ares timestamp_timeout=5, timestamp_type=ppid\n' > /etc/sudoers.d/zz-reuse-control
chmod 0440 /etc/sudoers.d/zz-reuse-control
visudo --check
reuse_probe
rm /etc/sudoers.d/zz-reuse-control
rm -rf /run/sudo/ts /var/run/sudo/ts
expect_failure reuse_probe
# 1 is sudo -n refusing; 90 would mean the first, real authentication failed.
test "$LAST_STATUS" = 1
grep -q 'a password is required' <<< "$LAST_FAILURE"
pass 'after a successful sudo, a child exec of sudo -n is refused (the old ppid ticket allowed it)'

# polkit keeps no admin authorization either (review 2). A real polkitd on a
# private system bus; ares authorizes once through a text agent, then the same
# process asks again. Without logind every subject counts as remote, where the
# base cached NetworkManager's and firewalld's settings (auth_admin_keep).
# Control: a check-only action that keeps the cached default.
if grep -l '_keep[[:space:]]*</allow_' /usr/share/polkit-1/actions/*.policy; then
    echo 'An installed polkit default is still cached'
    exit 1
fi
cat > /usr/share/polkit-1/actions/org.aresos.ci.cached.policy <<'POLICY'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE policyconfig PUBLIC "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/PolicyKit/1/policyconfig.dtd">
<policyconfig>
  <action id="org.aresos.ci.cached">
    <description>Check-only control with a cached default</description>
    <message>Check-only control</message>
    <defaults>
      <allow_any>auth_admin_keep</allow_any>
      <allow_inactive>auth_admin_keep</allow_inactive>
      <allow_active>auth_admin_keep</allow_active>
    </defaults>
  </action>
</policyconfig>
POLICY
systemd-sysusers
mkdir -p /run/dbus
dbus-daemon --system --fork --nopidfile
helper=/usr/lib/polkit-1/polkit-agent-helper-1
stat -c '%a %U %n' "$helper"
if [[ ! -u $helper ]]; then
    # polkit's helper is socket-activated by systemd; start that socket here.
    cat /usr/lib/systemd/system/polkit-agent-helper.socket /usr/lib/systemd/system/polkit-agent-helper@.service
    socket=$(sed -n 's/^ListenStream=//p' /usr/lib/systemd/system/polkit-agent-helper.socket)
    command=$(sed -n 's/^ExecStart=//p' /usr/lib/systemd/system/polkit-agent-helper@.service)
    mkdir -p "$(dirname "$socket")"
    # shellcheck disable=SC2086 # the unit's command line, split as systemd would
    systemd-socket-activate --accept --inetd -l "$socket" $command &
fi
runuser -u polkitd -- /usr/lib/polkit-1/polkitd --no-debug &
for _ in $(seq 100); do
    if busctl --system status org.freedesktop.PolicyKit1 > /dev/null 2>&1; then
        break
    fi
    sleep 0.2
done
busctl --system status org.freedesktop.PolicyKit1 > /dev/null
runuser -u ares -- python3 - org.aresos.ci.cached org.freedesktop.NetworkManager.settings.modify.system \
    org.fedoraproject.FirewallD1.config > /tmp/polkit-reuse.json <<'PY'
import json, os, pty, select, subprocess, sys, time
password = open('/run/reuse-password').read().strip()

def authorize_twice(action):
    subject = subprocess.Popen(['sleep', '300'])
    agent, terminal = pty.fork()
    if agent == 0:
        os.execv('/usr/bin/pkttyagent', ['pkttyagent', '--process', str(subject.pid)])
    try:
        time.sleep(2)
        first = subprocess.Popen(['pkcheck', '--action-id', action, '--process', str(subject.pid),
                                  '--allow-user-interaction'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        transcript, answered, deadline = b'', False, time.monotonic() + 60
        while first.poll() is None and time.monotonic() < deadline:
            if select.select([terminal], [], [], 0.2)[0]:
                try:
                    transcript += os.read(terminal, 4096)
                except OSError:
                    pass
                if not answered and b'Password:' in transcript:
                    os.write(terminal, password.encode() + b'\n')
                    answered = True
        if first.poll() is None:
            first.kill()
        _, first_error = first.communicate()
        second = subprocess.run(['pkcheck', '--action-id', action, '--process', str(subject.pid)],
                                capture_output=True, text=True)
        return dict(action=action, first=first.returncode, password_asked=answered,
                    first_stderr=first_error.decode(errors='replace').strip(),
                    second=second.returncode, second_stderr=second.stderr.strip(),
                    agent=transcript.decode(errors='replace').replace(password, '<password>'))
    finally:
        os.kill(agent, 9)
        os.waitpid(agent, 0)
        subject.kill()
        subject.wait()

print(json.dumps([authorize_twice(action) for action in sys.argv[1:]], indent=1))
PY
cat /tmp/polkit-reuse.json
python3 - /tmp/polkit-reuse.json <<'PY'
import json, sys
rows = {row['action']: row for row in json.load(open(sys.argv[1]))}
for row in rows.values():
    # pkcheck: 0 authorized, 2 needs authentication that was not allowed here.
    assert row['first'] == 0 and row['password_asked'], row
control = rows.pop('org.aresos.ci.cached')
assert control['second'] == 0, ('the probe cannot see a cached authorization', control)
for row in rows.values():
    assert row['second'] == 2, ('authorization was reused', row)
print('polkit asked again for', ', '.join(rows))
PY
pkill -x polkitd || true
pkill -x dbus-daemon || true
pkill -f systemd-socket-activate || true
rm /usr/share/polkit-1/actions/org.aresos.ci.cached.policy
pass 'polkit: after ares authorizes once, the same process is asked again (a cached control action is reused)'
usermod -p '!*' ares
rm /run/reuse-password
test "$(getent shadow ares | cut -d: -f2)" = '!*'

# --- OS updaters stay out of reach; Flatpak and Homebrew are his.
for command in uupd ujust topgrade bazzite-updater bazzite-portal bazaar plasma-discover gnome-software; do
    path=$(command -v "$command" || true)
    if [[ -n $path ]]; then
        runuser -u ares -- test ! -x "$path"
    fi
done
pass 'uupd, ujust, topgrade, the Bazzite updater/portal and the stores are not executable by ares'
runuser -u ares -- test -x /usr/bin/flatpak
runuser -u ares -- flatpak --version
runuser -u ares -- test -x /usr/bin/brew
pass 'flatpak and brew are executable by ares'
while read -r unit; do
    test "$(systemctl --root=/ is-enabled "$unit" 2>/dev/null || true)" = masked
done < /usr/share/aresos/policy/masked-system-units.txt
while read -r unit; do
    test "$(systemctl --root=/ --global is-enabled "$unit" 2>/dev/null || true)" = masked
done < /usr/share/aresos/policy/masked-user-units.txt
for unit in flatpak-system-update.timer flatpak-system-update.service bootc-fetch-apply-updates.timer \
    rpm-ostreed-automatic.timer uupd.timer fwupd-refresh.timer brew-update.timer brew-upgrade.timer; do
    grep -qx "$unit" /usr/share/aresos/policy/masked-system-units.txt
done
for unit in flatpak-system-helper.service; do
    test "$(systemctl --root=/ is-enabled "$unit" 2>/dev/null || true)" != masked
done
for unit in flatpak-portal.service flatpak-session-helper.service; do
    test "$(systemctl --root=/ --global is-enabled "$unit" 2>/dev/null || true)" != masked
done
python3 /usr/libexec/aresos-audit --output /tmp/updaters.json
pass 'automatic updaters masked; Flatpak helpers available; static updater audit passes'

# --- Google Chrome from the image, under /usr, without a side updater.
lock=/usr/share/aresos/manifest/google-chrome.lock.json
test "$(rpm -q --qf '%{NEVRA}' google-chrome-stable)" = "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["nevra"])' "$lock")"
for command in google-chrome google-chrome-stable; do
    test "$(readlink -f "/usr/bin/$command")" = /usr/lib/opt/google/chrome/google-chrome
done
test -x /usr/lib/opt/google/chrome/chrome
stat -c '%a %U %n' /usr/lib/opt/google/chrome/chrome-sandbox
test "$(stat -c '%a %u' /usr/lib/opt/google/chrome/chrome-sandbox)" = '4755 0'
test ! -e /var/opt/google
test ! -e /var/opt
rpm -ql google-chrome-stable | grep '^/opt/google/' | sed 's|^/opt/|/usr/lib/opt/|' | while read -r file; do
    test -e "$file" || test -L "$file"
done
pass 'Chrome NEVRA matches its pin; every packaged /opt file lives under /usr/lib/opt; commands point there'
version=$(runuser -u ares -- env HOME=/tmp google-chrome --version)
printf '%s\n' "$version"
grep -Eq '^Google Chrome [0-9.]+' <<< "$version"
pass "ares can run google-chrome: $version"
systemd-tmpfiles --create /usr/lib/tmpfiles.d/aresos-google-chrome.conf
test "$(readlink /var/opt/google)" = /usr/lib/opt/google
test "$(readlink -f /opt/google/chrome/google-chrome)" = /usr/lib/opt/google/chrome/google-chrome
runuser -u ares -- env HOME=/tmp /opt/google/chrome/google-chrome --version
pass 'tmpfiles links /opt/google to the image copy'
if grep -rlis 'dl.google.com\|google-chrome' /etc/yum.repos.d /etc/dnf /etc/zypp 2>/dev/null; then
    echo 'A Google repository file exists'
    exit 1
fi
if find /etc/cron.* /etc/crontab /etc/anacrontab /var/spool/cron -iname '*google*' 2>/dev/null | grep .; then
    echo 'A Google cron job exists'
    exit 1
fi
test ! -e /etc/cron.daily/google-chrome
if rpm -q gpg-pubkey --qf '%{NAME}-%{VERSION}\n' | grep -i eb4c1bfd4f042f6dddccec917721f63bd38b4796; then
    echo 'The image rpm database trusts Google'\''s key'
    exit 1
fi
grep -qx 'repo_add_once="false"' /etc/default/google-chrome
pass 'no Google repository, cron job or trusted key in the image'
test -f /usr/share/applications/google-chrome.desktop
grep -q '^Exec=/usr/bin/google-chrome-stable' /usr/share/applications/google-chrome.desktop
handler=$(runuser -u ares -- env HOME=/var/home/ares XDG_CURRENT_DESKTOP=AresOS xdg-mime query default x-scheme-handler/https)
test "$handler" = google-chrome.desktop
handler=$(runuser -u ares -- env HOME=/var/home/ares XDG_CURRENT_DESKTOP=AresOS xdg-mime query default x-scheme-handler/http)
test "$handler" = google-chrome.desktop
pass 'xdg-open sends http and https links to Chrome in the AresOS session'
test ! -e /etc/opt/chrome || test -d /etc/opt/chrome
mkdir -p /etc/opt/chrome/policies/managed
rmdir /etc/opt/chrome/policies/managed /etc/opt/chrome/policies
pass '/etc/opt/chrome/policies can be created for the control layer'

# --- The daily login shell: PATH, Homebrew through /usr/bin/brew, no Flatpak errors.
# A stand-in for the stock administrator who owns the inherited Homebrew.
useradd --uid 1000 --no-create-home --shell /sbin/nologin aresos-fixture-owner
for stage in absent present; do
    if [[ $stage == present ]]; then
        # The inherited stock prefix, owned by UID 1000 and denied by an earlier image.
        mkdir -p /var/home/linuxbrew/.linuxbrew/bin
        printf '#!/bin/sh\nprintf "%%s\\n" "$*" >> /tmp/brew-calls\necho FIXTURE_BREW\n' > /var/home/linuxbrew/.linuxbrew/bin/brew
        chmod 0755 /var/home/linuxbrew/.linuxbrew/bin/brew
        touch /tmp/brew-calls
        chmod 0666 /tmp/brew-calls
        chown -R 1000:1000 /var/home/linuxbrew
        setfacl -m u:1001:--- /var/home/linuxbrew
        systemd-tmpfiles --create /usr/lib/tmpfiles.d/aresos-inherited-homebrew.conf
        getfacl -n /var/home/linuxbrew | grep -qx 'user:1001:r-x'
        runuser -u ares -- mkdir -p /var/home/ares/.local/share/flatpak/exports/bin
    fi
    runuser -l ares -c 'printf "%s\n" "$PATH"' > /tmp/login-path 2> /tmp/login-errors
    cat /tmp/login-path /tmp/login-errors
    test ! -s /tmp/login-errors
    login_path=$(cat /tmp/login-path)
    case $login_path in /var/home/ares/.local/bin:/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin*) ;; *) exit 1 ;; esac
    if [[ $stage == present ]]; then
        case :$login_path: in *:/usr/sbin:/home/linuxbrew/.linuxbrew/bin:*) ;; *) exit 1 ;; esac
        case :$login_path: in *:/var/home/ares/.local/share/flatpak/exports/bin:*) ;; *) exit 1 ;; esac
    else
        case :$login_path: in *linuxbrew*) exit 1 ;; esac
    fi
    pass "daily login PATH with Homebrew $stage: $login_path (no errors printed)"
done
runuser -u ares -- env HOME=/var/home/ares /usr/lib/systemd/user-environment-generators/60-flatpak > /tmp/generator 2> /tmp/generator-errors
test ! -s /tmp/generator-errors
pass 'the 60-flatpak user environment generator runs for ares without errors'
# Review 5: the session keeps the system PATH; a normal AresOS terminal gets
# his daily PATH and the recovery terminal keeps the system one. The hub's
# Terminal app (package 24) runs the same rcfile without the banner and gets
# his daily PATH too.
for mode in normal recovery hub; do
    terminal=()
    if [[ $mode != hub ]]; then
        terminal=(ARESOS_TERMINAL="$mode")
    fi
    runuser -u ares -- env -i HOME=/var/home/ares PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin \
        "${terminal[@]}" TERM=dumb /usr/bin/bash --rcfile /usr/share/aresos/bashrc -i \
        -c 'printf "TERMINAL_PATH=%s\n" "$PATH"' < /dev/null > /tmp/terminal-path 2> /dev/null
    terminal_path=$(sed -n 's/^TERMINAL_PATH=//p' /tmp/terminal-path)
    if [[ $mode == recovery ]]; then
        test "$terminal_path" = /usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin
    else
        case $terminal_path in /var/home/ares/.local/bin:/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/home/linuxbrew/.linuxbrew/bin*) ;; *) exit 1 ;; esac
    fi
    if [[ $mode == hub ]]; then
        if grep -q 'Super+Ctrl+Escape' /tmp/terminal-path; then
            exit 1
        fi
    else
        grep -q 'Super+Ctrl+Escape: recovery terminal' /tmp/terminal-path
    fi
    pass "$mode AresOS terminal PATH: $terminal_path"
done
grep -qF '"argv": ["/usr/bin/foot", "--app-id=aresos.terminal", "/usr/bin/bash", "--rcfile", "/usr/share/aresos/bashrc", "-i"]' \
    /usr/share/aresos/apps/terminal.json
grep -qx 'export PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin' /usr/bin/aresos-session
pass 'the session itself starts with the system PATH and absolute commands'
# greetd's session wrapper, a non-interactive /bin/sh, sources /etc/profile
# before /usr/bin/aresos-session: the base image's profile scripts run there
# with the system PATH. His login shells get his own.
wrapper_path=$(runuser -u ares -- env -i HOME=/var/home/ares PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin \
    /bin/sh -c '[ -f /etc/profile ] && . /etc/profile; printf "%s" "$PATH"' < /dev/null 2> /dev/null)
case ":$wrapper_path:" in *:/var/home/ares/.local/bin:*) exit 1 ;; esac
login_path=$(runuser -l ares -c 'printf "%s" "$PATH"' < /dev/null 2> /dev/null)
case ":$login_path:" in *:/var/home/ares/.local/bin:*) ;; *) exit 1 ;; esac
pass "greetd's profile wrapper keeps the system PATH ($wrapper_path); his login shell adds his own ($login_path)"
# Every absolute command the greeter, session, terminals, shortcuts and their
# helpers run must exist in this image, or an absolute path would only trade
# one way to fail for another.
# Package 23: the desktop supervisor (autostart), its Java wrapper (Prism's
# wrapper command), its message window and the app helper it starts.
startup_commands=$( (grep -ohE '/usr/(local/)?(s?bin|libexec)/[A-Za-z0-9/._-]+' /etc/greetd/config.toml \
    /usr/bin/aresos-session /usr/bin/aresos-terminal /usr/share/aresos/bashrc /etc/profile.d/aresos.sh \
    /usr/share/aresos/labwc/autostart /usr/share/aresos/labwc/rc.xml /usr/libexec/aresos-keyboard \
    /usr/libexec/aresos-subids /usr/bin/brew /usr/libexec/aresos-shell /usr/share/aresos/apps/*.json \
    /usr/libexec/aresos-desktop /usr/libexec/aresos-desktop-java /usr/share/aresos/desktop-view.bashrc \
    /usr/libexec/aresos-level) | sort -u)
for command in /usr/bin/dbus-run-session /usr/bin/dbus-daemon /usr/bin/labwc /usr/bin/busctl /usr/bin/foot \
    /usr/libexec/aresos-shell /usr/bin/systemd-run /usr/bin/systemctl /usr/bin/kwrite /usr/bin/google-chrome \
    /usr/libexec/aresos-desktop /usr/libexec/aresos-desktop-java /usr/libexec/aresos-cover /usr/bin/prismlauncher \
    /usr/bin/python3 /usr/bin/cat /usr/libexec/aresos-indicator; do
    grep -qx "$command" <<< "$startup_commands"
done
for command in $startup_commands; do
    test -x "$command"
done
pass "all $(wc -l <<< "$startup_commands") absolute startup commands exist: $(tr '\n' ' ' <<< "$startup_commands")"
# Package 24's app helper under the session's system PATH, with broken
# programs of every name it or its apps could look up first on that PATH:
# every app resolves, and every launch runs absolute commands only.
shadow=$(mktemp -d /tmp/pkg21-helper-shadow.XXXXXX)
for name in python3 systemd-run systemctl foot bash kwrite google-chrome google-chrome-stable sh env; do
    printf '#!/bin/sh\nprintf "%%s\\n" "$0" >> %s/ran\nexit 97\n' "$shadow" > "$shadow/$name"
    chmod 0755 "$shadow/$name"
done
chmod 0755 "$shadow"
install -m 0666 /dev/null "$shadow/ran"
runuser -u ares -- env -i HOME=/var/home/ares PATH="$shadow:/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin" \
    /usr/libexec/aresos-shell --list > /tmp/helper-list.json
runuser -u ares -- env -i HOME=/var/home/ares PATH="$shadow:/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin" \
    /usr/bin/python3 - /tmp/helper-list.json <<'PY'
import importlib.machinery, importlib.util, json, os, sys
listed = json.load(open(sys.argv[1]))
assert {row['id']: row['available'] for row in listed['apps']} == {'browser': True, 'notepad': True, 'terminal': True}, listed
loader = importlib.machinery.SourceFileLoader('aresos_shell', '/usr/libexec/aresos-shell')
spec = importlib.util.spec_from_loader('aresos_shell', loader)
shell = importlib.util.module_from_spec(spec)
loader.exec_module(shell)
apps, _ = shell.load_registry(shell.REGISTRY)
for app in apps.values():
    argv, _, reason = shell.resolve(app)
    assert reason is None, (app.id, reason)
    command = shell.ScopeLauncher(environ={'HOME': '/var/home/ares'}).command(app, argv, 'pkg21')
    assert command[0] == '/usr/bin/systemd-run' and os.access(command[0], os.X_OK), command
    assert os.path.isabs(argv[0]) and os.access(argv[0], os.X_OK), argv
    for part in argv[1:]:
        if part.startswith('/'):
            assert os.path.exists(part), (app.id, part)
    print('HELPER_LAUNCH', app.id, ' '.join(command))
assert shell.LIST_SCOPES[0] == '/usr/bin/systemctl' and os.access(shell.LIST_SCOPES[0], os.X_OK)
PY
test ! -s "$shadow/ran"
rm -rf "$shadow"
pass 'the app helper resolves browser, notepad and terminal and launches by absolute paths under the system PATH with shadows first'
# Package 30 review fixes: the reviewed window hints ship in the image and pass the helper's own strict check.
runuser -u ares -- env -i HOME=/var/home/ares PATH=/usr/bin /usr/bin/python3 - <<'PY'
import importlib.machinery, importlib.util
loader = importlib.machinery.SourceFileLoader('aresos_shell', '/usr/libexec/aresos-shell')
spec = importlib.util.spec_from_loader('aresos_shell', loader)
shell = importlib.util.module_from_spec(spec)
loader.exec_module(shell)
hints = shell.load_hints('/usr/share/aresos/apps/hints')
assert hints == {'lunarclient.desktop': shell.Hint('lunarclient.desktop', ('com.mojang.minecraft',), (), 'discrete',
                                                   (('SDL_VIDEO_DRIVER', 'wayland'),)),
                 'steam.desktop': shell.Hint('steam.desktop', (), ('steam_app_',))}, hints
PY
test "$(stat -c %U /usr/share/aresos/apps/hints /usr/share/aresos/apps/hints/*.json | sort -u)" = root
pass 'the app helper loads the two reviewed window hints (Lunar Client, Steam), owned by root'
test "$(runuser -l ares -c 'command -v brew')" = /usr/bin/brew
test "$(runuser -l ares -c 'brew --version')" = FIXTURE_BREW
grep -qx -- '--version' /tmp/brew-calls
expect_failure runuser -l ares -c 'brew install aresos-never-installed < /dev/null'
grep -q 'Homebrew belongs to aresos-fixture-owner; sudo asks for your own password' <<< "$LAST_FAILURE"
grep -Eq 'sudo: (a terminal is required|a password is required)' <<< "$LAST_FAILURE"
if grep -q install /tmp/brew-calls; then
    echo 'Homebrew ran an install for ares without a password'
    exit 1
fi
test "$(stat -c %u /var/home/linuxbrew/.linuxbrew)" = 1000
pass 'ares runs read-only brew directly; installs go through sudo as the prefix owner and fail without a password'

# --- Terminal, keys, polkit agent, tools.
# Review 1: a broken `foot` first on his PATH must not take either terminal
# away. A recording stand-in replaces /usr/bin/foot in this container only.
mv /usr/bin/foot /usr/bin/foot.real
printf '#!/bin/sh\nprintf "%%s|%%s\\n" "$ARESOS_TERMINAL" "$*" >> /tmp/foot-calls\n' > /usr/bin/foot
chmod 0755 /usr/bin/foot
runuser -u ares -- mkdir -p /var/home/ares/.local/bin
printf '#!/bin/sh\ntouch /tmp/broken-foot-ran\nexit 3\n' > /var/home/ares/.local/bin/foot
chmod 0755 /var/home/ares/.local/bin/foot
chown ares:ares /var/home/ares/.local/bin/foot
touch /tmp/foot-calls
chmod 0666 /tmp/foot-calls
runuser -l ares -c 'test "$(command -v foot)" = /var/home/ares/.local/bin/foot && /usr/bin/aresos-terminal --recovery && /usr/bin/aresos-terminal'
test ! -e /tmp/broken-foot-ran
cat /tmp/foot-calls
test "$(cat /tmp/foot-calls)" = "recovery|--title=AresOS /usr/bin/bash --rcfile /usr/share/aresos/bashrc -i
normal|--title=AresOS /usr/bin/bash --rcfile /usr/share/aresos/bashrc -i"
mv /usr/bin/foot.real /usr/bin/foot
rm /var/home/ares/.local/bin/foot
pass 'both terminals run /usr/bin/foot even with a broken foot first on PATH'
# --- TuneD (review 2): ares may switch power profiles without a password, and
# tuned-ppd maps them to the TuneD profiles in /etc/tuned/ppd.conf. None of
# those, with everything they include, may touch the bootloader or kernel
# arguments; direct TuneD profile changes are denied to ares in polkit.
python3 - <<'PY'
import configparser, pathlib
ppd = configparser.ConfigParser(interpolation=None, strict=False)
assert ppd.read('/etc/tuned/ppd.conf'), 'tuned-ppd configuration missing'
roots = [pathlib.Path('/etc/tuned/profiles'), pathlib.Path('/usr/lib/tuned/profiles'),
         pathlib.Path('/etc/tuned'), pathlib.Path('/usr/lib/tuned')]
targets = {value.strip() for section in ('profiles', 'battery') if ppd.has_section(section)
           for _, value in ppd.items(section)}
assert targets, 'no profiles mapped in ppd.conf'

def check(name, seen):
    if name in seen:
        return
    seen.add(name)
    folder = next((root / name for root in roots if (root / name / 'tuned.conf').is_file()), None)
    assert folder, f'TuneD profile {name} not found'
    profile = configparser.ConfigParser(interpolation=None, strict=False)
    profile.read(folder / 'tuned.conf')
    for section in profile.sections():
        plugin = profile.get(section, 'type', fallback=section).strip()
        assert plugin != 'bootloader' and not profile.has_option(section, 'cmdline'), (name, section)
    for include in profile.get('main', 'include', fallback='').split(','):
        include = include.strip()
        if include:
            assert '$' not in include, f'{name} includes a computed profile: {include}'
            check(include, seen)

seen = set()
for target in sorted(targets):
    check(target, seen)
print('tuned-ppd profiles and their includes, none with a bootloader section:', ', '.join(sorted(seen)))
PY
pass 'every power profile ares can switch to leaves the bootloader and kernel arguments alone'
grep -qx 'font=monospace:size=16' /etc/xdg/foot/foot.ini
pass 'foot default font size 16 (a user foot.ini replaces this file)'
grep -qx 'clipboard-paste=Control+v Control+Shift+v XF86Paste' /etc/xdg/foot/foot.ini
foot --check-config -c /etc/xdg/foot/foot.ini
pass 'foot pastes with Ctrl+V and Ctrl+Shift+V, and its config parses (package 55)'
grep -qx '/usr/libexec/kf6/polkit-kde-authentication-agent-1 &' /usr/share/aresos/labwc/autostart
test -x /usr/libexec/kf6/polkit-kde-authentication-agent-1
rpm -qf /usr/libexec/kf6/polkit-kde-authentication-agent-1
pass 'the labwc session starts the base image polkit agent'
python3 - <<'PY'
import os, xml.etree.ElementTree as ET
root = ET.parse('/usr/share/aresos/labwc/rc.xml').getroot()
binds = {b.get('key'): b.find('action').get('command') for b in root.iter('keybind')}
library = open(next(p for p in ('/usr/lib64/libxkbcommon.so.0',) if os.path.exists(p)), 'rb').read()
# Package 320: each key runs aresos-level with its action; the script makes the change, then tells the indicator.
actions = {'XF86MonBrightnessUp': 'brightness-up', 'XF86MonBrightnessDown': 'brightness-down',
           'XF86AudioRaiseVolume': 'volume-up', 'XF86AudioLowerVolume': 'volume-down',
           'XF86AudioMute': 'mute', 'XF86AudioMicMute': 'mic-mute'}
for key, action in actions.items():
    assert binds[key] == f'/usr/libexec/aresos-level {action}', (key, binds[key])
    assert b'\0' + key.encode() + b'\0' in library, f'{key} is not a keysym name libxkbcommon knows'
    print(key, '->', binds[key])
assert os.access('/usr/libexec/aresos-level', os.X_OK)
assert binds['W-C-Escape'] == '/usr/bin/aresos-terminal --recovery'
PY
for program in /usr/libexec/aresos-level /usr/libexec/aresos-settings /usr/libexec/aresos-indicator; do
    test "$(stat -c '%U:%G %a' "$program")" = 'root:root 755'
done
bash -n /usr/libexec/aresos-level
# With no settings file, aresos-settings gives the defaults (package 320) and writes nothing.
settings=$(runuser -u ares -- env -i HOME=/nonexistent PATH=/usr/bin /usr/libexec/aresos-settings get)
test "$settings" = '{"indicator-place": "top", "indicator-size": "medium", "look": "B"}'
pass "brightness, volume, mute and mic-mute keys run aresos-level (package 320); aresos-settings gives the defaults ($settings); recovery terminal kept"
for command in script qrencode brightnessctl wpctl gdbus flock timeout setsid; do
    command -v "$command"
done
script --version
qrencode -t UTF8 'AresOS' > /dev/null
brightnessctl --version
rpm -q util-linux-script qrencode brightnessctl
pass 'script, qrencode and brightnessctl are installed'

# --- Rootless containers: subordinate IDs, and the boot service that adds them.
grep -x 'ares:524288:65536' /etc/subuid
grep -x 'ares:524288:65536' /etc/subgid
before=$(sha256sum /etc/subuid /etc/subgid)
/usr/libexec/aresos-subids
test "$(sha256sum /etc/subuid /etc/subgid)" = "$before"
test "$(systemctl --root=/ is-enabled aresos-subids.service)" = enabled
pass 'ares has subordinate ID ranges; the boot service is enabled and idempotent'

# --- Package 311: labwc is our rebuild of Fedora's source package, the only labwc, unchanged since it was installed.
labwc_nevra=$(python3 -c 'import json; print(json.load(open("/usr/share/aresos/manifest/labwc.lock.json"))["result"]["nevra"])')
test "$labwc_nevra" = labwc-0.9.6-1.fc44.aresos1.x86_64
test "$(rpm -q --qf '%{NEVRA}\n' labwc)" = "$labwc_nevra"
labwc_verify=$(rpm -V labwc)
test -z "$labwc_verify"
pass "labwc is the locked rebuild ($labwc_nevra), the only labwc installed, and rpm -V labwc is clean"
# labwc is built on fedora:44 and runs on this image: every library must be found here, and every Requires must be
# met by a package of this image. labwc is the only package that comes from that stage. rpm -V above checks versions.
python3 -I - <<'LABWC_RUNTIME'
import subprocess
import sys


def run(*command):
    return subprocess.run(command, capture_output=True, text=True)


ldd = run('ldd', '/usr/bin/labwc')
missing = [line.strip() for line in ldd.stdout.splitlines() if 'not found' in line]
if ldd.returncode != 0 or missing:
    sys.exit(f'LABWC_RUNTIME_FAILED ldd exit {ldd.returncode}, not found: {missing}')
requires = run('rpm', '-q', '--qf', '[%{REQUIRENAME}\\n]', 'labwc')
names = sorted({name for name in requires.stdout.split('\n') if name and not name.startswith('rpmlib(')})
if requires.returncode != 0 or not names:
    sys.exit(f'LABWC_RUNTIME_FAILED cannot read the Requires of labwc: {requires.stderr.strip()}')
unmet = []
for name in names:
    providers = run('rpm', '-q', '--whatprovides', '--qf', '%{NAME}\\n', name)
    if providers.returncode != 0 or not set(providers.stdout.split()) - {'labwc'}:
        unmet.append(name)
if unmet:
    sys.exit(f'LABWC_RUNTIME_FAILED no package of this image provides: {unmet}')
print(f'LABWC_RUNTIME_OK {len(names)} requirements')
LABWC_RUNTIME
pass 'labwc finds every library, and packages of this image provide everything it requires'

# --- Package 23: Minecraft starts in AresOS.
lock=/usr/share/aresos/minecraft/desktop.lock.json
java=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["java"]["path"])' "$lock")
java_nevra=$(python3 -c 'import json; print(next(p["nevra"] for p in json.load(open("/usr/share/aresos/manifest/packages.lock.json"))["packages"] if p["nevra"].startswith("java-25-openjdk-headless-")))')
test "$(rpm -q --qf '%{NEVRA}' java-25-openjdk-headless)" = "$java_nevra"
test "$(rpm -qf --qf '%{NAME}' "$java")" = java-25-openjdk-headless
test ! -L "$java"
runuser -u ares -- "$java" -version 2>&1 | tee /tmp/pkg23-java-version
grep -Eq '^openjdk version "25(\.[0-9]+)*"' /tmp/pkg23-java-version
pass "Java 25 from the package lock ($java_nevra) at $java, runnable by ares"
test "$(readlink /usr/bin/prismlauncher)" = /usr/lib/prismlauncher/bin/prismlauncher
test ! -e /usr/lib/prismlauncher/portable.txt
test ! -e /usr/lib/prismlauncher/UserData
if find /usr/lib/prismlauncher -name '*updater*' | grep .; then
    echo "Prism's updater is in the image"
    exit 1
fi
if find /usr/lib/prismlauncher /usr/share/aresos/minecraft /usr/libexec/aresos-desktop /usr/libexec/aresos-desktop-java \
    -perm /6000 | grep .; then
    echo 'A setuid or setgid file belongs to the desktop'
    exit 1
fi
# The tarball records its files as UID 1001, which is ares on AresOS: they
# must belong to root in the image, or ares could change Prism.
owned=(-not -type l '(' -not -user root -o -not -group root -o -perm /022 ')')
if find /usr/lib/prismlauncher /usr/share/aresos/minecraft "${owned[@]}" | grep .; then
    echo 'A desktop file in /usr is not root-owned or is group/world-writable'
    exit 1
fi
# Every bundled file is the one build.sh recorded from the pinned tarball.
sha256sum --quiet -c /usr/share/aresos/manifest/prism-files.sha256
install -d -o ares -g ares /tmp/pkg23-prism
prism_version="PrismLauncher $(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["prism"]["version"])' "$lock")"
# Prism prints its version and then an empty line.
runuser -u ares -- env -i HOME=/tmp/pkg23-prism LANG=C.UTF-8 QT_QPA_PLATFORM=offscreen \
    /usr/bin/prismlauncher --version > /tmp/pkg23-prism-version 2>&1
cat /tmp/pkg23-prism-version
grep -qx "$prism_version" /tmp/pkg23-prism-version
status=0
runuser -u ares -- env -i HOME=/tmp/pkg23-prism LANG=C.UTF-8 QT_QPA_PLATFORM=offscreen XDG_RUNTIME_DIR=/tmp/pkg23-prism \
    /usr/bin/timeout 20 /usr/bin/prismlauncher > /tmp/pkg23-prism-start.txt 2>&1 || status=$?
test "$status" = 124
prism_log=/tmp/pkg23-prism/.local/share/PrismLauncher/logs/PrismLauncher-0.log
grep -F 'Updates Enabled            : No' "$prism_log"
grep -F 'Adjusted by                : "Persistent data path"' "$prism_log"
grep -F 'Application root path      : "/usr/lib/prismlauncher"' "$prism_log"
pass "Prism Launcher $prism_version from its pinned bundle: updater removed, data in his home, no setuid files"
runuser -u ares -- /usr/bin/python3 - <<'PY'
import importlib.machinery, importlib.util, json, sys
loader = importlib.machinery.SourceFileLoader('aresos_desktop', '/usr/libexec/aresos-desktop')
spec = importlib.util.spec_from_loader('aresos_desktop', loader)
desktop = importlib.util.module_from_spec(spec)
loader.exec_module(desktop)
lock = desktop.load_lock()
problems = desktop.verify_inputs(lock, desktop.SHARE)
assert problems == [], problems
for path, digest in desktop.pinned_files(lock, desktop.SHARE):
    print('PINNED', digest, path)
PY
pass 'every provisioning input in /usr/share/aresos/minecraft matches its pin; Java and Prism are present'
# The mod jar in the image is the one the image records (build.sh configure).
python3 - /usr/share/aresos <<'PY'
import hashlib, json, pathlib, re, sys
share = pathlib.Path(sys.argv[1])
record = json.loads((share / 'manifest/aresos-mod.json').read_text())
assert sorted(record) == ['pinned_sha256', 'sha256', 'source_revision'], record
assert re.fullmatch('[0-9a-f]{40}', record['source_revision']), record
jar = hashlib.sha256((share / 'minecraft/mods/aresos.jar').read_bytes()).hexdigest()
assert jar == record['sha256'], f'The mod jar in the image is {jar}; the image records {record["sha256"]}'
print('MOD_JAR_RECORDED', jar, 'from', record['source_revision'],
      'its pin' if jar == record['pinned_sha256'] else f'NOT its pin {record["pinned_sha256"]} (throwaway build)')
PY
pass 'the mod jar in the image is the one its manifest records (aresos-mod.json: SHA-256 and source commit)'
lines=$(grep -Ev '^[[:space:]]*(#|$)' /usr/share/aresos/labwc/autostart)
test "$lines" = '/usr/libexec/kf6/polkit-kde-authentication-agent-1 &
/usr/libexec/aresos-desktop session &'
test "$(readlink /usr/bin/aresos-desktop)" = ../libexec/aresos-desktop
grep -q '<windowRule identifier="aresos-desktop" serverDecoration="no"><action name="Maximize" /></windowRule>' \
    /usr/share/aresos/labwc/rc.xml
pass 'labwc autostart starts the desktop supervisor (no session terminal); the hub window is borderless and maximized'
# Package 23b: the startup cover. Present and executable, its GTK 4, Pango and cairo load as ares, its labwc rule
# is there (and the hub's rule above is unchanged), and fontconfig finds package 31's Space Grotesk for it. This
# container has real directory mtimes, so it cannot see a stale font cache that the deployed image (mtime 0) would
# use: the VM's cover step checks fc-match in the real session, which proves the drawing (review 1, finding 1).
test -x /usr/libexec/aresos-cover
test "$(stat -c '%U:%G %a' /usr/libexec/aresos-cover)" = 'root:root 755'
grep -q '<windowRule identifier="aresos.cover" serverDecoration="no"><action name="ToggleFullscreen" /><action name="ToggleAlwaysOnTop" /></windowRule>' \
    /usr/share/aresos/labwc/rc.xml
# Package 25: the black screen of a stop has a rule of its own (each of its windows asks for its output itself).
grep -q '<windowRule identifier="aresos.black" serverDecoration="no"><action name="ToggleAlwaysOnTop" /></windowRule>' \
    /usr/share/aresos/labwc/rc.xml
runuser -u ares -- env -i HOME=/tmp PATH=/usr/bin /usr/bin/python3 - <<'PY'
import importlib.machinery, importlib.util
loader = importlib.machinery.SourceFileLoader('aresos_cover', '/usr/libexec/aresos-cover')
spec = importlib.util.spec_from_loader('aresos_cover', loader)
cover = importlib.util.module_from_spec(spec)
loader.exec_module(cover)
GLib, Gtk, Pango, PangoCairo, cairo = cover.load_gtk()
print('COVER_GTK', Gtk.get_major_version(), Gtk.get_minor_version(), 'cairo', cairo.version)
assert Gtk.get_major_version() == 4
assert cover.parse(['--again']).again and cover.parse([]).limit == cover.LIMIT == 600.0
PY
font=$(runuser -u ares -- env -i HOME=/tmp PATH=/usr/bin /usr/bin/fc-match --format '%{file}' 'Space Grotesk:bold')
test "$font" = /usr/share/fonts/aresos/SpaceGrotesk-Variable.ttf
pass "the startup cover is installed and loads GTK 4 as ares; fontconfig finds Space Grotesk ($font); its labwc rule is set"
# Package 320: the indicator pack and its font, followed by the program's real loader without a display.
python3 - <<'PY'
import hashlib
from pathlib import Path

share = Path('/usr/share')
font = share / 'fonts/aresos/Jersey10-Regular.ttf'
assert font.stat().st_size == 77732
assert hashlib.sha256(font.read_bytes()).hexdigest() == 'db9cbd091617048a145d249daa2b815fe7083be6ab66ac26626e21a4e01c3e82'
licence = font.with_name('OFL-Jersey10.txt').read_text()
assert 'Copyright 2023 The Soft Type Project Authors' in licence
assert 'SIL OPEN FONT LICENSE Version 1.1' in licence

pack = share / 'aresos/look'
icons = ('sun', 'speaker', 'speaker-muted', 'microphone', 'microphone-off')
names = {'plate', 'slot', *icons, *(f'{icon}-unavailable' for icon in icons),
         *(f'step-{kind}' for kind in ('lit', 'unlit', 'muted', 'part', 'limit'))}
buttons = ('menu', 'iconify', 'max', 'max_toggled', 'close', 'shade', 'shade_toggled', 'desk', 'desk_toggled')
frame = {f'sprites/frame/{button}{hover}-{state}.png' for button in buttons
         for hover in ('', '_hover') for state in ('active', 'inactive')}
directories = {'sprites', 'sprites/frame'}
expected = {'look.json', *directories, *(f'sprites/{name}.png' for name in names), *frame}
paths = {path.relative_to(pack).as_posix() for path in pack.rglob('*')}
assert paths == expected, f'look A file list differs: {paths ^ expected}'
files = sorted(paths - directories)
tree = '\n'.join(f'{hashlib.sha256((pack / name).read_bytes()).hexdigest()}  {name}' for name in files)
digest = hashlib.sha256(tree.encode()).hexdigest()
assert digest == 'f4c4a0f201d30e5cafddd278eb8f69d0f40d61e1efa12ede8a7bb7f5735baabd', f'look A differs: {digest}'
PY
font=$(runuser -u ares -- env -i HOME=/nonexistent PATH=/usr/bin /usr/bin/fc-match --format '%{file}' 'Jersey 10')
test "$font" = /usr/share/fonts/aresos/Jersey10-Regular.ttf
test -x /usr/bin/pw-dump
pass "Jersey 10 and its licence are installed ($font); the look A pack matches its pin"
layer=/usr/lib64/libgtk4-layer-shell.so.0
if [[ ! -r $layer ]]; then
    echo 'The indicator requires gtk4-layer-shell from the R29 image package' >&2
    exit 1
fi
runuser -u ares -- env -i HOME=/nonexistent PATH=/usr/bin LD_PRELOAD="$layer" /usr/bin/python3 - <<'PY'
import os
import runpy

gui = runpy.run_path('/usr/libexec/aresos-indicator')['load_gui']()
assert gui.Gtk.get_major_version() == 4
assert gui.layer.get_major_version() >= 1
assert (os.environ['GDK_DISABLE'], os.environ['GSK_RENDERER']) == ('gl,vulkan', 'cairo')
print('INDICATOR_GTK', gui.Gtk.get_major_version(), gui.Gtk.get_minor_version(), 'cairo', gui.cairo.version,
      'gtk4-layer-shell', gui.layer.get_major_version(), gui.layer.get_minor_version(), gui.layer.get_micro_version())
PY
pass 'the indicator loads GTK 4, Pango, Cairo and Gtk4LayerShell as the everyday account'
# Package 53f: the laptop home draws natively. Load the program's own load_gui() without a display, as the cover's
# check does: GTK 4, Pango and Cairo as ares, with the Cairo renderer and no GPU device asked for.
test -x /usr/libexec/aresos-laptop-home
runuser -u ares -- env -i HOME=/tmp PATH=/usr/bin /usr/bin/python3 - <<'PY'
import importlib.machinery, importlib.util, os
loader = importlib.machinery.SourceFileLoader('aresos_laptop_home', '/usr/libexec/aresos-laptop-home')
spec = importlib.util.spec_from_loader('aresos_laptop_home', loader)
home = importlib.util.module_from_spec(spec)
loader.exec_module(home)
gui = home.load_gui()
print('LAPTOP_HOME_GTK', gui.Gtk.get_major_version(), gui.Gtk.get_minor_version(), 'cairo', gui.cairo.version)
assert gui.Gtk.get_major_version() == 4
assert (os.environ['GDK_DISABLE'], os.environ['GSK_RENDERER']) == ('gl,vulkan', 'cairo')
import struct, zlib
def chunk(name, data):
    return struct.pack('>I', len(data)) + name + data + struct.pack('>I', zlib.crc32(name + data))
png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 6, 0, 0, 0))
       + chunk(b'IDAT', zlib.compress(b'\0\1\2\3\4')) + chunk(b'IEND', b''))
# The decoder runs only in bubblewrap (53f review fix 1). Where this container allows no user namespace, bubblewrap
# itself cannot start, and the home must then refuse to decode rather than decode unsandboxed.
import subprocess
assert home.BWRAP == '/usr/bin/bwrap' and os.access(home.BWRAP, os.X_OK)
try:
    decoded = home.decode_png(png)
except (OSError, ValueError, subprocess.SubprocessError) as error:
    alone = subprocess.run([home.BWRAP, '--ro-bind', '/', '/', '--', '/usr/bin/true'], capture_output=True)
    assert alone.returncode != 0, f'bubblewrap runs here, yet the decoder failed: {error}'
    print('LAPTOP_HOME_DECODER refused: bubblewrap cannot start in this container, and no icon is decoded')
else:
    assert decoded == (1, 1, b'\1\2\3\4')
    print('LAPTOP_HOME_DECODER decoded in bubblewrap')
PY
pass 'the laptop home loads GTK 4, Pango and Cairo as ares with the Cairo renderer, and its icon decoder is sandboxed'
# Package 323: the laptop home also loads the layer library when preloaded.
layer_nevra=$(python3 -I - /usr/share/aresos/manifest/packages.lock.json <<'LAYER_NEVRA'
import json, sys
with open(sys.argv[1]) as lock:
    pinned = [p['nevra'] for p in json.load(lock)['packages'] if p['nevra'].rsplit('-', 2)[0] == 'gtk4-layer-shell']
assert len(pinned) == 1, 'the package lock must pin exactly one gtk4-layer-shell'
print(pinned[0])
LAYER_NEVRA
)
test "$(rpm -q --qf '%{NEVRA}\n' gtk4-layer-shell)" = "$layer_nevra"
layer_verify=$(rpm -V gtk4-layer-shell)
test -z "$layer_verify"
layer_library=/usr/lib64/libgtk4-layer-shell.so.0
test -f "$layer_library"
runuser -u ares -- env -i HOME=/tmp PATH=/usr/bin LD_PRELOAD="$layer_library" /usr/bin/python3 - <<'LAPTOP_HOME_LAYER'
import importlib.machinery, importlib.util
loader = importlib.machinery.SourceFileLoader('aresos_laptop_home', '/usr/libexec/aresos-laptop-home')
spec = importlib.util.spec_from_loader('aresos_laptop_home', loader)
home = importlib.util.module_from_spec(spec)
loader.exec_module(home)
layer = home.load_gui().layer
assert layer is not None, 'the laptop home could not load Gtk4LayerShell'
version = f'{layer.get_major_version()}.{layer.get_minor_version()}.{layer.get_micro_version()}'
print('LAPTOP_HOME_LAYER_SHELL', version)
LAPTOP_HOME_LAYER
pass "gtk4-layer-shell ($layer_nevra) verifies and the laptop home loads it as ares with the preload"

# Package 323: the laptop home's monospace font and its licence.
sha256sum -c <<'JETBRAINS_MONO_SHA256'
48715a42ec242c21e9f02692891e147d022299a52e48d5e413e1a942193ffeda  /usr/share/fonts/aresos/JetBrainsMono-Variable.ttf
b2fe5e8987594e9ffd1d2ca52a2f5d73eb8335243893c5d6254b5ad69269591d  /usr/share/fonts/aresos/OFL-JetBrainsMono.txt
JETBRAINS_MONO_SHA256
font=$(runuser -u ares -- env -i HOME=/tmp PATH=/usr/bin /usr/bin/fc-match --format '%{file}' 'JetBrains Mono')
test "$font" = /usr/share/fonts/aresos/JetBrainsMono-Variable.ttf
pass "fontconfig finds the pinned JetBrains Mono ($font) as ares, and its licence is installed"

# Package 323: the Mesa EGL and Intel Vulkan manifests the desktop supervisor can select.
mesa_egl=/usr/share/glvnd/egl_vendor.d/50_mesa.json
intel_vulkan=/usr/share/vulkan/icd.d/intel_icd.x86_64.json
for manifest in "$mesa_egl" "$intel_vulkan"; do
    test -f "$manifest"
    test ! -L "$manifest"
    rpm -qf "$manifest"
done
python3 -I - "$mesa_egl" "$intel_vulkan" <<'DRIVER_MANIFESTS'
import json, re, subprocess, sys
from pathlib import Path


def cached_libraries(soname):
    cache = subprocess.check_output(['ldconfig', '-p'], text=True)
    for entry in cache.splitlines():
        if match := re.fullmatch(r'\s*(\S+) \(([^)]*)\) => (/.+)', entry):
            name, flags, path = match.groups()
            if name == soname and 'x86-64' in flags.replace(' ', '').split(','):
                yield Path(path)


for manifest in map(Path, sys.argv[1:]):
    library = json.loads(manifest.read_text())['ICD']['library_path']
    path = Path(library)
    if path.is_absolute():
        candidates = [path]
    else:
        assert library and '/' not in library, f'{manifest}: expected an absolute library path or soname: {library!r}'
        candidates = cached_libraries(library)
    found = next((candidate for candidate in candidates if candidate.is_file()), None)
    assert found is not None, f'{manifest}: missing library {library!r}'
    print(f'{manifest}: {library} => {found}')
DRIVER_MANIFESTS
pass 'the Mesa EGL and Intel Vulkan manifests are package-owned and name libraries in the image'

# Super+Ctrl+Escape opens the recovery terminal, then ends the cover through the supervisor (PLAN-GAP 2). The
# supervisor takes the command as ares; with no supervisor running here it says so and exits 1.
python3 - <<'PY'
import xml.etree.ElementTree as ET
root = ET.parse('/usr/share/aresos/labwc/rc.xml').getroot()
binds = [bind for bind in root.iter('keybind') if bind.get('key') == 'W-C-Escape']
assert len(binds) == 1, binds
actions = [(action.get('name'), action.get('command')) for action in binds[0]]
assert actions == [('Execute', '/usr/bin/aresos-terminal --recovery'),
                   ('Execute', '/usr/libexec/aresos-desktop hide-cover')], actions
PY
install -d -o ares -g ares -m 0700 /tmp/pkg23b-run
hide_code=0
hide_answer=$(runuser -u ares -- env -i HOME=/tmp XDG_RUNTIME_DIR=/tmp/pkg23b-run PATH=/usr/bin \
    /usr/libexec/aresos-desktop hide-cover 2>&1) || hide_code=$?
test "$hide_code" = 1
grep -q 'supervisor is not running' <<<"$hide_answer"
rm -rf /tmp/pkg23b-run
pass 'Super+Ctrl+Escape opens the recovery terminal and then runs aresos-desktop hide-cover, which ares can run'
# Provisioning as ares from the image's real inputs: creates the instance,
# changes nothing on a second run, and reports a changed instance.
install -d -o ares -g ares -m 0700 /tmp/pkg23-home /tmp/pkg23-run
runuser -u ares -- env -i HOME=/tmp/pkg23-home /usr/bin/python3 - <<'PY'
import importlib.machinery, importlib.util, json, os, pathlib
loader = importlib.machinery.SourceFileLoader('aresos_desktop', '/usr/libexec/aresos-desktop')
spec = importlib.util.spec_from_loader('aresos_desktop', loader)
desktop = importlib.util.module_from_spec(spec)
loader.exec_module(desktop)
lock = desktop.load_lock()
paths = desktop.Paths('/tmp/pkg23-home', '/tmp/pkg23-run')
created = desktop.provision(paths, lock)
assert created == [paths.worlds, paths.instance('AresDesktop'), paths.prism_config], created
assert desktop.check_instance(paths, lock) == []
snapshot = {str(p): (os.readlink(p) if p.is_symlink() else p.read_bytes() if p.is_file() else None)
            for p in pathlib.Path('/tmp/pkg23-home').rglob('*')}
assert desktop.provision(paths, lock) == []
assert snapshot == {str(p): (os.readlink(p) if p.is_symlink() else p.read_bytes() if p.is_file() else None)
                    for p in pathlib.Path('/tmp/pkg23-home').rglob('*')}
instance = pathlib.Path(paths.instance('AresDesktop'))
for link in ('patches', 'libraries', 'minecraft/mods'):
    assert os.path.realpath(instance / link).startswith('/usr/share/aresos/minecraft/'), link
assert sorted(os.listdir(instance / 'minecraft/mods')) == ['aresos.jar', 'fabric-api.jar']
assert desktop.check_world(paths, lock)[0] == 'missing'
cfg = instance / 'instance.cfg'
cfg.write_text(cfg.read_text().replace('WrapperCommand=/usr/libexec/aresos-desktop-java', 'WrapperCommand='))
assert desktop.check_instance(paths, lock) == ["instance.cfg WrapperCommand is '', not '/usr/libexec/aresos-desktop-java'"]
print('PROVISIONED', sorted(str(p.relative_to(instance)) for p in instance.rglob('*')))
PY
pass 'provisioning as ares creates the managed instance from the image inputs, is idempotent and reports a changed instance'
# No system unit starts the desktop or Prism: they start inside the everyday session only. What a unit runs is in its
# Exec*= lines (continued lines joined, as systemd joins them); a comment or Documentation= line runs nothing. The one
# exception is package 25's shutdown guard, by its exact path and only as reviewed: its start runs /usr/bin/true, its
# stop asks the session's supervisor to save the home and close the game, and nothing else of it executes, in the unit
# or in a drop-in that applies to it.
python3 -I - /usr/lib/systemd/system /etc/systemd/system <<'SYSTEM_UNITS'
import os
import re
import sys

NAMES = re.compile(r'aresos-desktop|prismlauncher')
EXEC = re.compile(r'Exec[A-Za-z]*\s*=')
GUARD = 'aresos-guardian.service'
GUARD_LINES = ['ExecStart=/usr/bin/true', 'ExecStop=/usr/libexec/aresos-desktop stop --reason shutdown']
# Drop-in folders systemd applies to the guard: its own, its dash prefix's, and every service's.
GUARD_DROP_INS = {GUARD + '.d', 'aresos-.service.d', 'service.d'}


def exec_lines(path):
    with open(path, 'rb') as unit:
        text = unit.read().decode('utf-8', 'replace')
    lines, line = [], ''
    for raw in text.splitlines():
        if raw.lstrip().startswith(('#', ';')):
            continue  # a comment, also one inside a continued line, which systemd skips there too
        if raw.endswith('\\'):
            line += raw[:-1] + ' '
            continue
        lines.append((line + raw).strip())
        line = ''
    lines.append(line.strip())
    return [line for line in lines if EXEC.match(line)]


roots = sys.argv[1:]
guard = os.path.join(roots[0], GUARD)
if os.path.islink(guard):
    sys.exit(f'SYSTEM_UNITS_FAILED {guard} must be a file of its own, not a link')
problems = []
for root in roots:
    for folder, folders, files in os.walk(root):
        folders.sort()
        for name in sorted(files):
            path = os.path.join(folder, name)
            if not os.path.isfile(path):
                continue  # a dangling link or a mask (a link to /dev/null) runs nothing
            lines = exec_lines(path)
            if os.path.realpath(path) == os.path.realpath(guard):
                if sorted(lines) != sorted(GUARD_LINES):
                    problems.append(f'{path}: the shutdown guard runs exactly {GUARD_LINES}, but its Exec lines are '
                                    f'{lines}')
            elif os.path.basename(folder) in GUARD_DROP_INS and lines:
                problems.append(f'{path}: a drop-in adds what the shutdown guard runs: {lines}')
            else:
                problems += [f'{path}: {line}' for line in lines if NAMES.search(line)]
if problems:
    print('A system unit starts the desktop or Prism:', *problems, sep='\n  ')
    sys.exit('SYSTEM_UNITS_FAILED')
print('SYSTEM_UNITS_OK no system unit runs the desktop or Prism; the shutdown guard runs only its two reviewed lines')
SYSTEM_UNITS
pass 'no system service runs the desktop: it starts inside the everyday session only; the shutdown guard only asks it to stop'

# --- Package 30: the icon conversion route must survive base-image updates.
test -x /usr/bin/magick
test -x /usr/bin/bwrap
# Review 1, FIX 2: the converter's address-space ceiling is set by util-linux prlimit.
test -x /usr/bin/prlimit
python3 - <<'PY'
import re, subprocess
formats = subprocess.run(['/usr/bin/magick', '-list', 'format'], check=True, capture_output=True,
                         timeout=3, env={'PATH': '/usr/bin', 'LC_ALL': 'C', 'HOME': '/nonexistent'}).stdout
assert re.search(rb'^\s*SVG\s+SVG\s+r[-w+]+\s+[^\n]*\bRSVG\b', formats, re.MULTILINE), \
    'ImageMagick svg: must use librsvg, never MSVG or an external delegate'
assert re.search(rb'^\s*PNG\*?\s+PNG\s+rw', formats, re.MULTILINE), 'PNG coder missing'
print('ICON_CONVERTER /usr/bin/magick; SVG coder: librsvg (RSVG); bubblewrap present')
PY
pass 'package 30: ImageMagick PNG and librsvg SVG coders, bubblewrap and prlimit exist'

# --- Package 31: the Ares-Crown frame and the defaults for apps' own bars.
python3 - <<'PY'
import hashlib, pathlib, xml.etree.ElementTree as ET
share = pathlib.Path('/usr/share')
theme = share / 'themes/Ares-Crown/labwc'
assert (theme / 'themerc').is_file(), 'Ares-Crown themerc is missing'
# labwc's nine glyphs, including the toggled states, in both focus and hover states.
for button in ('menu', 'iconify', 'max', 'max_toggled', 'close', 'shade', 'shade_toggled', 'desk', 'desk_toggled'):
    for hover in ('', '_hover'):
        for state in ('active', 'inactive'):
            path = theme / f'{button}{hover}-{state}.svg'
            svg = ET.parse(path).getroot()
            assert svg.tag == '{http://www.w3.org/2000/svg}svg', path
            assert (svg.get('width'), svg.get('height')) == ('44', '36'), path
# The reviewed theme, file for file: an empty themerc or an invisible button would pass the shape checks above.
files = sorted(theme.iterdir(), key=lambda p: p.name)
assert len(files) == 37, f'Ares-Crown has {len(files)} files, expected themerc and 36 buttons'
crown = hashlib.sha256('\n'.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}' for p in files).encode()).hexdigest()
assert crown == 'cf01b9b105fc38847e6bf6382056862f3c460d8fc6864cc6d0932794fbd2153e', f'Ares-Crown differs from the reviewed theme: {crown}'
assert not any((share / 'themes' / name).exists() for name in ('Ares-Plain', 'Ares-Block'))
font = share / 'fonts/aresos/SpaceGrotesk-Variable.ttf'
assert hashlib.sha256(font.read_bytes()).hexdigest() == 'acad6de1fc93436f5c0f1f4137751ef04f1aea3063e7036535970ffcfbd79f72'
license = (font.parent / 'OFL-SpaceGrotesk.txt').read_text()
assert 'Copyright 2020 The Space Grotesk Project Authors' in license
assert 'SIL OPEN FONT LICENSE Version 1.1' in license
rc = ET.parse(share / 'aresos/labwc/rc.xml').getroot()
assert rc.findtext('theme/titlebar/layout') == 'menu:iconify,max,close'
assert rc.find('windowSwitcher/osd').get('style') == 'thumbnail'
override = share / 'glib-2.0/schemas/zz-aresos.gschema.override'
assert '[org.gnome.desktop.wm.preferences:AresOS]' in override.read_text()
assert (override.parent / 'gschemas.compiled').is_file()
print('CROWN_FILES_PASSED: the reviewed themerc and 36 button images (pinned), pinned font, licence, rc.xml and schema override')
PY
# A fresh user/home cannot hide a broken compiled default behind a saved setting.
install -d -o ares -g ares -m 0700 /tmp/pkg31-home
layout=$(runuser -u ares -- env -i HOME=/tmp/pkg31-home PATH=/usr/bin:/usr/sbin \
    XDG_CURRENT_DESKTOP=AresOS GSETTINGS_BACKEND=memory \
    /usr/bin/gsettings get org.gnome.desktop.wm.preferences button-layout)
rm -rf /tmp/pkg31-home
printf '%s\n' "$layout"
test "$layout" = "'appmenu:minimize,maximize,close'"
pass 'Ares-Crown files kept unused; compiled AresOS default gives apps all three buttons'

# --- Package 329: look A's window frame.
python3 - <<'PY'
import hashlib
from pathlib import Path
import struct
import xml.etree.ElementTree as ET

share = Path('/usr/share')
theme = share / 'themes/AresOS/labwc'
buttons = ('menu', 'iconify', 'max', 'max_toggled', 'close', 'shade', 'shade_toggled', 'desk', 'desk_toggled')
names = {f'{button}{hover}-{state}.png' for button in buttons
         for hover in ('', '_hover') for state in ('active', 'inactive')}
files = sorted(theme.iterdir(), key=lambda path: path.name)
expected = {'themerc', *names}
actual = {path.name for path in files}
assert actual == expected, f'AresOS theme file list differs: {actual ^ expected}'
tree = []
for path in files:
    data = path.read_bytes()
    if path.name in names:
        assert data[:16] == b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR', path
        assert struct.unpack('>IIBB', data[16:26]) == (48, 40, 8, 6), path
    tree.append(f'{hashlib.sha256(data).hexdigest()}  {path.name}')
aresos_theme = hashlib.sha256('\n'.join(tree).encode()).hexdigest()
assert aresos_theme == '1edd49859255bde9a1c8f4ba779d92010ad38bde0f591507a3b29bbee17d916e', f'AresOS theme differs: {aresos_theme}'

labwc = share / 'aresos/labwc'
assert 'themerc-override' not in {path.name for path in labwc.iterdir()}
rc = ET.parse(labwc / 'rc.xml').getroot()

def expect(path, xml):
    elements = rc.findall(path)
    assert len(elements) == 1, path
    assert ET.canonicalize(ET.tostring(elements[0]), strip_text=True) == ET.canonicalize(xml, strip_text=True), path

expect('theme/name', '<name>AresOS</name>')
expect('theme/cornerRadius', '<cornerRadius>0</cornerRadius>')
places = ('ActiveWindow', 'InactiveWindow', 'MenuHeader', 'MenuItem', 'OnScreenDisplay')
assert len(rc.findall('theme/font')) == len(places)
for place in places:
    expect(f'theme/font[@place="{place}"]', f'<font place="{place}"><name>Jersey 10</name><size>28</size></font>')
expect('windowSwitcher', '''<windowSwitcher preview="yes" outlines="yes" order="focus">
    <osd show="yes" style="thumbnail" output="focused" thumbnailLabelFormat="%T" />
    </windowSwitcher>''')
expect('keyboard/keybind[@key="A-S-Tab"]', '<keybind key="A-S-Tab"><action name="PreviousWindow" /></keybind>')
expect('mouse', '''<mouse>
    <default />
    <context name="TitleBar">
      <mousebind direction="Up" action="Scroll"><action name="None" /></mousebind>
      <mousebind direction="Down" action="Scroll"><action name="None" /></mousebind>
    </context>
    </mouse>''')
PY
pass 'the pinned AresOS theme has 36 RGBA buttons, and labwc selects it with the frame, switcher and scroll settings'

# --- Package 18c: the Control tools (the tool service, its commands, Claude
# Code's managed files). Every path the image records in control.json is here
# with its mode and content, root-owned with root-owned parents and no links,
# and nothing else is under Control's own folders. check-image.sh holds the
# record itself to this checkout and its requirements.lock.
python3 - <<'PY'
import hashlib, json, os, pathlib, re, stat
record = json.loads(pathlib.Path('/usr/share/aresos/manifest/control.json').read_text())
assert record['format'] == 1 and re.fullmatch('[0-9a-f]{40}', record['source_revision']), record.get('source_revision')
assert record['wheels'] and record['vendor'], 'no vendored dependencies recorded'
entries = {**record['files'], **record['vendor'],
           **{name: dict(mode=mode, sha256=None) for name, mode in record['directories'].items()}}
for name, entry in sorted(entries.items()):
    path = pathlib.Path(name)
    for part in (path, *path.parents):
        info = part.lstat()
        assert not stat.S_ISLNK(info.st_mode), f'{part} is a link'
        assert (info.st_uid, info.st_gid) == (0, 0) and not info.st_mode & 0o022, (str(part), oct(info.st_mode))
    info = path.lstat()
    assert f'{stat.S_IMODE(info.st_mode):04o}' == entry['mode'], (name, oct(info.st_mode), entry['mode'])
    if entry['sha256'] is None:
        assert stat.S_ISDIR(info.st_mode), name
    else:
        assert stat.S_ISREG(info.st_mode), name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256'], f'{name} differs from control.json'
for root in ('/usr/libexec/aresos-control', '/usr/lib/aresos-control', '/usr/share/aresos/control', '/etc/claude-code'):
    extra = sorted(str(path) for path in pathlib.Path(root).rglob('*') if str(path) not in entries)
    assert not extra, f'not recorded in control.json: {extra[:20]}'
for link, target in record['links'].items():
    assert os.readlink(link) == target, (link, os.readlink(link))
print(f'CONTROL_FILES_RECORDED {len(record["files"])} files, {len(record["vendor"])} vendored paths, '
      f'{len(record["wheels"])} wheels from {record["source_revision"]}')
PY
pass 'Control: every file, folder and vendored path control.json records is in the image as recorded, root-owned, no links, nothing extra'
# Agreed change 7: Claude Code fixes /etc/claude-code; its two files are the
# image's (recorded above), and there is no exclusive MCP file.
test -f /etc/claude-code/managed-settings.json
test -f /etc/claude-code/CLAUDE.md
test ! -e /etc/claude-code/managed-mcp.json
test ! -L /etc/claude-code/managed-mcp.json
pass 'Claude Code managed files: managed-settings.json and CLAUDE.md as recorded; no managed-mcp.json'

# Agreed change 6: enabled through multi-user.target, Type=simple, and nothing
# else (no login, session, display or recovery unit) requires it, wants it or
# orders itself after it, so a broken service never costs him his session.
test "$(systemctl --root=/ is-enabled aresos-toold.service)" = enabled
grep -qx 'Type=simple' /usr/lib/systemd/system/aresos-toold.service
python3 - <<'PY'
import json, os, pathlib
naming, links = [], []
for root in ('/usr/lib/systemd', '/usr/local/lib/systemd', '/etc/systemd', '/run/systemd'):
    for path in sorted(pathlib.Path(root).rglob('*')) if os.path.isdir(root) else ():
        if path.is_symlink():
            if 'aresos-toold' in path.name + os.readlink(path):
                links.append(str(path))
        elif path.is_file() and b'aresos-toold' in path.read_bytes():
            naming.append(str(path))
# The unit itself need not contain its own name; no other unit file may name it.
assert set(naming) <= {'/usr/lib/systemd/system/aresos-toold.service'}, naming
assert links == ['/etc/systemd/system/multi-user.target.wants/aresos-toold.service'], links
# Agreed change 3: the updater audit of build.sh configure saw the unit and passed it.
rows = [row for row in json.load(open('/usr/share/aresos/manifest/updaters.json'))
        if row['scope'] == 'system' and row['name'] == 'aresos-toold.service']
assert len(rows) == 1 and rows[0]['state'] == 'enabled' and not rows[0]['suspicious'], rows
PY
pass 'aresos-toold.service is enabled by multi-user.target only, Type=simple; no other unit names it; the updater audit saw it'

# Agreed change 5: sysusers makes the service user at boot (it ran above for
# the polkit check, as at boot) with its fixed numbers; nothing else has them.
systemd-sysusers /usr/lib/sysusers.d/aresos-tools.conf
test "$(getent passwd aresos-tools)" = 'aresos-tools:x:250:250:AresOS tool service:/var/lib/aresos-tools:/usr/sbin/nologin'
test "$(getent group aresos-tools | cut -d: -f1-3)" = 'aresos-tools:x:250'
test "$(getent passwd | awk -F: '$3 == 250 || $4 == 250 {print $1}')" = aresos-tools
test "$(getent group | awk -F: '$3 == 250 {print $1}')" = aresos-tools
case $(getent shadow aresos-tools | cut -d: -f2) in '!'* | '*'*) ;; *) echo 'aresos-tools has a password'; exit 1 ;; esac
pass 'aresos-tools: UID and GID 250, no login shell, no password; no other account or group uses 250'

# tmpfiles at boot: the service's runtime and state folders, and his two
# folders (agreed change 11), made when missing and left alone when present.
systemd-tmpfiles --create /usr/lib/tmpfiles.d/aresos-tools.conf /usr/lib/tmpfiles.d/aresos-control-folders.conf
test "$(stat -c '%a %U %G' /run/aresos-tools)" = '711 aresos-tools aresos-tools'
test "$(stat -c '%a %U %G' /var/lib/aresos-tools)" = '700 aresos-tools aresos-tools'
test "$(stat -c '%a %U %G' /var/lib/aresos-operation-evidence)" = '700 aresos-tools aresos-tools'
for folder in Downloads Documents; do
    test "$(stat -c '%a %U %G' "/var/home/ares/$folder")" = '700 ares ares'
done
chmod 0755 /var/home/ares/Downloads
chown root:root /var/home/ares/Documents
systemd-tmpfiles --create /usr/lib/tmpfiles.d/aresos-control-folders.conf
test "$(stat -c '%a %U %G' /var/home/ares/Downloads)" = '755 ares ares'
test "$(stat -c '%a %U %G' /var/home/ares/Documents)" = '700 root root'
chmod 0700 /var/home/ares/Downloads
chown ares:ares /var/home/ares/Documents
pass 'tmpfiles: /run/aresos-tools 0711, both state folders 0700 for aresos-tools; Downloads and Documents 0700 for ares when missing, kept as they are when present'

# Agreed change 7: the config follows the image's own account declaration.
python3 - <<'PY'
import json, pwd
owner = pwd.getpwnam('ares')
service = json.load(open('/usr/share/aresos/control/service.json'))
proxy = json.load(open('/usr/share/aresos/control/proxy.json'))
assert (service['owner_uid'], proxy['home']) == (owner.pw_uid, owner.pw_dir) == (1001, '/var/home/ares'), (service, proxy)
assert proxy['folders'] == ['/var/home/ares/Downloads', '/var/home/ares/Documents'], proxy
assert '_comment' not in service and '_comment' not in proxy
PY
pass 'Control config in /usr/share/aresos/control: owner_uid 1001 and home /var/home/ares are the ares account; folders Downloads and Documents'

# The installed launcher checks its whole tree before it runs anything.
/usr/bin/aresos --help > /tmp/pkg18c-help-root.txt
grep -q '^usage: aresos ' /tmp/pkg18c-help-root.txt
runuser -u ares -- /usr/bin/aresos --help > /tmp/pkg18c-help-ares.txt
cmp /tmp/pkg18c-help-root.txt /tmp/pkg18c-help-ares.txt
/usr/bin/python3 -I -c 'import importlib.util; assert importlib.util.find_spec("mcp") is None, "mcp in site-packages"'
pass "aresos --help runs through the installed launcher as root and as ares; Python's own site-packages has no MCP SDK"

# Agreed change 9: without the CI layer the image trusts no fixture CA and
# names no fixture server. The non-recursive bind mount shows the image's own
# /etc/hosts, not the one podman mounts over it. The same scan must find a
# planted fixture CA and hosts line, or it could not see one.
image_root=$(mktemp -d)
mount --bind / "$image_root"
planted=$(mktemp -d)
mkdir -p "$planted/etc/pki/ca-trust/source/anchors"
printf '10.0.2.2 greenmail dovecot\n' > "$planted/etc/hosts"
openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -keyout /dev/null -days 1 \
    -subj '/CN=mail-fixture.invalid' -out "$planted/etc/pki/ca-trust/source/anchors/fixture.pem" 2> /dev/null
python3 - "$image_root" "$planted" <<'PY'
import pathlib, re, subprocess, sys
# The fixture servers' names and address in the CI guest (control/ci/mail uses mail-fixture.invalid).
FIXTURE = re.compile(r'fixture|\.invalid\b|greenmail|dovecot|badmail', re.I)
PEM = re.compile(rb'-----BEGIN CERTIFICATE-----.+?-----END CERTIFICATE-----', re.S)


def traces(root):
    found = []
    hosts = root / 'etc/hosts'
    for line in (hosts.read_text().splitlines() if hosts.is_file() else []):
        fields = line.split('#', 1)[0].split()
        if fields and (fields[0] == '10.0.2.2' or any(FIXTURE.search(name) for name in fields[1:])):
            found.append(f'hosts: {line}')
    stores = ('etc/pki/ca-trust/source', 'usr/share/pki/ca-trust-source', 'etc/pki/ca-trust/extracted')
    for path in sorted(p for store in stores for p in (root / store).rglob('*') if p.is_file() and not p.is_symlink()):
        data = path.read_bytes()
        names = [subprocess.run(['openssl', 'x509', '-noout', '-subject', '-issuer'], input=pem,
                                capture_output=True).stdout.decode(errors='replace') for pem in PEM.findall(data)]
        # Text outside the certificates (p11-kit labels, comments) is searched as it is.
        names.append(PEM.sub(b'', data).decode(errors='replace') if b'\0' not in data else '')
        found += [f'{path.relative_to(root)}: {name.strip()}' for name in names if FIXTURE.search(name)]
    return found


image, planted = (pathlib.Path(arg) for arg in sys.argv[1:])
assert (image / 'etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem').is_file(), 'no system trust bundle to scan'
assert len(traces(planted)) == 2, traces(planted)
assert traces(image) == [], traces(image)
print('NO_FIXTURE_TRACES: the image trust store and /etc/hosts name no fixture CA or server')
PY
umount "$image_root"
rm -rf "$image_root" "$planted"
pass 'no fixture CA in the trust store and no fixture names in /etc/hosts (a planted fixture CA and hosts line are found)'

set +x
echo IMAGE_CHECKS_PASSED
