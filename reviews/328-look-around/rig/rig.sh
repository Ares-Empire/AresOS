#!/usr/bin/bash
# Package 328 rig: a private headless labwc with the image's rc.xml and two outputs side by side, on a private D-Bus.
# Never the owner's session: the compositor is headless with its own Wayland socket and Xwayland display; inner.sh
# refuses wayland-0 and :0. Everything runs in one systemd user scope, pkg328-rig-<pid>; stop.sh stops it.
#
#   rig.sh <run folder>     (blocks until the rig stops; start it in the background)
#
# TRACE=1 sets WAYLAND_DEBUG=client on labwc only, so the Xwayland it starts logs every Wayland message it sends and
# gets (pointer focus, locks, confinements, buttons) into <run folder>/labwc.log. inner.sh unsets it for the rest.
set -euo pipefail
RIG=${1:?usage: rig.sh <run folder>}
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
WT=$(cd -- "$here/../../.." && pwd)
RIG=$(/usr/bin/realpath -m -- "$RIG")
/usr/bin/mkdir -p -- "$RIG/labwc"
/usr/bin/rm -f -- "$RIG/env" "$RIG/vinput.sock"
/usr/bin/cp -- "$WT/os/config/usr/share/aresos/labwc/rc.xml" "$RIG/labwc/rc.xml"
node=
for n in /sys/class/drm/renderD*; do
    [[ -r $n/device/vendor && $(<"$n/device/vendor") == 0x10de ]] && { node=/dev/dri/${n##*/}; break; }
done
render=(WLR_RENDERER=pixman)
[[ -z $node ]] || render=(WLR_RENDER_DRM_DEVICE="$node")
trace=()
[[ ${TRACE:-0} != 1 ]] || trace=(WAYLAND_DEBUG=client)
exec /usr/bin/systemd-run --user --scope --collect --quiet --unit="pkg328-rig-$$" -- \
    /usr/bin/env -u DISPLAY -u WAYLAND_DISPLAY -u WAYLAND_SOCKET -u ARESOS_LAUNCH_NONCE -u ARESOS_DESKTOP_INSTANCE \
    -u ARESOS_SHELL_SOCKET -u DBUS_SESSION_BUS_ADDRESS -u LABWC_PID \
    /usr/bin/dbus-run-session -- /usr/bin/env WLR_BACKENDS=headless WLR_HEADLESS_OUTPUTS=2 WLR_LIBINPUT_NO_DEVICES=1 \
    LABWC_UPDATE_ACTIVATION_ENV=0 "${render[@]}" "${trace[@]}" RIG="$RIG" WT="$WT" \
    /usr/bin/labwc -C "$RIG/labwc" -s "$here/inner.sh" >"$RIG/labwc.log" 2>&1
