#!/bin/bash
set -euo pipefail
# Executed only by control-chrome on a disposable GitHub Linux runner.
test "${GITHUB_ACTIONS:-}" = true
test "$(uname -s)" = Linux
for latency_revision in current ab7aba92; do
  latency_tree="$PWD/.work/latency-runtime/$latency_revision"
  latency_out="$PWD/.work/latency-out/$latency_revision"
  mkdir -p "$latency_tree" "$latency_out"
  latency_ref="$latency_revision"
  if test "$latency_revision" = current; then latency_ref=HEAD; fi
  git archive "$latency_ref" control docs/control/TOOLS.md .github/workflows/control-chrome.yml .github/workflows/control-chrome-qualification.yml | tar -x -C "$latency_tree"
  if test "$latency_revision" != current; then
    cp -R control/chrome/ci/. "$latency_tree/control/chrome/ci/"
    cp -R control/chrome_tests/. "$latency_tree/control/chrome_tests/"
    cp .github/workflows/control-chrome.yml .github/workflows/control-chrome-qualification.yml "$latency_tree/.github/workflows/"
  fi
  python3 "$latency_tree/control/chrome/build.py" > "$latency_out/runtime-build.txt"
  tar -C "$latency_tree" -cf - control docs/control/TOOLS.md .github/workflows/control-chrome-qualification.yml .github/workflows/control-chrome.yml | docker build --build-arg PACKAGE_URL="$PACKAGE_URL" --build-arg PACKAGE_SHA256="$PACKAGE_SHA256" -t "aresos-latency-$latency_revision" -f control/chrome/ci/Dockerfile -
  timeout --signal=TERM --kill-after=30s 50m docker run --rm --network none --cap-add SYS_ADMIN --security-opt seccomp=unconfined --security-opt apparmor=unconfined --shm-size=512m -e INSTALL_MODE=policy -e LATENCY_PROBE=true -e LATENCY_PRIVACY -e LATENCY_BASELINE="$latency_revision" -e QUALIFICATION_VERSION -e GITHUB_RUN_ID -e GITHUB_SHA -v "$latency_out:/out" "aresos-latency-$latency_revision"
  python3 control/chrome/ci/latency-summary.py "$latency_out"
done
