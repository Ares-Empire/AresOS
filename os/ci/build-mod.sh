#!/usr/bin/bash
# Builds the AresOS mod jar from this checkout's mod/ in a digest-pinned JDK
# container and checks it against its pin in os/minecraft/desktop.lock.json
# (package 23). The jar is reproducible (mod/build.gradle), so the pin names
# exactly what these sources build. On success it is copied into the image
# build context as os/minecraft/aresos.jar (ignored by git).
#   build-mod.sh          build once, require the pin, copy into the context
#   build-mod.sh --twice  build twice from clean copies, require equal bytes,
#                         print the hash (to set or renew the pin)
set -euo pipefail
mode=${1-}
lock=os/minecraft/desktop.lock.json
builder=$(jq -r '.mods[] | select(.file == "aresos.jar") | .builder' "$lock")
expected=$(jq -r '.mods[] | select(.file == "aresos.jar") | .sha256' "$lock")
version=$(jq -r '.mods[] | select(.file == "aresos.jar") | .version' "$lock")
case $builder in *@sha256:*) ;; *) echo "The mod builder image must be pinned by digest: $builder" >&2; exit 2 ;; esac
test "$(sed -n 's/^version=//p' mod/gradle.properties)" = "$version"
mkdir -p evidence/mod

build() {
    # A clean copy of the committed sources: no local build output or caches.
    local work
    work=$(mktemp -d /tmp/pkg23-mod.XXXXXX)
    git archive HEAD mod | tar -x -C "$work"
    sudo podman run --rm --network=host -v "$work/mod:/src" -w /src -e GRADLE_USER_HOME=/src/.gradle-home \
        "$builder" ./gradlew --no-daemon --console=plain --stacktrace jar > "evidence/mod/build-$1.log" 2>&1 || {
        tail -50 "evidence/mod/build-$1.log" >&2
        exit 1
    }
    sudo cp "$work/mod/build/libs/aresos-$version.jar" "evidence/mod/aresos-$1.jar"
    sudo rm -rf "$work"
    sudo chown "$(id -u):$(id -g)" "evidence/mod/aresos-$1.jar"
    sha256sum "evidence/mod/aresos-$1.jar" | cut -d' ' -f1
}

sudo podman pull "$builder" > /dev/null
first=$(build 1)
echo "Mod jar build 1: $first"
if [[ $mode == --twice ]]; then
    second=$(build 2)
    echo "Mod jar build 2: $second"
    unzip -Z -v "evidence/mod/aresos-1.jar" > evidence/mod/entries.txt
    if [[ $first != "$second" ]]; then
        echo 'The mod jar is not reproducible: two clean builds differ' >&2
        exit 1
    fi
    echo "MOD_JAR_REPRODUCIBLE $first (pinned: $expected)"
    exit 0
fi
if [[ $first != "$expected" ]]; then
    echo "The mod jar built from these sources is $first; desktop.lock.json pins $expected" >&2
    exit 1
fi
cp "evidence/mod/aresos-1.jar" os/minecraft/aresos.jar
echo "MOD_JAR_PINNED $first"
