#!/usr/bin/bash
# DEVELOPMENT AID of package 25 (the real-game check), headless use only: the whole check, one launch at a time.
#
#   series.sh <tag> [first block]
#
# The first home if there is none; then three times the close alone and three times the path, in turn; then one more
# reopening. Each launch first asks the reopened game for the blocks of the launch before. A busy refusal (exit 75:
# short of memory, or the owner's game runs) is retried after five minutes (retry.sh), never forced; thirty seconds
# lie between launches for other holders of the lock. It stops at the first launch that fails.
set -u
here=$(cd -- "$(dirname -- "$0")" && pwd)
WT=$(cd -- "$here/../../.." && pwd)
tag=${1:?usage: series.sh <tag> [first block]}
n=${2:-1}  # nine blocks from here on; a new series on the same home takes blocks no earlier one set
launch() { "$here/retry.sh" "$here/run.sh" "$@" || exit $?; sleep 30; }
[[ -d $WT/.work/pkg25/home/.local/share/aresos/worlds/AresHub ]] || launch "create-$tag" MODE=create
launch "close-1-$tag" MODE=close PROBE=$n
launch "stop-1-$tag" MODE=stop PROBE=$((n + 1)) VERIFY=$n
launch "close-2-$tag" MODE=close PROBE=$((n + 3)) VERIFY=$((n + 1)),$((n + 2))
launch "stop-2-$tag" MODE=stop PROBE=$((n + 4)) VERIFY=$((n + 3))
launch "close-3-$tag" MODE=close PROBE=$((n + 6)) VERIFY=$((n + 4)),$((n + 5))
launch "stop-3-$tag" MODE=stop PROBE=$((n + 7)) VERIFY=$((n + 6))
launch "verify-$tag" MODE=verify VERIFY=$((n + 7)),$((n + 8))
