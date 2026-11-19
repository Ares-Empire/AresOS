#!/usr/bin/bash
# Package 316: build the input portal backend, inside the pinned Rust container (toolchain.env, BUILDER_IMAGE).
#
#   build.sh <source dir> <output dir>
#
# <source dir> is this folder and is only read. <output dir> must be missing or empty; it gets
#   aresos-input-portal   the binary, for /usr/libexec
#   data/                 the portal file, the D-Bus activation service and the empty allow-list
#   LICENSE               upstream's MIT text, which has to ship with the binary
#
# Package (c)'s image stage calls it as is, as root in that container; on the laptop dev/container.sh does.
# The network is used for two pinned downloads, both before any of this source is compiled: the Debian packages
# toolchain.env names, from Debian's snapshot archive (apt checks the archive's signature), and
# `cargo fetch --locked` (cargo checks each crate against Cargo.lock). The build and the tests run with --offline.
# Anything that differs from toolchain.env stops the build with one line that starts with INPUT_PORTAL_REFUSED.
set -euo pipefail

BINARY=aresos-input-portal

refuse() {
    echo "INPUT_PORTAL_REFUSED $*" >&2
    exit 1
}

[ "$#" -eq 2 ] || refuse "usage: build.sh <source dir> <output dir>"
src=$(realpath -e -- "$1") || refuse "no source dir $1"
for needed in Cargo.toml Cargo.lock toolchain.env LICENSE data; do
    [ -e "$src/$needed" ] || refuse "$1 is not the input portal's source: no $needed"
done
mkdir -p -- "$2"
out=$(realpath -e -- "$2")
[ -z "$(ls -A -- "$out")" ] || refuse "the output dir $2 is not empty"

# shellcheck source=toolchain.env
source "$src/toolchain.env"

rustc_commit=$(rustc -vV | sed -n 's/^commit-hash: //p') || refuse "no rustc here: run this in $BUILDER_IMAGE"
[ "$rustc_commit" = "$RUSTC_COMMIT" ] ||
    refuse "rustc is commit ${rustc_commit:-unknown}, toolchain.env says $RUSTC_COMMIT ($RUSTC_RELEASE): run this in $BUILDER_IMAGE"

work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT

read -r -a debian_packages <<< "$DEBIAN_PACKAGES"
echo "== ${debian_packages[*]} from Debian snapshot $DEBIAN_SNAPSHOT"
# Only this one source is read, whatever the image's own apt sources say.
mkdir "$work/apt-sources"
cat > "$work/apt-sources/snapshot.sources" <<EOF
Types: deb
URIs: https://snapshot.debian.org/archive/debian/$DEBIAN_SNAPSHOT
Suites: trixie
Components: main
Signed-By: /usr/share/keyrings/debian-archive-keyring.pgp
Check-Valid-Until: no
EOF
# Error-Mode=any: an update that could not reach the snapshot fails there, not later as "package not found".
apt_options=(-o Dir::Etc::sourcelist=/dev/null -o "Dir::Etc::sourceparts=$work/apt-sources"
             -o APT::Install-Recommends=false -o APT::Update::Error-Mode=any -o Acquire::Retries=3 -q)
export DEBIAN_FRONTEND=noninteractive
apt-get "${apt_options[@]}" update
apt-get "${apt_options[@]}" install -y "${debian_packages[@]}"
for package in "${debian_packages[@]}"; do
    installed=$(dpkg-query -W -f='${Version}' "${package%%=*}")
    [ "$installed" = "${package#*=}" ] || refuse "${package%%=*} is $installed, toolchain.env says ${package#*=}"
done

# The source dir stays untouched: everything cargo writes goes to the target dir. A caller that wants to keep it
# between runs (dev/container.sh --cache) sets CARGO_TARGET_DIR.
export CARGO_TARGET_DIR=${CARGO_TARGET_DIR:-$work/target}
manifest=(--manifest-path "$src/Cargo.toml")

echo "== cargo fetch --locked"
cargo fetch --locked "${manifest[@]}"
echo "== cargo build --release --locked --offline"
cargo build --release --locked --offline "${manifest[@]}"
echo "== cargo test --locked --offline"
cargo test --locked --offline "${manifest[@]}"

built=$CARGO_TARGET_DIR/release/$BINARY
[ -f "$built" ] || refuse "the build left no $BINARY"
install -m 0755 -- "$built" "$out/$BINARY"
mkdir "$out/data"
install -m 0644 -t "$out/data" -- "$src"/data/*
install -m 0644 -- "$src/LICENSE" "$out/LICENSE"

echo "== built"
(cd "$out" && find . -type f -print0 | sort -z | xargs -0 sha256sum)
# What the image has to provide at run time.
readelf -d "$out/$BINARY" | sed -n 's/.*(NEEDED).*\[\(.*\)\]/needs \1/p'
echo "INPUT_PORTAL_BUILT $BINARY $(sha256sum "$out/$BINARY" | cut -d' ' -f1)"
