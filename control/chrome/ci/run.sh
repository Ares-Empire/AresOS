#!/bin/bash
set -euo pipefail
test "${GITHUB_ACTIONS:-}" = true
test -f /.dockerenv
test "$(uname -s)" = Linux
mkdir -p /out
chmod 777 /out
qualification-chrome --version | tee /out/chrome-version.txt
if test -n "${QUALIFICATION_VERSION:-}"; then
  test "$(qualification-chrome --version | cut -d ' ' -f 3)" = "$QUALIFICATION_VERSION"
fi
python3 control/generate.py --check
python3 -m unittest discover -s control/chrome_tests -v 2>&1 | tee /out/python.txt
node --test control/chrome_tests/*.test.mjs 2>&1 | tee /out/node.txt
node control/chrome/ci/prepare.mjs
runuser -u aresos-tools -- env PYTHONPATH=/workspace/control PYTHONDONTWRITEBYTECODE=1 GITHUB_ACTIONS=true python3 control/chrome/ci/service.py > /out/service.txt 2>&1 &
service_pid=$!
trap 'kill "$service_pid" 2>/dev/null || true' EXIT
for attempt in $(seq 1 100); do
  if test -S /run/aresos-tools/act.sock; then break; fi
  sleep .1
done
test -S /run/aresos-tools/act.sock
runuser -u owner -- env GITHUB_ACTIONS=true dbus-run-session -- xvfb-run -a -s '-screen 0 1440x1000x24' bash -c '
  openbox > /out/openbox.txt 2>&1 &
  node control/chrome/ci/browser.mjs
' 2>&1 | tee /out/browser.txt
