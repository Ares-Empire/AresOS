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
    # Owner, 2026-11-09: the daily account uses the stock owner's Homebrew.
    # It reads and runs the prefix but never writes it; installs run as the
    # prefix owner only after sudo accepts the daily account's own password.
    getfacl -n /var/home/linuxbrew | grep -qx 'user:1001:r-x'
    runuser -u ares -- test -x "$brew"
    runuser -u ares -- test -r "$brew"
    if runuser -u ares -- test -w "$prefix"; then
        echo 'Daily account can write the inherited Homebrew prefix'
        exit 1
    fi
    runuser -u ares -- env HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_ANALYTICS=1 "$brew" --version
    runuser -l ares -c 'set -e; if test "$(command -v brew)" != /usr/bin/brew; then echo "Daily login does not use the image brew command"; exit 1; fi; case ":$PATH:" in *:/home/linuxbrew/.linuxbrew/bin:*) ;; *) echo "Homebrew is missing from the daily login PATH"; exit 1;; esac; brew --version'
    # The image sets no daily password, so an install must fail before brew runs.
    if runuser -u ares -- /usr/bin/brew install aresos-never-installed < /dev/null; then
        echo 'Daily account installed through Homebrew without a password'
        exit 1
    fi
    test ! -e "$prefix/Cellar/aresos-never-installed"
    python3 - <<'PY'
import pathlib, subprocess
pids = subprocess.check_output(['pgrep', '-u', 'ares', '-x', 'labwc'], text=True).split()
assert pids, 'No daily session to inspect'
for pid in pids:
    environ = dict(entry.split(b'=', 1) for entry in pathlib.Path(f'/proc/{pid}/environ').read_bytes().split(b'\0') if b'=' in entry)
    path = environ[b'PATH'].decode().split(':')
    # The compositor keeps the system PATH (package 21 review 5); his login
    # shell and AresOS terminals add ~/.local/bin, Homebrew and Flatpak.
    assert path == ['/usr/local/bin', '/usr/local/sbin', '/usr/bin', '/usr/sbin'], path
    print('DAILY_SESSION_PATH=' + ':'.join(path))
PY
    echo INHERITED_HOMEBREW_DAILY_USES_OWNER_WORKING
else
    echo INHERITED_HOMEBREW_STOCK_OWNER_WORKING
fi
