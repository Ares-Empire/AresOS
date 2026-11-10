#!/usr/bin/bash
# Throwaway image path (package 21). It builds this checkout's image into the
# runner's local storage and checks the result. The job has no registry write
# permission or credentials; nothing is pushed, signed or published.
set -euo pipefail
mode=${1-}
base=$(jq -r .reference os/manifest/base.json)
mkdir -p evidence
case $mode in
    resolve)
        # Inventory and resolve inside the pinned base only; no build.
        sudo podman pull "$base"
        sudo podman run --rm --network=host -v "$PWD/os:/tmp/aresos:ro" -v "$PWD/evidence:/evidence" \
            --entrypoint /usr/bin/bash "$base" /tmp/aresos/ci/check-resolve.sh
        # Package 23: the mod jar must build to the same bytes twice.
        bash os/ci/build-mod.sh --twice
        ;;
    build)
        date +%s > evidence/build-start-time.txt
        df -B1 / > evidence/runner-disk-before.txt
        sudo podman build --format=oci --build-arg "ARESOS_SOURCE_REVISION=$(git rev-parse HEAD)" \
            --tag localhost/aresos:check --file os/Containerfile os 2>&1 | tee evidence/build.log
        date +%s > evidence/build-end-time.txt
        sudo podman image inspect localhost/aresos:check > evidence/image-inspect.json
        bash os/ci/check-image.sh localhost/aresos:check
        # Then boot it once as the release job does, still without publishing:
        # the CI-only test layer, a file-backed disk and one fresh VM pass. Its
        # guest policy checks polkit for the daily account's real active
        # session (os/tests/guest.sh), then recovery login and the power key.
        sudo modprobe nbd max_part=8
        sudo podman tag localhost/aresos:check localhost/aresos:ci
        sudo podman build --format=oci --tag localhost/aresos:vm --file os/ci/overlay/Containerfile .
        python3 os/ci/prepare-disk.py
        mkdir -p vm-work/output
        builder=$(jq -r .builder os/manifest/base.json)
        sudo podman run --rm --privileged --security-opt label=type:unconfined_t \
            -v "$PWD/vm-work/config.toml:/config.toml:ro" \
            -v "$PWD/vm-work/output:/output" \
            -v /var/lib/containers/storage:/var/lib/containers/storage \
            "$builder" --type raw --rootfs btrfs --use-librepo=True localhost/aresos:vm
        sudo chmod -R a+rX vm-work/output
        sudo -E env ARESOS_VM_PASS=1 python3 os/ci/vm.py
        grep -q ARESOS_ACTIVE_SESSION_POLKIT_PASSED evidence/vm-pass-1/policy-result.json
        echo CHECK_BUILD_VM_PASSED
        ;;
    *)
        echo "Unknown check-build mode: '$mode' (expected resolve or build)" >&2
        exit 2
        ;;
esac
df -B1 / > evidence/runner-disk-after.txt
