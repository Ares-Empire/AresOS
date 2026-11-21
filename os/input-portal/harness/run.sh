#!/usr/bin/bash
# Package 316, on the laptop: the headless harness for the input portal backend (rootless podman).
#
#   harness/run.sh image                             build the harness image (labwc, the tools, the test clients)
#   harness/run.sh run <backend dir> <evidence dir>  run the tests on a built backend; the logs land in <evidence dir>
#
# <backend dir> is what `dev/container.sh build <dir>` leaves: the binary and data/.
#
# Isolation. The tests run in one throwaway container with no network (so no abstract socket of the host
# either), no host folder, no device and no host environment: the harness and the backend go in as a tar
# stream and the evidence comes back as one. Inside, in-container.sh checks all of that before anything starts,
# and makes a scratch HOME and XDG_RUNTIME_DIR for a private bus and a private headless labwc. Nothing here
# touches the session of whoever runs it: no sudo, no install outside the container, no portal configuration.
# The container has a time limit, and cleanup removes only that one container.
#
# The image is built from LABWC_IMAGE (default localhost/aresos-labwc:321c): the `labwc` stage of
# os/Containerfile, whose /out holds the RPM with both patches (311's and 321's). Build it with
#   podman --cgroup-manager=cgroupfs build --target labwc --format=oci --tag localhost/aresos-labwc:321c --file os/Containerfile os
# HARNESS_IMAGE (default localhost/aresos-input-portal-harness:321c) names the harness image, for a run on another
# labwc: the image's build refuses a labwc that is not the lock's, so that also needs that labwc's own lock.
set -euo pipefail

die() {
    echo "run.sh: $*" >&2
    exit 1
}

usage() {
    sed -n '2,6p' "$0" | sed 's/^# \{0,1\}//' >&2
    exit 2
}

here=$(realpath -e -- "$(dirname -- "$0")")
repo=$(realpath -e -- "$here/../../..")
labwc_image=${LABWC_IMAGE:-localhost/aresos-labwc:321c}
image=${HARNESS_IMAGE:-localhost/aresos-input-portal-harness:321c}

work=$(mktemp -d)
name=aresos-input-portal-harness-$$
# podman's --rm removes the container when it ends; the rm here covers an interrupted run.
trap 'podman rm -f "$name" >/dev/null 2>&1 || true; rm -rf -- "$work"' EXIT

build_image() {
    podman image exists "$labwc_image" || die "no image $labwc_image: build os/Containerfile's labwc stage first (see the head of this script)"
    # The build context: this folder's files and the lock that says which labwc is the right one.
    mkdir -p "$work/context/labwc-lock"
    cp -r -- "$here/clients" "$here/Containerfile" "$work/context/"
    cp -- "$repo/os/labwc/loaded_image.py" "$repo/os/labwc/labwc.lock.json" "$work/context/labwc-lock/"
    # --cgroup-manager=cgroupfs: a session without its own systemd scope can't use the systemd manager.
    timeout 1800 podman --cgroup-manager=cgroupfs build --format=oci --build-arg "LABWC_IMAGE=$labwc_image" \
        --tag "$image" --file "$work/context/Containerfile" "$work/context" >&2
}

run_tests() {
    [ "$#" -eq 2 ] || usage
    local backend evidence
    backend=$(realpath -e -- "$1")
    [ -x "$backend/aresos-input-portal" ] || die "$1 holds no aresos-input-portal"
    mkdir -p -- "$2"
    evidence=$(realpath -e -- "$2")
    [ -z "$(ls -A -- "$evidence")" ] || die "the evidence dir $2 is not empty"
    podman image exists "$image" || build_image

    mkdir -p "$work/stage/backend"
    cp -- "$here/in-container.sh" "$here/driver.py" "$work/stage/"
    cp -- "$backend/aresos-input-portal" "$work/stage/backend/"

    # --network=none: no route out, and a network namespace of its own, which is also what keeps the host's
    # abstract sockets (X11, a bus) out of reach. No -v, no --device, no --env: nothing of the host goes in.
    # --timeout: the whole run is over in a few minutes; the driver has its own, shorter limits inside.
    local status=0
    tar -C "$work/stage" -cf - . |
        podman run --rm -i --cgroups=disabled --network=none --http-proxy=false --timeout 900 --name "$name" \
            "$image" bash -euc '
                mkdir /harness
                tar -xf - -C /harness --no-same-owner
                exec bash /harness/in-container.sh' > "$work/evidence.tar" || status=$?

    # The archive comes from the container: accept plain files and folders only.
    if ! tar -tf "$work/evidence.tar" >/dev/null 2>&1; then
        die "the container returned no evidence (exit $status)"
    fi
    if tar -tvf "$work/evidence.tar" | grep -qv '^[-d]'; then
        die "the evidence archive holds something other than plain files and folders; nothing was unpacked"
    fi
    tar -xf "$work/evidence.tar" -C "$evidence" --no-same-owner
    echo "run.sh: evidence in $2, exit $status" >&2
    return "$status"
}

case "${1:-}" in
    image) shift; [ "$#" -eq 0 ] || usage; build_image ;;
    run) shift; run_tests "$@" ;;
    *) usage ;;
esac
