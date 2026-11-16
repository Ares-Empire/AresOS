#!/bin/bash
set -euo pipefail
test "${GITHUB_ACTIONS:-}" = true
test -f /.dockerenv
test "$(uname -s)" = Linux
# A network-none container may lack its own hostname in hosts. Keep sudo's
# logging lookup local rather than waiting for an unreachable DNS server.
python3 - <<'PY'
import socket
with open('/etc/hosts','a') as hosts:
    hosts.write('\n127.0.0.1 '+socket.gethostname()+'\n')
PY
mkdir -p /out
if test -n "${PYTHON_SHARD:-}"; then
  python3 control/chrome/ci/python-shard.py 2>&1 | tee /out/python.txt
  exit
fi
chmod 777 /out
qualification-chrome --version | tee /out/chrome-version.txt
if test -n "${QUALIFICATION_VERSION:-}"; then
  test "$(qualification-chrome --version | cut -d ' ' -f 3)" = "$QUALIFICATION_VERSION"
fi
python3 control/generate.py --check
if test "${INJECTION_PROBE:-}" = true; then
  node control/chrome/ci/prepare.mjs
  runuser -u owner -- env GITHUB_ACTIONS=true dbus-run-session -- xvfb-run -a -s '-screen 0 1440x1000x24' node control/chrome/ci/probe.mjs 2>&1 | tee /out/injection-probe.txt
  exit
fi
if test "${LATENCY_PROBE:-}" != true; then
# Fast page checks precede browser feedback; the full storage sweeps remain mandatory below.
PYTHONPATH=control:control/chrome_tests python3 -m unittest test_policy test_questions test_sites test_unit -v 2>&1 | tee /out/python-page.txt
node --test control/chrome_tests/*.test.mjs 2>&1 | tee /out/node.txt
fi
# Brief 20-ci-noise: the latency pair keeps the service's store (its journal
# and SQLite files) on a tmpfs for both runtimes, so the timed phases measure
# the product, not the shared runner's disk sync. Added disk syncs are caught
# by their counts instead (latency-check.py). A run writes well under 100 MB
# per directory (the journal holds 19 to 30 MB after the 4000-entry history);
# 512 MB each leaves the room the storage ledger's free-space check needs.
# latency-store.py records the mounts as the kernel reports them.
if test "${LATENCY_PROBE:-}" = true; then
  for store_dir in /var/lib/aresos-tools /var/lib/aresos-operation-evidence; do
    mount -t tmpfs -o rw,nosuid,nodev,noexec,size=512m,mode=0755,uid="$(id -u aresos-tools)" latency-store "$store_dir"
  done
  python3 control/chrome/ci/latency-store.py start /out/latency-store.json
fi
runuser -u owner -- env GITHUB_ACTIONS=true dbus-run-session -- xvfb-run -a -s '-screen 0 1440x1000x24' bash -c '
  openbox > /out/baseline-openbox.txt 2>&1 &
  node control/chrome/ci/baseline.mjs
' 2>&1 | tee /out/baseline.txt
node control/chrome/ci/prepare.mjs
# Main fix H5: the latency pair keeps its two harness streams (the service's
# stdout and the browser-boundary audit sink) on a tmpfs the pair mounts, so
# their flushes are not in the disk journal the store's fsyncs wait on. They
# are copied to /out when the probe ends. The store has its own tmpfs (above).
FIXTURE_LOG_DIR=/out
if test "${LATENCY_PROBE:-}" = true && test -d /scratch; then FIXTURE_LOG_DIR=/scratch; fi
export FIXTURE_LOG_DIR
# Brief 28, item 6: the test-only switch that registers chrome_outline. The
# service and the browser harness (with the proxy and the command it starts)
# each build their own catalogue, so both lines set it. Only these two: the
# generated-file check and the Python tests above, and the full suite below,
# see the catalogue without it (generate.py refuses to run with it set).
runuser -u aresos-tools -- env PYTHONPATH=/workspace/control PYTHONDONTWRITEBYTECODE=1 GITHUB_ACTIONS=true ARESOS_TEST_CHROME_OUTLINE=1 FIXTURE_LOG_DIR="$FIXTURE_LOG_DIR" python3 control/chrome/ci/service.py > "$FIXTURE_LOG_DIR/service.txt" 2>&1 &
service_pid=$!
trap 'kill "$service_pid" 2>/dev/null || true' EXIT
for attempt in $(seq 1 100); do
  if test -S /run/aresos-tools/act.sock; then break; fi
  sleep .1
done
test -S /run/aresos-tools/act.sock
runuser -u owner -- env GITHUB_ACTIONS=true ARESOS_TEST_CHROME_OUTLINE=1 dbus-run-session -- xvfb-run -a -s '-screen 0 1440x1000x24' bash -c '
  openbox > /out/openbox.txt 2>&1 &
  node control/chrome/ci/browser.mjs
' 2>&1 | tee /out/browser.txt

if test "${DESTINATION_PROBE:-}" = true || test "${LATENCY_PROBE:-}" = true; then
  if test "$FIXTURE_LOG_DIR" != /out; then
    kill "$service_pid" 2>/dev/null || true
    wait "$service_pid" 2>/dev/null || true
    cp "$FIXTURE_LOG_DIR/service.txt" "$FIXTURE_LOG_DIR/browser-boundary.jsonl" /out/
  fi
  if test "${LATENCY_PROBE:-}" = true; then python3 control/chrome/ci/latency-store.py end /out/latency-store.json; fi
  echo 'Post-18d safety probes complete; not full acceptance'
  exit
fi

if test -n "${BROWSER_SHARD:-}"; then
  echo "Browser shard complete; full Python discovery runs in required parallel shards"
  exit
fi

# A successful browser matrix is not CI acceptance until the complete Python suite passes.
python3 -m unittest discover -s control/chrome_tests -v 2>&1 | tee /out/python.txt
