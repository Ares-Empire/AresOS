#!/usr/bin/bash
# Sets or renews the AresOS mod jar's pin in os/minecraft/desktop.lock.json
# (package 23). Every image build already builds the jar from its own commit
# (the Containerfile's source and mod stages) and refuses other bytes; this
# builds exactly those two stages (--target mod) twice, without cache, for this
# checkout's pushed commit, requires equal bytes, and prints the hash to pin.
# It also checks minecraft/builder-tools.txt against the pinned JDK image.
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
python3 os/ci/builder-tools.py --check
revision=$(git rev-parse HEAD)
mkdir -p evidence/mod
hashes=()
for run in 1 2; do
    sudo podman build --no-cache --target mod --format=oci --build-arg "ARESOS_SOURCE_REVISION=$revision" \
        --tag "localhost/aresos-mod:$run" --file os/Containerfile os > "evidence/mod/build-$run.log" 2>&1 || {
        tail -50 "evidence/mod/build-$run.log" >&2
        exit 1
    }
    grep -E "^MOD_SOURCE $revision [0-9a-f]{64}\$" "evidence/mod/build-$run.log"
    container=$(sudo podman create "localhost/aresos-mod:$run")
    sudo podman cp "$container:/out/aresos.jar" "evidence/mod/aresos-$run.jar"
    sudo podman rm "$container" > /dev/null
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
