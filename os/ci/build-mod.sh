#!/usr/bin/bash
# Sets or renews the AresOS mod jar's pin in os/minecraft/desktop.lock.json
# (package 23). Every image build already builds the jar from its own commit
# (the Containerfile's mod stage runs `build.sh mod`) and refuses other bytes;
# this runs that same `build.sh mod` twice for this checkout's pushed commit in
# the pinned JDK image, requires equal bytes, and prints the hash to pin.
#   build-mod.sh --twice
set -euo pipefail
if [[ ${1-} != --twice ]]; then
    echo 'usage: build-mod.sh --twice   (image builds build the jar themselves)' >&2
    exit 2
fi
lock=os/minecraft/desktop.lock.json
builder=$(jq -r '.mods[] | select(.file == "aresos.jar") | .builder' "$lock")
expected=$(jq -r '.mods[] | select(.file == "aresos.jar") | .sha256' "$lock")
version=$(jq -r '.mods[] | select(.file == "aresos.jar") | .version' "$lock")
case $builder in *@sha256:*) ;; *) echo "The mod builder image must be pinned by digest: $builder" >&2; exit 2 ;; esac
test "$(sed -n 's/^version=//p' mod/gradle.properties)" = "$version"
test "$(awk '$1 == "FROM" && $NF == "mod" {print $2}' os/Containerfile)" = "$builder"
revision=$(git rev-parse HEAD)
mkdir -p evidence/mod
sudo podman pull "$builder" > /dev/null
hashes=()
for run in 1 2; do
    out=$(mktemp -d /tmp/pkg23-mod.XXXXXX)
    sudo podman run --rm --network=host -v "$PWD/os/build.sh:/tmp/build.sh:ro" -v "$out:/out" \
        --entrypoint /usr/bin/bash "$builder" /tmp/build.sh mod "$revision" /out > "evidence/mod/build-$run.log" 2>&1 || {
        tail -50 "evidence/mod/build-$run.log" >&2
        exit 1
    }
    sudo cp "$out/aresos.jar" "evidence/mod/aresos-$run.jar"
    sudo rm -rf "$out"
    sudo chown "$(id -u):$(id -g)" "evidence/mod/aresos-$run.jar"
    hashes+=("$(sha256sum "evidence/mod/aresos-$run.jar" | cut -d' ' -f1)")
    echo "Mod jar build $run: ${hashes[-1]}"
done
unzip -Z -v evidence/mod/aresos-1.jar > evidence/mod/entries.txt
if [[ ${hashes[0]} != "${hashes[1]}" ]]; then
    echo 'The mod jar is not reproducible: two clean builds differ' >&2
    exit 1
fi
echo "MOD_JAR_REPRODUCIBLE ${hashes[0]} (pinned: $expected)"
