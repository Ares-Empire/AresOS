#!/bin/bash
# Browser-free local reproduction of mail-sweep-growth.json (about 1.5 h on one
# Apple M5). Starts no browser, mail server or container; Mail runs on the unchanged
# test fixtures' in-memory IMAP. Never run inside a worktree someone is editing.
#
#   run.sh MAIN_WORKTREE BRANCH_WORKTREE OUT_DIR PYTHON [LOGS_DIR]
#
# MAIN_WORKTREE at b2b51107, BRANCH_WORKTREE at the measured branch head.
# PYTHON: CPython 3.14 with jsonschema 4.26.0 (the fixtures' only extra need).
# LOGS_DIR: optional `gh run view <id> --log` outputs named <id>.log.
set -euo pipefail
main=$(cd "$1" && pwd); branch=$(cd "$2" && pwd); out=$(mkdir -p "$3" && cd "$3" && pwd); python=$4
tools=$(cd "$(dirname "$0")" && pwd)
inside() {  # inside WORKTREE [ENV=VALUE...] script args...
  local tree=$1; shift
  (cd "$tree/control/mail_tests" && env PYTHONPATH="$tree/control:$tree/control/mail_tests:$tools" \
     PYTHONDONTWRITEBYTECODE=1 "$@")
}
# 1. Clean discovery with call-site attribution (seconds).
inside "$main" "$python" "$tools/discover.py" "$out/clean-main.json"
inside "$branch" "$python" "$tools/discover.py" "$out/clean-branch.json"
inside "$branch" NO_HEADER_INDEX=1 "$python" "$tools/discover.py" "$out/clean-branch-noindex.json"
# 2. Every single-mode fault run: exact pair counts and their cleanup sites.
inside "$main" "$python" "$tools/discover.py" "$out/allsingles-main.json" --singles
inside "$branch" "$python" "$tools/discover.py" "$out/allsingles-branch.json" --singles
inside "$branch" REAL_JOURNAL_STAT=1 "$python" "$tools/discover.py" "$out/allsingles-branch-realstat.json" --singles
# 3. Time per sweep case, same machine, back to back.
flows="maintenance restart_index cancel status"
inside "$main" "$python" "$tools/case_cost.py" "$out/cost-main.json" $flows
inside "$branch" "$python" "$tools/case_cost.py" "$out/cost-branch.json" $flows
inside "$branch" CACHED_BUILD=1 "$python" "$tools/case_cost.py" "$out/cost-branch-cachedbuild.json" $flows
inside "$branch" CACHED_BUILD=1 REAL_JOURNAL_STAT=1 "$python" "$tools/case_cost.py" "$out/cost-branch-cachedbuild-realstat.json" $flows
inside "$branch" CACHED_BUILD=1 REAL_JOURNAL_STAT=1 NO_HEADER_INDEX=1 "$python" "$tools/case_cost.py" "$out/cost-branch-cachedbuild-realstat-noindex.json" $flows
# 4. Mail per-call latency at 0/1000/4000 retained operations, ABBA then AB.
for step in main:plain:r1 branch:plain:r1 branch:plain:r2 main:plain:r2 main:instrumented:r1 branch:instrumented:r1; do
  IFS=: read -r side profile tag <<<"$step"
  tree=$main; [ "$side" = branch ] && tree=$branch
  inside "$tree" "$python" "$tools/latency.py" "$out/latency-$profile-$side-$tag.json" "$profile" 50
done
# 5. Read-only Mail calls on a full disk (temporary sort files).
inside "$main" "$python" "$tools/fulldisk_read.py" "$out/fulldisk-main.json"
inside "$branch" "$python" "$tools/fulldisk_read.py" "$out/fulldisk-branch.json"
# 6. CI logs (optional) and the record.
if [ -n "${5:-}" ]; then
  args=()
  for pair in main-a=43465777152 main-b=43177961962 main-c=43183755749 branch-a=43513676712 \
              branch-b=43530064032 branch-c=43521486798 branch-d=43506058350; do
    args+=("${pair}:$5/${pair#*=}.log")
  done
  "$python" -I "$tools/ci_cases.py" "$out/ci.json" "${args[@]}"
fi
"$python" -I "$tools/summarize.py" "$out" "$out/mail-sweep-growth.json" "$tools/context.json"
