#!/usr/bin/bash
set -euo pipefail

# Isolate APT from the runner's mutable Ubuntu and third-party repositories.
directory="$PWD/.work/apt"
mkdir -p "$directory/lists/partial"
repository=$(jq -r .repository os/ci/toolchain.json)
while read -r suite; do
    printf 'deb [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg check-valid-until=no] %s %s main universe restricted multiverse\n' "$repository" "$suite"
    printf 'deb-src [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg check-valid-until=no] %s %s main universe restricted multiverse\n' "$repository" "$suite"
done < <(jq -r '.suites[]' os/ci/toolchain.json) > "$directory/sources.list"
printf 'Package: *\nPin: release o=Ubuntu\nPin-Priority: 1001\n' > "$directory/preferences"
options=(-o Acquire::Retries=3 -o "Dir::Etc::sourcelist=$directory/sources.list" -o Dir::Etc::sourceparts=-
         -o "Dir::State::lists=$directory/lists" -o "Dir::Etc::preferences=$directory/preferences"
         -o Dir::Etc::preferencesparts=-)
sudo apt-get "${options[@]}" update
packages=()
names=()
while IFS=$'\t' read -r package version; do
    candidate=$(apt-cache "${options[@]}" policy "$package" | awk '/Candidate:/ {print $2}')
    test "$candidate" = "$version"
    packages+=("$package=$version")
    names+=("$package")
done < <(jq -r '.packages | to_entries[] | [.key, .value] | @tsv' os/ci/toolchain.json)
printf '%s\n' "${packages[@]}" | tee evidence/toolchain-packages.txt
sudo apt-get "${options[@]}" install -y --allow-downgrades "${packages[@]}"
# Reinstall even preinstalled packages so the tools/firmware bytes come from
# the signed dated archive, rather than trusting the mutable runner image.
sudo apt-get "${options[@]}" install -y --reinstall "${packages[@]}"
cp os/ci/toolchain.json evidence/toolchain.json
cp "$directory/sources.list" evidence/toolchain-sources.list
apt-cache "${options[@]}" policy > evidence/toolchain-policy.txt
dpkg-query -W > evidence/host-packages.txt
dpkg-query -W -f='${Package} ${Version}\n' "${names[@]}" > evidence/toolchain-installed.txt
for package in "${packages[@]}"; do
    apt-cache "${options[@]}" show "$package"
done > evidence/toolchain-package-metadata.txt
sha256sum /usr/bin/podman /usr/bin/skopeo /usr/bin/qemu-system-x86_64 /usr/bin/qemu-img /usr/bin/qemu-nbd \
    /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/OVMF/OVMF_VARS_4M.fd > evidence/toolchain-sha256.txt
{
    printf 'ImageOS=%s\nImageVersion=%s\n' "${ImageOS:-unknown}" "${ImageVersion:-unknown}"
    uname -a
    modinfo kvm || true
    modinfo nbd || true
} > evidence/host-platform.txt

# Use the patched source for the exact installed binary, authenticated by the
# same dated Ubuntu indexes. This downloads/extracts source, never builds it.
sudo apt-get "${options[@]}" install -y --no-install-recommends dpkg-dev python3-yaml
source_directory="$PWD/.work/edk2-source"
mkdir -p "$source_directory"
source_version=$(dpkg-query -W -f='${source:Version}' ovmf)
(cd "$source_directory"; apt-get "${options[@]}" source "edk2=$source_version")
python3 os/ci/firmware_contract.py "$source_directory"
