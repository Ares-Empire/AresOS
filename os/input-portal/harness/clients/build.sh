#!/usr/bin/bash
# Package 316's harness, inside its image build: compile the test clients and check that the installed labwc
# is the build that os/labwc/labwc.lock.json on this branch describes.
set -euo pipefail

src=/opt/harness/src out=/opt/harness/bin lock=/opt/harness/labwc-lock
gen=$(mktemp -d)
mkdir -p "$out"

protocols=$(pkg-config --variable=pkgdatadir wayland-protocols)
for xml in "$protocols/stable/xdg-shell/xdg-shell.xml" \
    "$protocols/unstable/xdg-decoration/xdg-decoration-unstable-v1.xml" \
    "$protocols/unstable/pointer-constraints/pointer-constraints-unstable-v1.xml" \
    "$protocols/unstable/relative-pointer/relative-pointer-unstable-v1.xml" \
    /usr/share/wlr-protocols/unstable/wlr-virtual-pointer-unstable-v1.xml \
    /usr/share/wlr-protocols/unstable/wlr-layer-shell-unstable-v1.xml \
    /usr/share/wlr-protocols/unstable/wlr-output-management-unstable-v1.xml \
    "$src/virtual-keyboard-unstable-v1.xml"; do
    name=$(basename "$xml" .xml)
    wayland-scanner client-header "$xml" "$gen/$name-client-protocol.h"
    wayland-scanner private-code "$xml" "$gen/$name-protocol.c"
done
# shellcheck disable=SC2046
gcc -std=c11 -O1 -Wall -Werror -I"$gen" -o "$out/wl-harness" "$src/wl-harness.c" "$gen"/*-protocol.c \
    $(pkg-config --cflags --libs wayland-client xkbcommon)
# shellcheck disable=SC2046
gcc -std=c11 -O1 -Wall -Werror -o "$out/eis-receiver" "$src/eis-receiver.c" $(pkg-config --cflags --libs libei-1.0)
rm -rf -- "$gen"

# The RPM's name and the bytes the loader maps, against the lock: this labwc is the stage's, both patches included.
python3 -I - "$lock" <<'PY'
import json
import subprocess
import sys

lock_dir = sys.argv[1]
sys.path.insert(0, lock_dir)
from loaded_image import loaded_sha256  # noqa: E402

result = json.load(open(f"{lock_dir}/labwc.lock.json"))["result"]
installed = subprocess.run(["rpm", "-q", "labwc"], capture_output=True, text=True, check=True).stdout.strip()
if installed != result["nevra"]:
    sys.exit(f"HARNESS_REFUSED labwc is {installed}, the lock says {result['nevra']}")
for path, want in sorted(result["loaded_sha256"].items()):
    got = loaded_sha256(path)
    if got != want:
        sys.exit(f"HARNESS_REFUSED {path} loads as {got}, the lock says {want}")
    print(f"HARNESS_LABWC {path} loaded_sha256 {got} matches the lock")
PY
sha256sum /opt/harness/rpm/*.rpm | sed 's/^/HARNESS_LABWC_RPM /'
