#!/bin/bash
# DEVELOPMENT AID of package 40, headless use only: this rig calls Gradle directly (inner.sh runs gradlew runClient).
# Package 40 reproduction rig: a headless labwc with an rc.xml of choice, the worktree's helper and the dev client.
# Never the owner's session: the compositor is headless and gets its own socket; inner.sh refuses wayland-0 / :0.
set -u
export WT=$(cd -- "$(dirname -- "$0")/../../.." && pwd)
export RIG=${RIG:?set RIG to a run folder}
export HELPER=${HELPER:-$WT/os/config/usr/libexec/aresos-shell}
export REGISTRY=${REGISTRY:-$WT/os/config/usr/share/aresos/apps}
export GAME_ARGS=${GAME_ARGS:-}
mkdir -p "$RIG/labwc" "$RIG/home/.local/share/applications" "$RIG/home/.local/opt/testapp" "$RIG/home/.local/bin"
# The rig's own program, from a user desktop entry whose Exec is an absolute path through a symlink (as in B).
# $RIG/testapp.mode picks what it does: same (a window with the desktop ID), other (another ID), none, exit0, exit1.
cat >"$RIG/home/.local/opt/testapp/testapp" <<TESTAPP
#!/bin/bash
case \$(cat "$RIG/testapp.mode" 2>/dev/null || echo same) in
  same)  exec /usr/bin/foot --app-id=pkg40.TestApp --title="Test app" -e /usr/bin/sleep 900 ;;
  other) exec /usr/bin/foot --app-id=other-identity --title="Test app" -e /usr/bin/sleep 900 ;;
  none)  exec /usr/bin/sleep 900 ;;
  exit0) exit 0 ;;
  exit1) exit 1 ;;
esac
TESTAPP
chmod +x "$RIG/home/.local/opt/testapp/testapp"
ln -sfn "$RIG/home/.local/opt/testapp/testapp" "$RIG/home/.local/bin/testapp"
printf '%s\n' '[Desktop Entry]' 'Categories=Utility;' "Exec=$RIG/home/.local/bin/testapp" 'Icon=pkg40.TestApp' \
    'Name=Test App' 'Terminal=false' 'Type=Application' >"$RIG/home/.local/share/applications/pkg40.TestApp.desktop"
cp -- "${RC:-$WT/os/config/usr/share/aresos/labwc/rc.xml}" "$RIG/labwc/rc.xml"
here=$(cd -- "$(dirname -- "$0")" && pwd)
source "$WT/mod/dev/env.sh"
aresos_find_java
aresos_check_room 0
exec 9>>"$ARESOS_CLIENT_TEST_LOCK"
/usr/bin/flock 9
node=
for n in /sys/class/drm/renderD*; do
    [[ -r $n/device/vendor && $(<"$n/device/vendor") == 0x10de ]] && { node=/dev/dri/${n##*/}; break; }
done
[[ -n $node ]] || { echo "no NVIDIA render node" >&2; exit 1; }
exec /usr/bin/env -u DISPLAY -u WAYLAND_DISPLAY -u WAYLAND_SOCKET -u ARESOS_LAUNCH_NONCE -u ARESOS_DESKTOP_INSTANCE \
    -u ARESOS_SHELL_SOCKET WLR_BACKENDS=headless WLR_LIBINPUT_NO_DEVICES=1 WLR_RENDER_DRM_DEVICE="$node" \
    /usr/bin/systemd-run --user --scope --collect --quiet --unit="pkg40-rig-$$" -- \
    /usr/bin/labwc -C "$RIG/labwc" -s "$here/inner.sh" >"$RIG/labwc.log" 2>&1
