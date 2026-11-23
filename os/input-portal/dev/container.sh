#!/usr/bin/bash
# Package 316, on the laptop: run build.sh or cargo audit in the pinned Rust container (rootless podman).
#
#   dev/container.sh build [--cache] <output dir>   build.sh on this source; the result lands in <output dir>
#   dev/container.sh audit                          cargo audit of Cargo.lock against the pinned advisory database
#
# The container mounts no host folder. The source goes in as a tar stream and the result comes back as one, so
# the build, which runs every dependency's build script, can't read or write a host file, and SELinux (enforcing
# on AresOS, where a plain -v mount of the repo is denied) needs no relabel and no exception.
#
# --cache keeps cargo's downloads and its target dir in two podman volumes, so a rebuild after an edit takes
# seconds instead of minutes. It is for development: results that count come from a run without it. Remove them
# with `podman volume rm aresos-input-portal-registry aresos-input-portal-target`.
#
# CARGO_BUILD_JOBS (default 4) limits how many compilers run at once: the laptop's 16 GB are shared.
set -euo pipefail

die() {
    echo "container.sh: $*" >&2
    exit 1
}

usage() {
    sed -n '2,5p' "$0" | sed 's/^# \{0,1\}//' >&2
    exit 2
}

source_dir=$(realpath -e -- "$(dirname -- "$0")/..")
# shellcheck source=../toolchain.env
source "$source_dir/toolchain.env"

work=$(mktemp -d)
name=aresos-input-portal-$$
# podman's --rm removes the container when it ends; the rm here covers an interrupted run.
trap 'podman rm -f "$name" >/dev/null 2>&1 || true; rm -rf -- "$work"' EXIT

# --cgroups=disabled: a session without its own systemd scope (an agent's shell) can't create the container's
# cgroup (seen in package 311). --timeout: nothing here runs longer than an hour.
run=(podman run --rm -i --cgroups=disabled --timeout 3600 --name "$name")

build() {
    local cache=()
    if [ "${1:-}" = --cache ]; then
        cache=(-v aresos-input-portal-registry:/usr/local/cargo/registry
               -v aresos-input-portal-target:/cache/target -e CARGO_TARGET_DIR=/cache/target)
        shift
    fi
    [ "$#" -eq 1 ] || usage
    mkdir -p -- "$1"
    local out
    out=$(realpath -e -- "$1")
    [ -z "$(ls -A -- "$out")" ] || die "the output dir $1 is not empty"

    echo "container.sh: building in $BUILDER_IMAGE" >&2
    # ./target is what a cargo run outside the container would have left; it is never sent in.
    tar -C "$source_dir" --exclude=./target -cf - . |
        "${run[@]}" -e "CARGO_BUILD_JOBS=${CARGO_BUILD_JOBS:-4}" "${cache[@]}" "$BUILDER_IMAGE" bash -euc '
            mkdir /src /out
            tar -xf - -C /src --no-same-owner
            bash /src/build.sh /src /out >&2
            tar -cf - -C /out .' > "$work/out.tar"

    # The archive comes from a container that ran third-party build scripts: accept plain files and folders only
    # (tar itself refuses names that would leave the output dir).
    if tar -tvf "$work/out.tar" | grep -qv '^[-d]'; then
        die "the build's archive holds something other than plain files and folders; nothing was unpacked"
    fi
    tar -xf "$work/out.tar" -C "$out" --no-same-owner
    echo "container.sh: result in $1" >&2
}

audit() {
    [ "$#" -eq 0 ] || usage
    local in=$work/in db=$work/in/advisory-db
    mkdir "$in"
    curl -fsSL --proto '=https' --tlsv1.2 --retry 3 -o "$in/cargo-audit.tgz" "$CARGO_AUDIT_URL"
    echo "$CARGO_AUDIT_SHA256  $in/cargo-audit.tgz" | sha256sum --check --quiet - ||
        die "cargo-audit's download is not the file toolchain.env pins"

    # The advisory database at exactly the pinned commit. It is data: no hook of ours or theirs runs on it.
    git init --quiet "$db"
    git -C "$db" -c core.hooksPath=/dev/null fetch --quiet --depth 1 "$ADVISORY_DB_URL" "$ADVISORY_DB_COMMIT"
    git -C "$db" -c core.hooksPath=/dev/null -c advice.detachedHead=false checkout --quiet FETCH_HEAD
    [ "$(git -C "$db" rev-parse HEAD)" = "$ADVISORY_DB_COMMIT" ] ||
        die "the advisory database is not at $ADVISORY_DB_COMMIT"
    cp -- "$source_dir/Cargo.lock" "$in/Cargo.lock"

    echo "cargo-audit $CARGO_AUDIT_VERSION (sha256 $CARGO_AUDIT_SHA256) in $BUILDER_IMAGE, no network"
    echo "advisory database $ADVISORY_DB_URL at $ADVISORY_DB_COMMIT" \
        "($(TZ=UTC git -C "$db" log -1 --format=%cd --date=format-local:%Y-%m-%dT%H:%M:%SZ))"
    echo "Cargo.lock sha256 $(sha256sum "$in/Cargo.lock" | cut -d' ' -f1)"
    echo "not checked: yanked crates (that needs the live crates.io index, which no pin can hold still)"
    # --no-fetch: the database above and nothing newer. --stale: a pinned database is old on purpose.
    # audit.toml turns the yanked check off, which without a network only prints one error per crate.
    # cargo-audit exits 1 when it finds a vulnerability, and so does this script.
    tar -C "$in" -cf - . |
        "${run[@]}" --network=none "$BUILDER_IMAGE" bash -euc '
            mkdir -p /in/.cargo
            cd /in
            tar -xf - --no-same-owner
            tar -xzf cargo-audit.tgz --no-same-owner --strip-components=1 --wildcards "*/cargo-audit"
            printf "[yanked]\nenabled = false\n" > .cargo/audit.toml
            ./cargo-audit audit --color never --no-fetch --stale --db advisory-db --file Cargo.lock'
}

case "${1:-}" in
    build) shift; build "$@" ;;
    audit) shift; audit "$@" ;;
    *) usage ;;
esac
