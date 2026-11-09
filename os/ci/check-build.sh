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
        ;;
    build)
        date +%s > evidence/build-start-time.txt
        df -B1 / > evidence/runner-disk-before.txt
        sudo podman build --format=oci --build-arg "ARESOS_SOURCE_REVISION=$(git rev-parse HEAD)" \
            --tag localhost/aresos:check --file os/Containerfile os 2>&1 | tee evidence/build.log
        date +%s > evidence/build-end-time.txt
        sudo podman image inspect localhost/aresos:check > evidence/image-inspect.json
        bash os/ci/check-image.sh localhost/aresos:check
        ;;
    *)
        echo "Unknown check-build mode: '$mode' (expected resolve or build)" >&2
        exit 2
        ;;
esac
df -B1 / > evidence/runner-disk-after.txt
