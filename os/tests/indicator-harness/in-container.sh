#!/usr/bin/bash
# The isolation gate comes from package 316. stdout carries only the evidence archive.
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

# Podman's virtual files and container-generated identity files are the only mounts.
only_container_mounts() {
    awk '$5 !~ /^(\/|\/proc(\/.*)?|\/dev(\/pts(\/.*)?|\/shm|\/mqueue|\/(null|zero|full|tty|random|urandom))?|\/sys(\/.*)?|\/etc\/(hostname|hosts|resolv.conf)|\/run\/(\.containerenv|secrets))$/ {
        print "unexpected mount: " $5 > "/dev/stderr"; bad=1
    } END {exit bad}' /proc/self/mountinfo
}
must "only Podman container mounts" only_container_mounts
must "no container secrets" absent_or_empty /run/secrets
for var in DBUS_SYSTEM_BUS_ADDRESS LD_PRELOAD GDK_BACKEND; do
    must "the container starts without $var" unset_var "$var"
done

run_isolated() (
    set -e
    HOME=$(mktemp -d /tmp/indicator-home.XXXXXX)
    XDG_RUNTIME_DIR=$(mktemp -d /tmp/indicator-run.XXXXXX)
    chmod 0700 "$XDG_RUNTIME_DIR"
    export HOME XDG_RUNTIME_DIR
    export XDG_CONFIG_HOME=$HOME/.config XDG_DATA_HOME=$HOME/.local/share XDG_CACHE_HOME=$HOME/.cache \
        XDG_STATE_HOME=$HOME/.local/state STANDIN_DIR=$HOME/standins GDK_BACKEND=wayland GTK_A11Y=none
    mkdir -p "$XDG_CONFIG_HOME/labwc" "$STANDIN_DIR"
    cp -- /harness/rc.xml "$XDG_CONFIG_HOME/labwc/rc.xml"
    install -m 0755 /harness/os/config/usr/libexec/aresos-{indicator,level,settings} /usr/libexec/
    install -D -m 0644 /harness/Jersey10-Regular.ttf /usr/share/fonts/aresos/Jersey10-Regular.ttf
    install -d /usr/share/aresos
    cp -r /harness/look /usr/share/aresos/
    cp -r /harness/AresOS /usr/share/themes/
    local driver=driver.py
    if [[ $1 == frame ]]; then
        cp -r /harness/baseline/Ares-Crown /usr/share/themes/
        install -m 0644 /harness/baseline/SpaceGrotesk-Variable.ttf /usr/share/fonts/aresos/
        driver=frame.py
    fi
    fc-cache /usr/share/fonts/aresos
    python3 -I /harness/install_standins.py
    grep -q ARESOS-TEST-STAND-IN /usr/bin/brightnessctl
    grep -q ARESOS-TEST-STAND-IN /usr/bin/wpctl
    grep -q ARESOS-TEST-STAND-IN /usr/bin/pw-dump
    {
        cat /harness/harness-image.txt
        rpm -q labwc wlroots0.19 gtk4 gtk4-layer-shell python3-gobject python3-cairo pango grim python3-pillow
        sha256sum /opt/harness/rpm/*.rpm
        sha256sum /usr/libexec/aresos-{indicator,level,settings} /usr/share/fonts/aresos/Jersey10-Regular.ttf
        fc-match 'Jersey 10'
        if [[ $1 == frame ]]; then
            cat /harness/merge-base.txt
            sha256sum /harness/{rc.xml,baseline/rc.xml} /usr/share/themes/{AresOS,Ares-Crown}/labwc/themerc
            fc-match 'Space Grotesk'
        fi
        python3 -IB /harness/check_labwc.py
    } > "$EV/versions.txt"
    cat "$EV/versions.txt"
    cat > "$XDG_RUNTIME_DIR/bus.conf" <<XML
<busconfig>
  <type>session</type>
  <listen>unix:tmpdir=$XDG_RUNTIME_DIR</listen>
  <policy context="default"><allow send_destination="*"/><allow receive_sender="*"/><allow own="*"/></policy>
</busconfig>
XML
    exec timeout 270 /usr/bin/dbus-run-session --config-file="$XDG_RUNTIME_DIR/bus.conf" --dbus-daemon=/usr/bin/dbus-daemon -- \
        /usr/bin/python3 -IB "/harness/$driver"
)

if [ "$fail" -ne 0 ]; then
    echo "UNUSABLE the container is not isolated; nothing was tested" | tee "$EV/results.txt"
    code=2
else
    run_isolated "$1"
    code=$?
fi
echo "$code" > "$EV/exit-code"
tar -cf - -C "$EV" . >&3
exit "$code"
