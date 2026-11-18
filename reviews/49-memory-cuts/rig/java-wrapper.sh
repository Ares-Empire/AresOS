#!/usr/bin/bash
# DEVELOPMENT AID of package 49 (copied from package 41) (measurement only): installed by run.sh as bin/java of a folder that otherwise links
# to the real JDK, so Gradle takes the folder for a JDK. The game (Loom's dev launcher) runs in a systemd user scope
# of the run's own with MemoryHigh, as package 23's supervisor starts it; anything else (Gradle's probe) runs plainly.
real=${PKG49_REAL_JAVA:?}
game=0
for arg; do
    case $arg in
        *devlaunchinjector*) game=1 ;;
        @*) [[ -r ${arg#@} ]] && grep -q devlaunchinjector -- "${arg#@}" && game=1 ;;
    esac
done
if ((game)); then
    echo "$(date -Is) game: $*" >>"${PKG49_JAVA_LOG:-/dev/null}"
    env_args=()
    IFS=, read -ra settings <<<"${PKG49_GAME_ENV:-}"
    for setting in "${settings[@]}"; do
        [[ $setting =~ ^[A-Za-z_][A-Za-z_0-9]*= ]] || { echo "invalid ENV assignment" >&2; exit 2; }
        # Env is scoped to the JVM. Never allow a setting to redirect it to the owner's display/helper.
        case ${setting%%=*} in
            MALLOC_ARENA_MAX|GLIBC_TUNABLES|JE_MALLOC_CONF) env_args+=("--setenv=$setting") ;;
            *) echo "ENV key not allowed by this rig: ${setting%%=*}" >&2; exit 2 ;;
        esac
    done
    exec /usr/bin/systemd-run --user --scope --collect --quiet --unit="${PKG49_GAME_UNIT:?}" \
        --property=MemoryHigh="${PKG49_MEMORY_HIGH:?}" "${env_args[@]}" -- "$real" "$@"
fi
echo "$(date -Is) other: $*" >>"${PKG49_JAVA_LOG:-/dev/null}"
exec "$real" "$@"
