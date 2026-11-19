#!/usr/bin/bash
# Package 311, check_build=resolve: runs inside the locked fedora:44, which has no Python. Finds what labwc's source
# package needs today and leaves it for stage.py resolve, which writes the candidate lock.
#   resolve-download.sh <source package url> <its sha256> <output folder>
set -uo pipefail
url=$1 sha256=$2 out=$3
refuse() { echo "LABWC_REFUSED $*" >&2; exit 1; }
mkdir -p "$out/downloads"
source_rpm=$(mktemp)
curl -fsSL --proto '=https' --tlsv1.2 --retry 3 -o "$source_rpm" "$url" || refuse "could not download $url"
[[ $(sha256sum "$source_rpm" | cut -d' ' -f1) == "$sha256" ]] || refuse 'the source package differs from the lock'
rpm -qa --qf '%{NEVRA}\n' | grep -v '^gpg-pubkey-' | sort > "$out/base-packages.txt"
# Names only: rpmbuild checks the spec's version limits itself when it builds.
mapfile -t wanted < <(rpm -qp --nosignature --requires "$source_rpm" | grep -v '^rpmlib(' | cut -d' ' -f1)
(( ${#wanted[@]} )) || refuse 'the source package lists no build dependencies'
# python3 runs stage.py in the stage; the other two are what rpmbuild itself needs. A real transaction, downloaded
# only: it picks the x86_64 packages and the upgrades of the base that the stage will install.
dnf5 --disable-repo='*' --enable-repo=fedora --enable-repo=updates --setopt=install_weak_deps=False \
    --setopt=skip_if_unavailable=False --setopt=gpgcheck=True --setopt=keepcache=True install -y --downloadonly \
    python3 rpm-build redhat-rpm-config "${wanted[@]}" ||
    refuse "the build dependencies do not resolve on fedora:44 from Fedora's repositories"
# dnf5 install has no download folder of its own; this container's package cache holds this transaction only.
find /var/cache/libdnf5 -name '*.rpm' -exec cp -t "$out/downloads" {} + ||
    refuse 'the resolved packages could not be collected'
