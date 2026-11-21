#!/usr/bin/bash
# Package 316's harness (and 321's checks), inside its container (harness/run.sh starts it). Checks that the container is cut off
# from the host, makes the scratch session folders, installs the backend into the container's own /usr and
# hands over to driver.py. stdout is the evidence archive; everything readable goes to stderr.
set -uo pipefail
exec 3>&1 1>&2

EV=/evidence
mkdir -p "$EV"

# ---- isolation first: before anything is set or started -----------------------------------------------------
env | sort > "$EV/isolation-start-env.txt"
# Every mount point with its filesystem type (the sources are podman's own storage paths on the host).
awk '{ for (i = 1; i <= NF; i++) if ($i == "-") { print $5, $(i + 1); break } }' /proc/self/mountinfo \
    > "$EV/isolation-mounts.txt"

fail=0
must() { # must <what> <command...>
    local what=$1
    shift
    if "$@" >/dev/null 2>&1; then
        echo "PASS isolation $what" | tee -a "$EV/isolation.txt"
    else
        echo "FAIL isolation $what" | tee -a "$EV/isolation.txt"
        fail=1
    fi
}
unset_var() { [ -z "${!1:-}" ]; }
absent_or_empty() { [ ! -e "$1" ] || { [ -d "$1" ] && [ -z "$(ls -A -- "$1")" ]; }; }
only_loopback() { [ "$(ls /sys/class/net | tr '\n' ' ')" = "lo " ]; }
no_sockets() { [ -z "$(find / \( -path /proc -o -path /sys \) -prune -o -type s -print 2>/dev/null)" ]; }
no_host_mount() { # passes only when grep read the table and found no match (1); a match (0) or an error (2) fails
    local status=0
    grep -Eq ' /(home|var/home|run/user|tmp/\.X11-unix)(/| )' /proc/self/mountinfo || status=$?
    [ "$status" -eq 1 ]
}

for var in WAYLAND_DISPLAY DISPLAY DBUS_SESSION_BUS_ADDRESS XDG_RUNTIME_DIR XDG_DESKTOP_PORTAL_DIR \
    XDG_CURRENT_DESKTOP XAUTHORITY SSH_AUTH_SOCK; do
    must "the container starts without $var" unset_var "$var"
done
must "no network interface but loopback (its own network namespace: no abstract socket of the host)" only_loopback
for path in /dev/input /dev/uinput /dev/dri /tmp/.X11-unix /run/user /run/dbus /var/run/dbus /home /var/home; do
    must "no $path, or an empty one" absent_or_empty "$path"
done
must "no socket exists anywhere before the harness starts one" no_sockets
must "no host home, runtime or X11 folder is mounted" no_host_mount

# ---- the scratch session ------------------------------------------------------------------------------------
HOME=$(mktemp -d /tmp/harness-home.XXXXXX)
XDG_RUNTIME_DIR=$(mktemp -d /tmp/harness-run.XXXXXX)
chmod 0700 "$XDG_RUNTIME_DIR"
export HOME XDG_RUNTIME_DIR
export XDG_CONFIG_HOME=$HOME/.config XDG_DATA_HOME=$HOME/.local/share XDG_CACHE_HOME=$HOME/.cache \
    XDG_STATE_HOME=$HOME/.local/state
mkdir -p "$XDG_CONFIG_HOME/labwc" "$XDG_DATA_HOME" "$XDG_CACHE_HOME" "$XDG_STATE_HOME"

# labwc's bindings (brief 321, "What to build" 6). The two marked allowWhenInhibited are the only ones that may run
# while the backend's capture surface holds the keyboard: the way out, and the recovery terminal with the way out as
# its first action (/harness/binding stands in for the terminal). The others are the image's own unmarked kinds
# (close, the window switcher, media keys, a lone Super that acts on release) and two mouse bindings that apply in
# every context, so also over the capture surface. Step 3 gives the image's rc.xml the same two marks.
cat > "$XDG_CONFIG_HOME/labwc/rc.xml" <<'XML'
<?xml version="1.0"?>
<labwc_config>
  <keyboard>
    <keybind key="W-S-Escape" allowWhenInhibited="yes">
      <action name="Execute" command="/usr/libexec/aresos-input-portal --release" />
    </keybind>
    <keybind key="W-C-Escape" allowWhenInhibited="yes">
      <action name="Execute" command="/usr/libexec/aresos-input-portal --release" />
      <action name="Execute" command="/harness/binding recovery-terminal" />
    </keybind>
    <keybind key="A-F4"><action name="Close" /></keybind>
    <keybind key="A-Tab"><action name="NextWindow" /></keybind>
    <keybind key="XF86AudioRaiseVolume"><action name="Execute" command="/harness/binding volume-up" /></keybind>
    <keybind key="XF86AudioMute"><action name="Execute" command="/harness/binding mute" /></keybind>
    <keybind key="XF86MonBrightnessUp"><action name="Execute" command="/harness/binding brightness-up" /></keybind>
    <keybind key="Super_L" onRelease="yes"><action name="Execute" command="/harness/binding lone-super" /></keybind>
  </keyboard>
  <mouse>
    <default />
    <context name="All">
      <mousebind button="A-Middle" action="Press"><action name="Execute" command="/harness/binding mouse-press" /></mousebind>
      <mousebind direction="A-Down" action="Scroll"><action name="Execute" command="/harness/binding mouse-scroll" /></mousebind>
    </context>
  </mouse>
</labwc_config>
XML
cp "$XDG_CONFIG_HOME/labwc/rc.xml" "$EV/labwc-rc.xml"
# What the test bindings run: one line per run, so the driver sees which binding acted and how often.
cat > /harness/binding <<'SH'
#!/usr/bin/bash
echo "$1" >> /evidence/bindings.log
SH
chmod 0755 /harness/binding
: > "$EV/bindings.log"

# The backend and its allow-list, where the image will have them: in this container's own /usr.
install -D -m 0755 /harness/backend/aresos-input-portal /usr/libexec/aresos-input-portal
install -d -m 0755 /usr/share/aresos/input-portal
printf '# the harness\norg.aresos.harness\n' > /usr/share/aresos/input-portal/allowed-apps
chmod 0644 /usr/share/aresos/input-portal/allowed-apps
# The sharing switch (brief 321), on, as the owner's password leaves it: root's file in root's folders, where
# the image's helper writes it. Every test but the switch's own runs with it on.
install -d -m 0755 /etc/aresos /etc/aresos/input-portal
printf 'on\n' > /etc/aresos/input-portal/sharing
chmod 0644 /etc/aresos/input-portal/sharing

{
    rpm -q labwc
    sha256sum /opt/harness/rpm/*.rpm
    sha256sum /usr/libexec/aresos-input-portal
    rpm -q wlroots0.19 libei dbus-daemon wl-clipboard wlr-randr
    stat -c '%A %u:%g %n' / /etc /etc/aresos /etc/aresos/input-portal /etc/aresos/input-portal/sharing
} > "$EV/versions.txt" 2>&1
cat "$EV/versions.txt"

if [ "$fail" -ne 0 ]; then
    echo "UNUSABLE the container is not isolated; nothing was tested" | tee -a "$EV/results.txt"
    code=2
else
    timeout 840 python3 -I /harness/driver.py
    code=$?
fi
echo "$code" > "$EV/exit-code"
tar -cf - -C "$EV" . >&3
exit "$code"
