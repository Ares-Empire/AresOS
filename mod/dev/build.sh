#!/usr/bin/bash
# Builds the AresOS mod on Linux (AresOS laptop): `./gradlew build`, which runs the unit tests and the server game
# tests. Opens no window. Extra arguments go to Gradle.
#
#   mod/dev/build.sh [--force] [gradle arguments...]
#
# Refuses (exit 75) while the owner's Lunar Client game runs or less than 6 GB of memory is available;
# --force skips those two checks. Gradle's --daemon, --foreground, --stop and --status are refused (exit 2). Java 25
# comes from JAVA_HOME or ~/.local/opt/jdk-25 (env.sh).
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/env.sh"

force=0
gradle_args=()
while (($#)); do
    case $1 in
        --force) force=1 ;;
        --) shift; gradle_args+=("$@"); break ;;
        *) gradle_args+=("$1") ;;
    esac
    shift
done
aresos_check_gradle_args "${gradle_args[@]}"

aresos_find_java
aresos_check_room "$force"
aresos_say "Java: $JAVA_HOME"
aresos_scoped build -- "${ARESOS_GRADLE[@]}" build "${gradle_args[@]}"
