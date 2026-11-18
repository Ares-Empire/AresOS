#!/usr/bin/bash
# Check packages 21, 23 and 18c on a locally built image (never pushed).
set -euo pipefail
image=$1
# release or throwaway, as check-build.sh built it (build.sh configure, the mod jar).
kind=$2
[[ $kind == release || $kind == throwaway ]]
out=evidence/image
mkdir -p "$out/polkit" "$out/manifest"

# Checks that run inside the image, as root, without network. runuser and
# podman need their PAM session and user namespaces, hence --privileged.
sudo podman run --rm -i --privileged --network=none \
    -v "$PWD/os/ci/control/chrome_image.py:/tmp/aresos-chrome-image-check.py:ro" \
    --entrypoint /usr/bin/bash "$image" -s < os/ci/image-checks.sh \
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
                       ('gh.lock.json', json.loads(pathlib.Path('os/gh.lock.json').read_text())),
                       ('desktop.lock.json', desktop)):
    assert json.loads((manifest / name).read_text()) == reviewed, name
print('Image manifest locks equal the reviewed locks')
PY
# Package 18c: the Control files the image records (image-checks.sh proved the
# image holds exactly them) are what this checkout installs: build.sh's own
# install map recomputes them here. The build commit is this one, and the
# vendored wheels are this checkout's requirements.lock: build.sh checked them
# inside the build, and this check reads the lock again from the checkout,
# apart from the build (REVIEW-A1 #6); image-checks.sh checked the installed bytes
# against the record, and vendor_check.py below the record against the wheels.
expected=$(mktemp -d)
cmp os/gh.lock.json "$out/manifest/gh.lock.json"
bash os/build.sh control-tree os control "$expected/root" | tee "$out/control-tree.txt"
python3 - "$out/manifest/control.json" "$expected/root/usr/share/aresos/manifest/control.json" "$(git rev-parse HEAD)" \
    control/requirements.lock <<'PY'
import json, re, sys
image, expected = (json.load(open(path)) for path in sys.argv[1:3])
revision = sys.argv[3]
assert image['source_revision'] == revision, f'Control in the image is from {image["source_revision"]}, not {revision}'
# The lock as pip reads it: `name==version \` then one or more `--hash=sha256:` lines. Every other line is a comment
# or blank, so no pin can be skipped by a line this parser doesn't know.
normal = lambda name: re.sub(r'[-_.]+', '-', name).lower()
lock, current = {}, None
for line in open(sys.argv[4]).read().splitlines():
    if match := re.fullmatch(r'([A-Za-z0-9._-]+)==(\S+) \\', line):
        current = (normal(match[1]), match[2])
        assert current not in lock, f'requirements.lock pins {current} twice'
        lock[current] = set()
    elif match := re.fullmatch(r'\s+--hash=sha256:([0-9a-f]{64})( \\)?', line):
        assert current is not None, f'a hash before any pin in requirements.lock: {line}'
        lock[current].add(match[1])
    else:
        assert not line.strip() or line.startswith('#'), f'requirements.lock line not understood: {line}'
assert lock and all(lock.values()), 'requirements.lock has no pins, or a pin without a hash'
wheels = image['wheels']
installed = [(wheel['name'], wheel['version']) for wheel in wheels]
assert len(set(installed)) == len(installed), f'a wheel is recorded twice: {installed}'
if set(installed) != set(lock):
    print(f'not in the lock: {sorted(set(installed) - set(lock))}; not installed: {sorted(set(lock) - set(installed))}',
          file=sys.stderr)
    raise SystemExit("The image's wheels are not this checkout's requirements.lock")
unpinned = [wheel for wheel in wheels if wheel['sha256'] not in lock[(wheel['name'], wheel['version'])]
            or not wheel['file'].endswith('.whl')]
assert not unpinned, f"wheels whose SHA-256 is not one of the lock's pins: {unpinned}"
for key in ('format', 'requirements_lock', 'links', 'directories', 'files', 'chrome_build', 'gh'):
    if image[key] != expected[key]:
        if isinstance(expected[key], dict):
            changed = sorted(name for name in image[key].keys() | expected[key].keys()
                             if image[key].get(name) != expected[key].get(name))
            print(f'control.json {key} differs at: {changed[:20]}', file=sys.stderr)
        raise SystemExit(f'control.json {key} is not what this checkout installs')
assert image['wheels'] and all(name == '/usr/lib/aresos-control' or name.startswith('/usr/lib/aresos-control/')
                               for name in image['vendor']), 'vendored paths outside /usr/lib/aresos-control'
print(f'Control in the image is this checkout: {len(image["files"])} files from {revision}, '
      f'{len(image["wheels"])} wheels from requirements.lock (sha256 {image["requirements_lock"]})')
print(f'CONTROL_GH_CHECKOUT_PASS {image["gh"]["version"]} {image["gh"]["binary_sha256"]}')
PY
python3 -B os/ci/control/chrome_image.py compare "$out/manifest/control.json" \
    "$expected/root/usr/share/aresos/manifest/control.json" control | tee "$out/control-chrome-checkout.txt"
rm -rf "$expected"
# REVIEW-X1 #1: the vendored tree itself, apart from the build. The wheels the record names (held to the lock just
# above) come from PyPI again, each with its recorded SHA-256. In a throwaway container of the image, without
# network, vendor_check.py derives the tree they install (the wheels' files and what pip writes, by the rules in its
# docstring), compiles it with the build's command where the build compiled it, and requires the image's tree and
# its record to be exactly that tree: paths, contents (bytecode included) and modes.
vendor_work=$(mktemp -d)
mkdir "$vendor_work/wheels"
python3 -I os/ci/control/vendor_check.py fetch "$out/manifest/control.json" "$vendor_work/wheels" \
    | tee "$out/control-vendor.txt"
cp os/ci/control/vendor_check.py "$out/manifest/control.json" "$vendor_work/"
tar -c -C "$vendor_work" . | sudo podman run --rm -i --network=none --entrypoint /usr/bin/bash "$image" -ec \
    'mkdir /tmp/vendor-check && tar -x -C /tmp/vendor-check &&
     exec /usr/bin/python3 -I /tmp/vendor-check/vendor_check.py check /tmp/vendor-check/control.json /tmp/vendor-check/wheels' \
    | tee -a "$out/control-vendor.txt"
grep -q '^CONTROL_VENDOR_FROM_WHEELS ' "$out/control-vendor.txt"
rm -rf "$vendor_work"
echo CHECK_BUILD_PASSED
