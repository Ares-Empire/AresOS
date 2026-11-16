#!/usr/bin/bash
# DEVELOPMENT AID of package 41 (measurement only): installed by run.sh as bin/java of a folder that otherwise links
# to the real JDK, so Gradle takes the folder for a JDK. The game (Loom's dev launcher) runs in a systemd user scope
# of the run's own with MemoryHigh, as package 23's supervisor starts it; anything else (Gradle's probe) runs plainly.
real=${PKG41_REAL_JAVA:?}
game=0
for arg; do
    case $arg in
        *devlaunchinjector*) game=1 ;;
        @*) [[ -r ${arg#@} ]] && grep -q devlaunchinjector -- "${arg#@}" && game=1 ;;
    esac
done
if ((game)); then
    echo "$(date -Is) game: $*" >>"${PKG41_JAVA_LOG:-/dev/null}"
    exec /usr/bin/systemd-run --user --scope --collect --quiet --unit="${PKG41_GAME_UNIT:?}" \
        --property=MemoryHigh="${PKG41_MEMORY_HIGH:?}" -- "$real" "$@"
fi
echo "$(date -Is) other: $*" >>"${PKG41_JAVA_LOG:-/dev/null}"
exec "$real" "$@"
