#!/usr/bin/bash
# Package 311: the labwc stage's first step, on the locked fedora:44. That image has no Python, so the checked inputs
# from the labwc-inputs stage go in first; stage.py build then proves the result is exactly the locked environment.
#   install-inputs.sh <inputs folder>
set -uo pipefail
if ! dnf5 --disable-repo='*' --setopt=install_weak_deps=False --setopt=localpkg_gpgcheck=True install -y "$1"/rpms/*.rpm; then
    echo 'LABWC_REFUSED the locked build dependencies do not install on the locked fedora:44: renew them with check_build=resolve' >&2
    exit 1
fi
