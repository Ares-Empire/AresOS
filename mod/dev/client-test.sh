#!/usr/bin/bash
# Runs the mod's client game tests (`./gradlew runClientGameTest`) on Linux (AresOS laptop) without a window on the
# owner's screen. Extra arguments go to Gradle.
#
#   mod/dev/client-test.sh [--force] [--keep-screenshots <dir>] [--gpu auto|nvidia|intel|software] [gradle args...]
#
# - The game runs inside its own headless Wayland compositor (cage with WLR_BACKENDS=headless) and that
#   compositor's own Xwayland (Minecraft asks GLFW for X11). DISPLAY and WAYLAND_DISPLAY point there only, so
#   the game cannot reach the owner's display. It gets no input but the tests' own, and its sound goes to
#   OpenAL's null device. The AresOS launch variables are removed, so it can never reach a real app helper.
# - Rendering: the RTX 4060 (PRIME render offload) if it works headless, else the Intel GPU, else software.
#   --gpu picks one instead of trying them in that order.
# - One run at a time on the laptop: it waits for ~/.cache/aresos-dev/client-test.lock and says so.
# - Refuses (exit 75) while the owner's Lunar Client game runs or less than 6 GB of memory is available;
#   --force skips those two checks (not the lock).
# - Every exit stops the compositor, the game and Gradle's daemon (env.sh: one systemd user scope).
# - The tests rewrite tracked screenshots under reviews/. --keep-screenshots copies the ones this run wrote into
#   <dir> (paths kept) before you undo them with `git checkout -- ../reviews/` from mod/.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/env.sh"

usage="usage: client-test.sh [--force] [--keep-screenshots <dir>] [--gpu auto|nvidia|intel|software] [gradle args...]"
force=0
keep=
gpu=auto
gradle_args=()
while (($#)); do
    case $1 in
        --force) force=1 ;;
        --keep-screenshots)
            (($# >= 2)) || aresos_fail 2 "--keep-screenshots needs a directory; $usage"
            keep=$2
            shift ;;
        --gpu)
            (($# >= 2)) || aresos_fail 2 "--gpu needs auto, nvidia, intel or software; $usage"
            gpu=$2
            shift ;;
        --) shift; gradle_args+=("$@"); break ;;
        *) gradle_args+=("$1") ;;
    esac
    shift
done
case $gpu in auto | nvidia | intel | software) ;; *) aresos_fail 2 "--gpu must be auto, nvidia, intel or software." ;; esac
if [[ -n $keep && $keep != /* ]]; then keep="$ARESOS_CALLER_DIR/$keep"; fi

REPO_DIR=$(cd -- "$ARESOS_MOD_DIR/.." && pwd -P)
COMPOSITOR_LOG="$ARESOS_DEV_CACHE/client-test-compositor.log"
GAME_LOG="$ARESOS_MOD_DIR/build/run/clientGameTest/logs/latest.log"
stamp=

aresos_find_java
aresos_check_room "$force"

/usr/bin/mkdir -p -- "$ARESOS_DEV_CACHE"
aresos_lock "$ARESOS_CLIENT_TEST_LOCK" "another client test run on this laptop"
# The wait can be long: the owner may have started his game meanwhile.
[[ $ARESOS_LOCK_WAITED == 0 ]] || aresos_check_room "$force"

# The render node (/dev/dri/renderD*) of the first GPU from this PCI vendor (0x10de NVIDIA, 0x8086 Intel).
render_node() {
    local node
    for node in /sys/class/drm/renderD*; do
        if [[ -r $node/device/vendor && $(<"$node/device/vendor") == "$1" ]]; then
            printf '/dev/dri/%s\n' "${node##*/}"
            return 0
        fi
    done
    return 1
}

# Sets compositor_env (the headless compositor's renderer, which Xwayland renders with too) and game_env for a
# mode, and expected (what its OpenGL renderer string contains). Fails when this laptop has no such GPU.
gpu_settings() {
    local node
    case $1 in
        nvidia)
            node=$(render_node 0x10de) || return 1
            compositor_env=(WLR_RENDER_DRM_DEVICE="$node")
            game_env=("${ARESOS_NVIDIA_OFFLOAD[@]}")
            expected=NVIDIA ;;
        intel)
            node=$(render_node 0x8086) || return 1
            compositor_env=(WLR_RENDER_DRM_DEVICE="$node")
            game_env=(__GLX_VENDOR_LIBRARY_NAME=mesa __VK_LAYER_NV_optimus=non_NVIDIA_only)
            expected=Intel ;;
        software)
            compositor_env=(WLR_RENDERER=pixman)
            game_env=(LIBGL_ALWAYS_SOFTWARE=1 __GLX_VENDOR_LIBRARY_NAME=mesa)
            expected=llvmpipe ;;
    esac
}

# Everything that would let the game reach the owner's display or a real AresOS app helper.
ISOLATE=(-u DISPLAY -u WAYLAND_DISPLAY -u WAYLAND_SOCKET -u ARESOS_LAUNCH_NONCE -u ARESOS_DESKTOP_INSTANCE
         -u ARESOS_SHELL_SOCKET WLR_BACKENDS=headless)

# Prints the OpenGL renderer a game would get in this mode's headless compositor; fails if it is not the
# expected GPU. Without glxinfo the mode is taken on trust and the game log shows what it got.
probe() {
    local out
    [[ -x /usr/bin/glxinfo ]] || { printf 'unchecked (no glxinfo)\n'; return 0; }
    out=$(/usr/bin/env "${ISOLATE[@]}" "${compositor_env[@]}" /usr/bin/timeout 30 /usr/bin/cage -- \
        /usr/bin/env "${game_env[@]}" /usr/bin/glxinfo -B 2>/dev/null) || true
    [[ $out =~ OpenGL\ renderer\ string:\ ([^$'\n']*) ]] || return 1
    printf '%s\n' "${BASH_REMATCH[1]}"
    [[ ${BASH_REMATCH[1]} == *"$expected"* ]]
}

renderer=
modes=(nvidia intel software)
[[ $gpu == auto ]] || modes=("$gpu")
for mode in "${modes[@]}"; do
    if gpu_settings "$mode" && renderer=$(probe); then
        gpu=$mode
        break
    fi
    aresos_say "Headless rendering on $mode does not work here${renderer:+ (got $renderer)}."
    renderer=
done
[[ -n $renderer ]] || aresos_fail 1 "No headless rendering works on this laptop; not running the client tests (they would need the owner's screen)."
aresos_say "Rendering headless on $gpu: $renderer"

started=$SECONDS
aresos_cleanup() {
    local status=$1 seconds=$((SECONDS - started))
    if [[ -n $keep && -n $stamp ]]; then
        /usr/bin/mkdir -p -- "$keep"
        # What this run wrote: the tracked review screenshots and the untracked ones under build/.
        (cd -- "$REPO_DIR" && /usr/bin/find reviews mod/build/review mod/build/run/clientGameTest/screenshots \
            -type f -newer "$stamp" -exec /usr/bin/cp --parents -t "$keep" -- {} + 2>/dev/null) || true
        aresos_say "Copied this run's screenshots to $keep"
    fi
    # What the game itself reported, which the probe can only predict.
    if [[ -n $stamp && $GAME_LOG -nt $stamp ]]; then
        device=$(/usr/bin/grep -m1 -o 'Using graphics device: .*' "$GAME_LOG" || true)
        [[ -z $device ]] || renderer=${device#Using graphics device: }
    fi
    [[ -z $stamp ]] || /usr/bin/rm -f -- "$stamp"
    aresos_say "Client tests ended with exit code $status after $((seconds / 60)) min $((seconds % 60)) s ($gpu: $renderer)."
    aresos_say "Compositor log: $COMPOSITOR_LOG"
    aresos_say "The tests rewrote tracked screenshots; to undo, run from mod/: git checkout -- ../reviews/"
    aresos_say "Screenshots with new numbers stay untracked; git status --short -- ../reviews/ lists them."
}

stamp=$(/usr/bin/mktemp -- "$ARESOS_DEV_CACHE/client-test-started.XXXXXX")
# Gradle and the game keep the terminal's stderr (fd 3 inside); only the compositor's own log goes to the file.
aresos_scoped aresos-dev-client-test /usr/bin/env "${ISOLATE[@]}" "${compositor_env[@]}" /usr/bin/cage -- \
    /usr/bin/env "${game_env[@]}" ALSOFT_DRIVERS=null \
    /usr/bin/bash -c 'exec 2>&3 3>&-; exec "$@"' client-test "${ARESOS_GRADLE[@]}" runClientGameTest "${gradle_args[@]}" \
    3>&2 2>"$COMPOSITOR_LOG"
