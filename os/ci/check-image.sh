#!/usr/bin/bash
# Check packages 21 and 23 on a locally built image (never pushed).
set -euo pipefail
image=$1
# release or throwaway, as check-build.sh built it (build.sh configure, the mod jar).
kind=$2
[[ $kind == release || $kind == throwaway ]]
out=evidence/image
mkdir -p "$out/polkit" "$out/manifest"

# Checks that run inside the image, as root, without network. runuser and
# podman need their PAM session and user namespaces, hence --privileged.
sudo podman run --rm -i --privileged --network=none --entrypoint /usr/bin/bash "$image" -s < os/ci/image-checks.sh \
    2>&1 | tee "$out/checks.txt"
grep -qx IMAGE_CHECKS_PASSED "$out/checks.txt"

# Rootless containers for the daily account need its subordinate ID ranges.
# This needs user namespaces inside the check container, hence --privileged.
sudo podman run --rm -i --privileged --network=none --entrypoint /usr/bin/bash "$image" -s <<'EOF' 2>&1 | tee "$out/rootless.txt"
set -euxo pipefail
systemd-tmpfiles --create /usr/lib/tmpfiles.d/aresos.conf
grep -x 'ares:524288:65536' /etc/subuid
grep -x 'ares:524288:65536' /etc/subgid
runuser -u ares -- env HOME=/var/home/ares XDG_RUNTIME_DIR=/tmp podman unshare cat /proc/self/uid_map | tee /tmp/uid_map
awk '$1 == 0 && $2 == 1001 && $3 == 1 {owner = 1} $1 == 1 && $2 == 524288 && $3 == 65536 {range = 1} END {exit !(owner && range)}' /tmp/uid_map
echo ROOTLESS_MAPPING_PASSED
EOF
grep -qx ROOTLESS_MAPPING_PASSED "$out/rootless.txt"

# polkit: evaluate the image's real rules, then the same rules without the
# AresOS file, which must fail (the check is not vacuous).
sudo podman run --rm --network=none --entrypoint /usr/bin/bash "$image" -ec \
    'cd / && tar -c $(ls -d etc/polkit-1/rules.d usr/share/polkit-1/rules.d usr/share/polkit-1/actions 2>/dev/null)' \
    | tar -x -C "$out/polkit"
sudo podman run --rm --network=none --entrypoint /usr/bin/tar "$image" -c -C /usr/share/aresos/manifest . \
    | tar -x -C "$out/manifest"
sudo chown -R "$(id -u):$(id -g)" "$out"
test -d "$out/polkit/usr/share/polkit-1/actions"
cmp os/config/usr/share/polkit-1/rules.d/00-aresos-maintenance.rules \
    "$out/polkit/usr/share/polkit-1/rules.d/00-aresos-maintenance.rules"
node os/ci/polkit-check.js "$out/polkit" os/ci/polkit-review.json "$out/polkit-result.json" | tee "$out/polkit.txt"
control=$(mktemp -d)
cp -a "$out/polkit/." "$control/"
rm "$control/usr/share/polkit-1/rules.d/00-aresos-maintenance.rules"
if node os/ci/polkit-check.js "$control" os/ci/polkit-review.json "$out/polkit-without-aresos.json" > "$out/polkit-without-aresos.txt"; then
    echo 'polkit check passed even without the AresOS rule' >&2
    exit 1
fi
rm -rf "$control"
echo 'The same check fails without the AresOS rule, as expected' | tee -a "$out/polkit.txt"
sudo podman run --rm --network=none --entrypoint /usr/bin/cat "$image" /usr/share/aresos/minecraft/desktop.lock.json \
    > "$out/manifest/desktop.lock.json"
# build.sh re-serializes the Fedora lock it verified, so compare content. The
# image records its mod jar (aresos-mod.json): in a release build it is the
# pin; a throwaway build may carry another jar, and then its desktop lock
# differs from the reviewed one in that jar's SHA-256 alone.
python3 - "$out/manifest" "$kind" <<'PY'
import json, pathlib, sys
manifest, kind = pathlib.Path(sys.argv[1]), sys.argv[2]
desktop = json.loads(pathlib.Path('os/minecraft/desktop.lock.json').read_text())
mod = next(mod for mod in desktop['mods'] if mod['file'] == 'aresos.jar')
record = json.loads((manifest / 'aresos-mod.json').read_text())
assert record['pinned_sha256'] == mod['sha256'], record
if record['sha256'] != mod['sha256']:
    assert kind == 'throwaway', f'A release image carries mod jar {record["sha256"]}, not its pin {mod["sha256"]}'
    print(f'Throwaway image: mod jar {record["sha256"]}, pin {mod["sha256"]}')
    mod['sha256'] = record['sha256']
for name, reviewed in (('packages.lock.json', json.loads(pathlib.Path('os/packages.lock.json').read_text())),
                       ('google-chrome.lock.json', json.loads(pathlib.Path('os/google-chrome.lock.json').read_text())),
                       ('desktop.lock.json', desktop)):
    assert json.loads((manifest / name).read_text()) == reviewed, name
print('Image manifest locks equal the reviewed locks')
PY
echo CHECK_BUILD_PASSED
