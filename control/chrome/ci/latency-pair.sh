#!/bin/bash
set -euo pipefail
# Executed only by control-chrome on a disposable GitHub Linux runner.
#   latency-pair.sh             the paired latency samples, current and ab7aba92
#   latency-pair.sh efficiency  brief 28's group 16 tasks, after the pair, in the
#                               current runtime's image the pair built (plain leg)
test "${GITHUB_ACTIONS:-}" = true
test "$(uname -s)" = Linux

# One docker command for the samples and the efficiency probe, so their options
# can't drift apart. Extra options (the probe's) come before the mount.
latency_container() {
  local revision="$1" out="$2"
  shift 2
  timeout --signal=TERM --kill-after=30s 50m docker run --rm --network none --cap-add SYS_ADMIN --security-opt seccomp=unconfined --security-opt apparmor=unconfined --shm-size=512m --tmpfs /scratch:rw,size=256m,mode=1777 -e INSTALL_MODE=policy -e LATENCY_PROBE=true -e CHROME_FIXTURE_OBSERVER=true -e LATENCY_PRIVACY -e LATENCY_BASELINE="$revision" -e QUALIFICATION_VERSION -e GITHUB_RUN_ID -e GITHUB_SHA "$@" -v "$out:/out" "aresos-latency-$revision"
}

case "${1:-pair}" in
  pair)
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
      latency_container "$latency_revision" "$latency_out"
      python3 control/chrome/ci/latency-summary.py "$latency_out"
    done
    ;;
  efficiency)
    # The tasks run once, in a fresh container and service of their own, so the
    # latency samples above never see their history. Only the plain leg: no
    # audit recording in the counts or the timings.
    test "${LATENCY_PRIVACY:-}" = plain
    docker image inspect aresos-latency-current > /dev/null
    efficiency_out="$PWD/.work/latency-out/efficiency"
    mkdir -p "$efficiency_out"
    latency_container current "$efficiency_out" -e EFFICIENCY_PROBE=true -e ImageOS -e ImageVersion -e RUNNER_ENVIRONMENT -e RUNNER_ARCH
    python3 control/chrome/ci/efficiency-summary.py "$efficiency_out"
    ;;
  *)
    echo 'usage: latency-pair.sh [pair|efficiency]' >&2
    exit 64
    ;;
esac
