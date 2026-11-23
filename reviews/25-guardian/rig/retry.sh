#!/usr/bin/bash
# A busy refusal is retried after five minutes, at most six retries. Never bypass the guard.
set -u
for ((attempt=0; attempt<=6; attempt++)); do
    printf '%s attempt=%s command=' "$(date -Is)" "$attempt"
    printf '%q ' "$@"
    printf '\n'
    "$@"
    status=$?
    printf '%s attempt=%s exit=%s\n' "$(date -Is)" "$attempt" "$status"
    ((status == 75 && attempt < 6)) || exit "$status"
    sleep 300
done
