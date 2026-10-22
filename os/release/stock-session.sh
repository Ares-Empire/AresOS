#!/usr/bin/bash
set -euo pipefail
if getent passwd ares; then
    echo 'Stock deployment unexpectedly contains daily account ares'
    exit 1
fi
systemctl is-active display-manager.service
test ! -e /usr/bin/aresos-session
