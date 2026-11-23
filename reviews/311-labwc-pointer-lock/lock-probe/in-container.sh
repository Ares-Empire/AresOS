#!/usr/bin/bash
# Runs inside a throwaway fedora:44 container. Installs one labwc RPM, builds the
# probe and runs it against that labwc on a private headless socket.
#   in-container.sh <labwc rpm> <folder with lock-probe.c>
set -uo pipefail
rpm_file=$1 probe_dir=$2

dnf5 -y -q --setopt=install_weak_deps=False install "$rpm_file" xorg-x11-server-Xwayland gcc pkgconf-pkg-config wayland-devel \
    wayland-protocols-devel wlr-protocols-devel >/dev/null 2>&1 || { echo 'UNUSABLE test tools did not install'; exit 2; }
echo "LABWC $(rpm -q labwc)"

build=$(mktemp -d)
protocols=$(pkg-config --variable=pkgdatadir wayland-protocols)
wlr=/usr/share/wlr-protocols/unstable
for xml in "$protocols/unstable/pointer-constraints/pointer-constraints-unstable-v1.xml" \
    "$protocols/unstable/relative-pointer/relative-pointer-unstable-v1.xml" \
    "$protocols/stable/xdg-shell/xdg-shell.xml" \
    "$wlr/wlr-layer-shell-unstable-v1.xml" "$wlr/wlr-virtual-pointer-unstable-v1.xml"; do
    name=$(basename "$xml" .xml)
    wayland-scanner client-header "$xml" "$build/$name-client-protocol.h"
    wayland-scanner private-code "$xml" "$build/$name-protocol.c"
done
gcc -std=c11 -Wall -Werror -I"$build" -o "$build/lock-probe" "$probe_dir/lock-probe.c" "$build"/*-protocol.c \
    $(pkg-config --cflags --libs wayland-client) -lm || { echo 'UNUSABLE the probe did not compile'; exit 2; }

status=0
for mode in layer window; do
    runtime=$(mktemp -d)
    chmod 0700 "$runtime"
    XDG_RUNTIME_DIR=$runtime WLR_BACKENDS=headless WLR_RENDERER=pixman WLR_HEADLESS_OUTPUTS=1 \
        WLR_LIBINPUT_NO_DEVICES=1 WAYLAND_DISPLAY= DISPLAY= \
        timeout 60 labwc -C "$(mktemp -d)" >"$runtime/labwc.log" 2>&1 &
    compositor=$!
    for _ in $(seq 100); do
        [[ -S $runtime/wayland-0 ]] && break
        sleep 0.1
    done
    if [[ ! -S $runtime/wayland-0 ]]; then
        echo "UNUSABLE labwc did not start for mode $mode"
        tail -20 "$runtime/labwc.log"
        exit 2
    fi
    XDG_RUNTIME_DIR=$runtime WAYLAND_DISPLAY=wayland-0 timeout 40 "$build/lock-probe" "$mode"
    code=$?
    echo "EXIT $mode $code"
    (( code > status )) && status=$code
    kill "$compositor" 2>/dev/null
    wait "$compositor" 2>/dev/null
done
exit "$status"
