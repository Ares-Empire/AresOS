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
    control|build)
        # check_build=control (package 18c, B2) builds and checks the same image,
        # then puts the Control test layer on top of the CI layer and boots that
        # disk once with os/ci/control/control_vm.py instead of vm.py. Its fixture
        # servers start first, so a broken fixture stops the run before the build.
        if [[ $mode == control ]]; then
            trap 'bash os/ci/control/runner.sh stop' EXIT
            bash os/ci/control/runner.sh start
        fi
        date +%s > evidence/build-start-time.txt
        df -B1 / > evidence/runner-disk-before.txt
        # No separate mod step: the image build itself (the Containerfile's mod
        # stage, then build.sh configure) builds the AresOS mod jar from this
        # commit, as every image build does (package 23). A release build
        # requires the jar's pin. Only the workflow's check-build job (read-only,
        # no secrets: it cannot push, sign or publish) builds a throwaway image,
        # which goes on with another jar and says so; every other caller, the
        # release job included, builds a release.
        kind=release
        if [[ ${GITHUB_JOB-} == check-build ]]; then kind=throwaway; fi
        echo "ARESOS_BUILD_KIND $kind"
        test ! -e os/minecraft/aresos.jar
        revision=$(git rev-parse HEAD)
        sudo podman build --format=oci --build-arg "ARESOS_SOURCE_REVISION=$revision" \
            --build-arg "ARESOS_BUILD_KIND=$kind" \
            --tag localhost/aresos:check --file os/Containerfile os 2>&1 | tee evidence/build.log
        grep -E "^MOD_SOURCE $revision [0-9a-f]{64}\$" evidence/build.log
        grep -E "^MOD_JAR_BUILT [0-9a-f]{64} from $revision\$" evidence/build.log
        unpinned=$(grep -E '^MOD_JAR_UNPINNED pin [0-9a-f]{64}, built [0-9a-f]{64} ' evidence/build.log || true)
        if [[ $kind == throwaway && -n $unpinned ]]; then
            echo "::warning title=Mod jar is not its pin::$unpinned"
        else
            grep -Ex 'MOD_JAR_PINNED [0-9a-f]{64}' evidence/build.log
        fi
        date +%s > evidence/build-end-time.txt
        sudo podman image inspect localhost/aresos:check > evidence/image-inspect.json
        bash os/ci/check-image.sh localhost/aresos:check "$kind"
        # Then boot it once as the release job does, still without publishing:
        # the CI-only test layer, a file-backed disk and one fresh VM pass. Its
        # guest policy checks polkit for the daily account's real active
        # session (os/tests/guest.sh), then recovery login and the power key.
        sudo modprobe nbd max_part=8
        sudo podman tag localhost/aresos:check localhost/aresos:ci
        sudo podman build --format=oci --tag localhost/aresos:vm --file os/ci/overlay/Containerfile .
        disk_image=localhost/aresos:vm
        if [[ $mode == control ]]; then
            bash os/ci/control/runner.sh layer
            disk_image=localhost/aresos:control
        fi
        python3 os/ci/prepare-disk.py
        mkdir -p vm-work/output
        builder=$(jq -r .builder os/manifest/base.json)
        sudo podman run --rm --privileged --security-opt label=type:unconfined_t \
            -v "$PWD/vm-work/config.toml:/config.toml:ro" \
            -v "$PWD/vm-work/output:/output" \
            -v /var/lib/containers/storage:/var/lib/containers/storage \
            "$builder" --type raw --rootfs btrfs --use-librepo=True "$disk_image"
        sudo chmod -R a+rX vm-work/output
        if [[ $mode == control ]]; then
            sudo -E env "ARESOS_REVISION=$revision" python3 os/ci/control/control_vm.py
            echo CHECK_BUILD_CONTROL_PASSED
        else
            sudo -E env ARESOS_VM_PASS=1 python3 os/ci/vm.py
            grep -q ARESOS_ACTIVE_SESSION_POLKIT_PASSED evidence/vm-pass-1/policy-result.json
            echo CHECK_BUILD_VM_PASSED
        fi
        ;;
    *)
        echo "Unknown check-build mode: '$mode' (expected resolve, build or control)" >&2
        exit 2
        ;;
esac
df -B1 / > evidence/runner-disk-after.txt
