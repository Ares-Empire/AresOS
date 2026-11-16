#!/bin/bash
# Development aid for AresOS package 44 (the laptop-screen home, a design study). Not product code.
#
# Shows a prototype in WebKitGTK inside a headless compositor of its own (cage, 1920 x 1080) and saves a
# picture, or measures memory. Nothing reaches the owner's screen: his display variables are removed first,
# and the compositor draws into memory only.
#
#   shots.sh picture <page and options> <picture.png>          e.g. 'street/index.html?apps=24&still=1'
#   shots.sh measure <page and options> [seconds to watch]     prints one JSON line (about:blank: the bare engine)
#   shots.sh all                                                the pictures in ../pictures
#   shots.sh check                                              keys and clicks on each page, and Night street's
#                                                               own check (a removed app, a group past 16)
#
# PKG44_RENDERER=pixman draws in software; unset, the compositor uses the laptop's graphics chip.
# PKG44_ACCEL=never makes the engine draw the page in software too.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
root=$(dirname "$here")

inside() {  # <page and options> <picture or -> <settle> <watch>
    /usr/bin/env -u DISPLAY -u WAYLAND_DISPLAY -u WAYLAND_SOCKET \
        WLR_BACKENDS=headless WLR_LIBINPUT_NO_DEVICES=1 ${PKG44_RENDERER:+WLR_RENDERER=$PKG44_RENDERER} \
        GDK_BACKEND=wayland GTK_A11Y=none PKG44_HEADLESS=1 \
        /usr/bin/timeout 120 /usr/bin/cage -- /bin/sh -c \
        '/usr/bin/wlr-randr --output HEADLESS-1 --custom-mode 1920x1080 && exec /usr/bin/python3 "$@"' \
        sh "$here/webkit-shot.py" "$([[ $1 == about:blank ]] && echo "$1" || echo "file://$root/prototypes/$1")" "$2" "$3" "$4" \
        2>>"${PKG44_LOG:-/dev/null}"
}

case ${1:-} in
picture) inside "$2" "$3" 1.5 0 ;;
measure) inside "$2" - 8 "${3:-20}" ;;
all)
    out=$root/pictures
    mkdir -p "$out"
    base='time=14:32&still=1'
    lit='run=test-web-2,test-tool-3'
    while read -r name page; do
        [[ -n $name ]] || continue
        inside "$page" "$out/$name.png" 1.5 0 >/dev/null
        echo "$name.png"
    done <<LIST
street-1-home        street/index.html?apps=24&$base&$lit
street-2-finding     street/index.html?apps=24&$base&$lit&q=tool
street-3-all-programs street/index.html?apps=24&$base&$lit&q=pdf
street-4-opened      street/index.html?apps=24&$base&run=test-tool-3&open=test-web-2&winx=1010&winy=330
street-5-day-one     street/index.html?apps=5&$base&run=test-web-1
street-6-forty-apps  street/index.html?apps=40&$base&$lit
street-7-ledges      street/index.html?apps=24&$base&$lit&ledges=1
street-8-forty-five-apps street/index.html?apps=45&$base&$lit
street-9-far-house   street/index.html?apps=45&$base&$lit&q=tool19
street-10-full-colour street/index.html?apps=24&$base&$lit&bright=1
map-1-home           map/index.html?apps=24&$base&$lit
map-2-finding        map/index.html?apps=24&$base&$lit&q=tool
map-3-opened         map/index.html?apps=24&$base&run=test-tool-3&open=test-web-2&winx=1080&winy=120
map-4-forty-apps     map/index.html?apps=40&$base&$lit
console-1-home       console/index.html?apps=24&$base&$lit
console-2-finding    console/index.html?apps=24&$base&$lit&q=tool
console-3-opened     console/index.html?apps=24&$base&run=test-tool-3&open=test-web-2&winx=120&winy=420
LIST
    ;;
check)
    for page in street map console; do inside "$page/index.html?apps=24" check 1 0; done
    inside 'street/index.html?apps=45&hole=test-web-1' check-street 1 0 ;;
*) sed -n '2,15p' "$0"; exit 2 ;;
esac
