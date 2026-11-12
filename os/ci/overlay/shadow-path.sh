#!/usr/bin/bash
# CI only (package 21 review 5): broken programs of the daily account, first
# on his shells' PATH, named like every command the session start or the
# recovery terminal could look up. Each records that it ran; the session, its
# terminal and the recovery shortcut must start without running one.
set -euo pipefail
bin=/var/home/ares/.local/bin
/usr/bin/install -d -o ares -g ares -m 0755 /var/home/ares/.local "$bin"
while read -r name; do
    printf '#!/bin/sh\nprintf "%%s\n" "$0" >> /tmp/aresos-ci-shadow-ran\nexit 97\n' > "$bin/$name"
    /usr/bin/chown ares:ares "$bin/$name"
    /usr/bin/chmod 0755 "$bin/$name"
done < /usr/libexec/aresos-ci/shadow-names.txt
