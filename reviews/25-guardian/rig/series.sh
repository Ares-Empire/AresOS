#!/usr/bin/bash
# DEVELOPMENT AID of package 25 (the real-game check), headless use only: the whole check, one launch at a time.
#
#   series.sh <tag> [first block]
#
# The first home if there is none; then three times the close alone and three times the path, in turn; then one more
# reopening. Each launch first asks the reopened game for the blocks of the launch before. A busy refusal (exit 75:
# short of memory, or the owner's game runs) is retried after five minutes (retry.sh), never forced; thirty seconds
# lie between launches for other holders of the lock. It stops at the first launch that fails. Started again with the
# same tag and first block it goes on after the last launch that left evidence. summary.py <tag> reads the result.
set -u
here=$(cd -- "$(dirname -- "$0")" && pwd)
WT=$(cd -- "$here/../../.." && pwd)
tag=${1:?usage: series.sh <tag> [first block]}
# mod/run/saves is the rig's link (check.sh) only while a series runs: a client test in this worktree must not
# write its worlds into the rig's.
trap '[[ ! -L $WT/mod/run/saves ]] || rm -f -- "$WT/mod/run/saves"' EXIT
n=${2:-1}  # fifteen blocks from here on; a new series on the same home takes blocks no earlier one set
lock=$HOME/.cache/aresos-dev/client-test.lock
launch() {
    # First wait, as the dev scripts do, until no other game run holds the laptop's lock (taken and let go at once):
    # while one runs, its game has the memory this run needs, and every try would only be refused.
    # A launch whose evidence exists is not run again: a series that was cut short goes on where it stopped.
    [[ ! -e $WT/reviews/25-guardian/runs/$1.json ]] || { echo "$1: its evidence exists already; skipped"; return 0; }
    [[ ! -e $lock ]] || /usr/bin/flock "$lock" /usr/bin/true
    "$here/retry.sh" "$here/run.sh" "$@" || exit $?
    sleep 30
}
[[ -d $WT/.work/pkg25/home/.local/share/aresos/worlds/AresHub ]] || launch "create-$tag" MODE=create
launch "close-1-$tag" MODE=close PROBE=$n
launch "stop-1-$tag" MODE=stop PROBE=$((n + 2)) VERIFY=$n,$((n + 1))
launch "close-2-$tag" MODE=close PROBE=$((n + 5)) VERIFY=$((n + 2)),$((n + 3)),$((n + 4))
launch "stop-2-$tag" MODE=stop PROBE=$((n + 7)) VERIFY=$((n + 5)),$((n + 6))
launch "close-3-$tag" MODE=close PROBE=$((n + 10)) VERIFY=$((n + 7)),$((n + 8)),$((n + 9))
launch "stop-3-$tag" MODE=stop PROBE=$((n + 12)) VERIFY=$((n + 10)),$((n + 11))
launch "verify-$tag" MODE=verify VERIFY=$((n + 12)),$((n + 13)),$((n + 14))
