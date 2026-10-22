#!/usr/bin/bash
set -euxo pipefail
stage=@STAGE@
prefix=/var/home/linuxbrew/.linuxbrew
brew="$prefix/bin/brew"

# This is the real inherited installation, never a replacement fixture.
test -f "$brew"
test "$(stat -c %u "$prefix")" = 1000
stat -c '%n owner=%u:%g mode=%a' /var/home/linuxbrew "$prefix" "$(readlink -f "$brew")"
getfacl -n /var/home/linuxbrew
sha256sum "$(readlink -f "$brew")"
runuser -u ares-recovery -- test -w "$prefix"
runuser -u ares-recovery -- env HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_ANALYTICS=1 "$brew" --version

if [[ $stage == aresos ]]; then
    runuser -u ares -- test ! -x "$brew"
    runuser -u ares -- test ! -r "$brew"
    runuser -u ares -- test ! -w "$prefix"
    if runuser -u ares -- "$brew" --version; then
        echo 'Daily account executed inherited Homebrew'
        exit 1
    fi
    if runuser -u ares -- bash "$brew" --version; then
        echo 'Daily account read inherited Homebrew through an interpreter'
        exit 1
    fi
    runuser -l ares -c 'set -e; if command -v brew; then echo "Homebrew is on the daily login PATH"; exit 1; fi; case "$PATH" in *linuxbrew*) exit 1;; esac; test -z "${HOMEBREW_PREFIX:-}"'
    python3 - <<'PY'
import pathlib, subprocess
pids = subprocess.check_output(['pgrep', '-u', 'ares', '-x', 'labwc'], text=True).split()
assert pids, 'No daily session to inspect'
for pid in pids:
    environ = dict(entry.split(b'=', 1) for entry in pathlib.Path(f'/proc/{pid}/environ').read_bytes().split(b'\0') if b'=' in entry)
    path = environ[b'PATH'].decode()
    assert 'linuxbrew' not in path, path
    print('DAILY_SESSION_PATH=' + path)
PY
    echo INHERITED_HOMEBREW_DAILY_DENIED_OWNER_WORKING
else
    echo INHERITED_HOMEBREW_STOCK_OWNER_WORKING
fi
