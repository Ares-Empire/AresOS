#!/usr/bin/bash
# From the plain, locally built image to a disposable disk on the hosted runner.
set -euo pipefail
test "${GITHUB_ACTIONS-}/${RUNNER_ENVIRONMENT-}/${GITHUB_JOB-}" = true/github-hosted/check-build
plain=localhost/aresos:check
bench=localhost/aresos:bench
planted=localhost/aresos:bench-layer-fixture
mkdir -p vm-work/output
context=$(mktemp -d "$PWD/vm-work/bench-context.XXXXXXXX")
cleanup() {
    rm -rf -- "$context"
    if sudo podman image exists "$planted"; then
        sudo podman rmi "$planted" >/dev/null
    fi
}
trap cleanup EXIT

test -z "$(git ls-files os | awk 'tolower($0) ~ /(^|[\/_-])bench([\/_.-]|$)/ && $0 !~ /^os\/ci\// && $0 !~ /^os\/tests\/test_bench_[a-z0-9_]+\.py$/')"
grep -Fxq 'ci/' os/.containerignore
grep -Fxq 'tests/test_bench_*' os/.containerignore
grep -Fq 'test ! -e /tmp/aresos/ci' os/Containerfile

scan() {
    sudo podman image inspect "$1" | sudo python3 -B os/ci/bench/release_layers.py
}

scan "$plain"
sudo podman run --rm --network=none --entrypoint /usr/bin/bash "$plain" -ec '
    for path in /tmp/aresos/ci/bench /tmp/aresos/bench /usr/libexec/aresos-bench \
        /usr/lib/systemd/system/aresos-bench.service \
        /usr/lib/systemd/system/multi-user.target.wants/aresos-bench.service; do
        test ! -e "$path" && test ! -L "$path" || exit 1
    done
'

# Hide the planted marker in the merged image. Only a scan of older layers sees it.
cat > "$context/Containerfile" <<'PLANT'
FROM localhost/aresos:check
RUN mkdir -p /usr/libexec/aresos-bench && touch /usr/libexec/aresos-bench/planted
RUN rm -rf /usr/libexec/aresos-bench
PLANT
sudo podman build --layers --pull=never --network=none --format=oci -t "$planted" "$context"
sudo podman run --rm --network=none --entrypoint /usr/bin/test "$planted" ! -e /usr/libexec/aresos-bench
if scan "$planted"; then
    echo 'Raw layer scan missed the planted bench file' >&2
    exit 1
else
    test "$?" = 1
fi
echo BENCH_PLANTED_LAYER_REFUSED

cp os/ci/bench/{Containerfile,agent.py,evidence.py,network.py,aresos-bench.service} os/ci/channel.py "$context/"
sudo podman build --pull=never --network=none --format=oci -t "$bench" "$context"
sudo podman image inspect --format '{{ index .Labels "org.opencontainers.image.revision" }}' "$bench" \
    > vm-work/bench-revision
test "$(cat vm-work/bench-revision)" = "$GITHUB_SHA"

builder=$(jq -er .builder os/manifest/base.json)
sudo podman run --rm --privileged --security-opt label=type:unconfined_t \
    -v "$PWD/os/ci/bench/disk.toml:/config.toml:ro" \
    -v "$PWD/vm-work/output:/output" \
    -v /var/lib/containers/storage:/var/lib/containers/storage \
    "$builder" --type raw --rootfs btrfs --use-librepo=True "$bench"
sudo chmod -R a+rX vm-work/output
echo BENCH_DISK_READY
