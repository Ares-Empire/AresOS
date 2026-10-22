#!/usr/bin/bash
set -euo pipefail
test "$(id -u ares-recovery)" = 1000
if getent passwd ares; then
    echo 'Refusing switch: daily account ares already exists'
    exit 1
fi
test -z "$(getent passwd 1001)"
test -r /etc/ostree/auth.json
bootc switch --retain @REFERENCE@
