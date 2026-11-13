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

# --- The everyday account: wheel, a password it does not have yet.
systemd-tmpfiles --create /usr/lib/tmpfiles.d/aresos.conf
test -d /var/home/ares
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
    /usr/libexec/aresos-desktop /usr/libexec/aresos-desktop-java /usr/share/aresos/desktop-view.bashrc) | sort -u)
for command in /usr/bin/dbus-run-session /usr/bin/dbus-daemon /usr/bin/labwc /usr/bin/busctl /usr/bin/foot \
    /usr/libexec/aresos-shell /usr/bin/systemd-run /usr/bin/systemctl /usr/bin/kwrite /usr/bin/google-chrome \
    /usr/libexec/aresos-desktop /usr/libexec/aresos-desktop-java /usr/bin/prismlauncher /usr/bin/python3 /usr/bin/cat; do
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
assert hints == {'lunarclient.desktop': shell.Hint('lunarclient.desktop', ('com.mojang.minecraft',), ()),
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
grep -qx '/usr/libexec/kf6/polkit-kde-authentication-agent-1 &' /usr/share/aresos/labwc/autostart
test -x /usr/libexec/kf6/polkit-kde-authentication-agent-1
rpm -qf /usr/libexec/kf6/polkit-kde-authentication-agent-1
pass 'the labwc session starts the base image polkit agent'
python3 - <<'PY'
import os, xml.etree.ElementTree as ET
root = ET.parse('/usr/share/aresos/labwc/rc.xml').getroot()
binds = {b.get('key'): b.find('action').get('command') for b in root.iter('keybind')}
library = open(next(p for p in ('/usr/lib64/libxkbcommon.so.0',) if os.path.exists(p)), 'rb').read()
for key in ('XF86MonBrightnessUp', 'XF86MonBrightnessDown', 'XF86AudioRaiseVolume', 'XF86AudioLowerVolume',
            'XF86AudioMute', 'XF86AudioMicMute'):
    command = binds[key].split()
    assert os.access(command[0], os.X_OK), (key, command)
    assert b'\0' + key.encode() + b'\0' in library, f'{key} is not a keysym name libxkbcommon knows'
    print(key, '->', ' '.join(command))
assert binds['W-C-Escape'] == '/usr/bin/aresos-terminal --recovery'
PY
pass 'brightness, volume, mute and mic-mute keys are bound to brightnessctl and wpctl; recovery terminal kept'
for command in script qrencode brightnessctl wpctl; do
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
if grep -rlE 'aresos-desktop|prismlauncher' /usr/lib/systemd/system /etc/systemd/system 2>/dev/null | grep .; then
    echo 'A system unit starts the desktop'
    exit 1
fi
pass 'no system service runs the desktop: it starts inside the everyday session only'

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

set +x
echo IMAGE_CHECKS_PASSED
