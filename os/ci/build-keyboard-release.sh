#!/usr/bin/bash
set -euo pipefail
# The caller resolves this interpreter before sudo. Shell builtins validate it
# before Python validates every other tool, and before any credential access.
python=${1-}
if [[ "$python" == /* && -f "$python" && -x "$python" ]]; then
    shift
    exec "$python" os/ci/build_tools.py privileged "$@"
fi
printf '%s\n' 'STOP: absolute executable Python path required before credentials' >&2
exit 1
