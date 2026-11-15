#!/bin/bash
# DEVELOPMENT AID of package 40, headless use only: this rig calls Gradle directly (inner.sh runs gradlew runClient).
# Rig tool: screenshot of the rig compositor. usage: shot.sh <rig> <file.png>
w=$(sed -n 's/^WAYLAND_DISPLAY=//p' "$1/env")
[[ -n $w && $w != wayland-0 ]] || { echo "refusing display '$w'" >&2; exit 1; }
exec env -u DISPLAY WAYLAND_DISPLAY="$w" /usr/bin/grim "$2"
