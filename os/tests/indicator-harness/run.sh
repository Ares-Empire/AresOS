#!/usr/bin/bash
# Run from the worktree. Build the image and test package 316's client build with "image".
# "run <empty evidence directory>" uses the image in one disposable container.
set -euo pipefail

here=$(realpath -e -- "$(dirname -- "$0")")
repo=$(realpath -e -- "$here/../../..")
portal=$repo/os/input-portal/harness
labwc_image=${LABWC_IMAGE:-localhost/aresos-labwc:311e}
tag=${HARNESS_IMAGE_TAG:-329}
clients_image=localhost/aresos-indicator-clients:$tag
image=localhost/aresos-indicator-harness:$tag
mkdir -p "$repo/.work"
work=$(mktemp -d "$repo/.work/indicator-harness.XXXXXX")
name=aresos-indicator-harness-$$
# Only remove the container created by this invocation.
trap 'podman rm -f "$name" >/dev/null 2>&1 || true; rm -rf -- "$work"' EXIT

die() { echo "indicator harness: $*" >&2; exit 1; }
[[ $(podman info --format '{{.Host.Security.Rootless}}') == true ]] || die "rootless podman required"

build_image() {
    podman image exists "$labwc_image" || die "missing package 311's image $labwc_image"
    mkdir -p "$work/clients/labwc-lock" "$work/indicator"
    cp -r -- "$portal/clients" "$portal/Containerfile" "$work/clients/"
    cp -- "$repo/os/labwc/"{loaded_image.py,labwc.lock.json} "$work/clients/labwc-lock/"
    cp -- "$here/Containerfile" "$work/indicator/"
    timeout 1800 podman --cgroup-manager=cgroupfs build --format=oci --build-arg "LABWC_IMAGE=$labwc_image" \
        --tag "$clients_image" "$work/clients"
    timeout 1800 podman --cgroup-manager=cgroupfs build --format=oci --build-arg "CLIENTS_IMAGE=$clients_image" \
        --tag "$image" "$work/indicator"
}

stage() {
    local config=$repo/os/config/usr
    mkdir -p "$work/stage/os/config/usr/libexec" "$work/stage/os/tests"
    cp -- "$here/"*.py "$here/in-container.sh" "$work/stage/"
    cp -p -- "$config/libexec/"aresos-{indicator,level,settings,shell} "$work/stage/os/config/usr/libexec/"
    cp -- "$config/share/aresos/labwc/rc.xml" "$config/share/fonts/aresos/Jersey10-Regular.ttf" \
        "$repo/reviews/312-component-study/tools/look.py" "$work/stage/"
    cp -r -- "$config/share/aresos/look" "$work/stage/"
    cp -r -- "$config/share/themes/AresOS" "$work/stage/"
    cp -- "$repo/os/tests/level_sandbox.py" "$work/stage/os/tests/"
    cp -- "$repo/os/labwc/"{labwc.lock.json,loaded_image.py} "$work/stage/"
}

stage_frame() {
    local base prefix=os/config/usr/share
    base=$(git -C "$repo" merge-base HEAD origin/main)
    printf '%s\n' "$base" > "$work/stage/merge-base.txt"
    mkdir -p "$work/stage/baseline"
    git -C "$repo" show "$base:$prefix/aresos/labwc/rc.xml" > "$work/stage/baseline/rc.xml"
    git -C "$repo" show "$base:$prefix/fonts/aresos/SpaceGrotesk-Variable.ttf" > "$work/stage/baseline/SpaceGrotesk-Variable.ttf"
    git -C "$repo" archive "$base" "$prefix/themes/Ares-Crown" |
        tar -xf - -C "$work/stage/baseline" --strip-components=5
    cp -- "$repo/docs/design/components/"A-{09,10,11,14}-*.png "$work/stage/"
}

run_tests() {
    local evidence status=0 mode=$2
    mkdir -p -- "$1"
    evidence=$(realpath -e -- "$1")
    [[ -z $(ls -A -- "$evidence") ]] || die "evidence directory is not empty"
    podman image exists "$image" || die "build the harness image first"
    stage
    podman image inspect --format '{{.Id}}' "$image" > "$work/stage/harness-image.txt"
    if [[ $mode == frame ]]; then stage_frame; fi
    # No bind, device, forwarded host environment or shared PID/network namespace.
    tar -C "$work/stage" -cf - . |
        podman run --rm -i --cgroups=disabled --network=none --http-proxy=false --timeout 300 --name "$name" \
            "$image" bash -euc '
                mkdir /harness
                tar -xf - -C /harness --no-same-owner
                exec bash /harness/in-container.sh "$1"' bash "$mode" > "$work/evidence.tar" || status=$?
    if ! tar -tf "$work/evidence.tar" >/dev/null 2>&1; then
        die "container returned no evidence (exit $status)"
    fi
    if tar -tvf "$work/evidence.tar" | grep -qv '^[-d]'; then
        die "evidence contains something other than plain files and directories"
    fi
    tar -xf "$work/evidence.tar" -C "$evidence" --no-same-owner
    echo "indicator harness: evidence in $1, exit $status" >&2
    return "$status"
}

case "$#:${1:-}" in
    1:image) build_image ;;
    2:run|2:frame) run_tests "$2" "$1" ;;
    *) die "usage: run.sh image | run.sh {run|frame} <empty evidence directory>" ;;
esac
