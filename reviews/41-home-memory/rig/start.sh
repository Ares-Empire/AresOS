#!/usr/bin/bash
# DEVELOPMENT AID of package 41 (measurement only), headless use only: package 40's rig (reviews/40-real-home/rig/)
# made to measure. Like that rig it calls Gradle itself (inner.sh runs `gradlew --no-daemon runClient`), inside a
# systemd user scope of its own, under the one-client-at-a-time lock, after mod/dev/env.sh's memory and Lunar checks.
#
# Starts a headless labwc (its own Wayland socket and Xwayland, never the owner's wayland-0 or :0) with the image's
# rc.xml; inside it inner.sh starts the restricted app helper, a virtual keyboard and pointer, and the development
# client. run.sh drives it; it sets every variable below.
#   RIG   the run's scratch folder (env, logs, frames, gc log)
#   APPS  the test apps (make-apps.py), HOMEDIR the helper's home folder
#   SIZE, REFRESH  the headless screen (1920x1080, 144)
#   PKG41_JVM_ARGS, PKG41_JAVA, PKG41_GAME_UNIT, PKG41_MEMORY_HIGH, GAME_ARGS  for the game (jvm41.gradle, jdk/bin/java)
set -u
export WT=$(cd -- "$(dirname -- "$0")/../../.." && pwd)
: "${RIG:?}" "${APPS:?}" "${HOMEDIR:?}" "${SIZE:?}" "${REFRESH:?}" "${PKG41_GAME_UNIT:?}"
export RIG APPS HOMEDIR SIZE REFRESH
mkdir -p "$RIG/labwc"
cp -- "$WT/os/config/usr/share/aresos/labwc/rc.xml" "$RIG/labwc/rc.xml"
here=$(cd -- "$(dirname -- "$0")" && pwd)
source "$WT/mod/dev/env.sh"
aresos_find_java
aresos_check_room 0
exec 9>>"$ARESOS_CLIENT_TEST_LOCK"
echo "waiting for $ARESOS_CLIENT_TEST_LOCK" >"$RIG/lock"
/usr/bin/flock 9
echo "holding $ARESOS_CLIENT_TEST_LOCK since $(date -Is)" >"$RIG/lock"
# The lock wait may have been long: check memory and Lunar again right before the game.
aresos_check_room 0
node=
for n in /sys/class/drm/renderD*; do
    [[ -r $n/device/vendor && $(<"$n/device/vendor") == 0x10de ]] && { node=/dev/dri/${n##*/}; break; }
done
[[ -n $node ]] || { echo "no NVIDIA render node" >&2; exit 1; }
exec /usr/bin/env -u DISPLAY -u WAYLAND_DISPLAY -u WAYLAND_SOCKET -u ARESOS_LAUNCH_NONCE -u ARESOS_DESKTOP_INSTANCE \
    -u ARESOS_SHELL_SOCKET WLR_BACKENDS=headless WLR_LIBINPUT_NO_DEVICES=1 WLR_RENDER_DRM_DEVICE="$node" \
    /usr/bin/systemd-run --user --scope --collect --quiet --unit="pkg41-rig-$$" -- \
    /usr/bin/labwc -C "$RIG/labwc" -s "$here/inner.sh" >"$RIG/labwc.txt" 2>&1
