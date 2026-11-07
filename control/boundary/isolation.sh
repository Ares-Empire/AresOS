#!/bin/bash
set -euo pipefail
# Toolbox/distrobox defaults share the host home and desktop sockets. This tests
# the proposed explicit separation, not those unsafe default integration flags.
container="boundary-assistant-${GITHUB_RUN_ID:-local}"
trap 'docker rm -f "$container" >/dev/null 2>&1 || true' EXIT
docker run -d --name "$container" --network none aresos-boundary \
  python3 -I /opt/aresos-control/isolation.py assistant >/dev/null
for attempt in $(seq 1 40); do
  if docker logs "$container" 2>&1 | grep -q ASSISTANT_READY; then break; fi
  sleep 0.25
done
docker logs "$container" | tee evidence/isolation-assistant.txt
grep -q ASSISTANT_READY evidence/isolation-assistant.txt
docker run --rm --network none --user 10003:10003 \
  -e HOME=/home/coder -e DISABLE_AUTOUPDATER=1 -e CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
  --mount "type=bind,src=$PWD/control/boundary/coding-settings.json,dst=/etc/claude-code/managed-settings.json,readonly" \
  aresos-boundary python3 -I /opt/aresos-control/isolation.py coder \
  2>&1 | tee evidence/isolation-coder.txt
