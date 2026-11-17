#!/bin/bash
# Shared setup and the full base suite, inside the disposable container.
set -euo pipefail
source control/ci/setup.sh
python3 control/generate.py --check
# The test process must not be PID 1: the hook tests mark it as their Claude Code session, and a hook's walk never
# takes PID 1 as a session (usage._session). Control base runs this script under `docker run --init`, Control Mail
# with `docker exec`. The printf after base.py also keeps bash from exec'ing base.py in place as its last command.
python3 control/ci/base.py
printf 'Control base suite PASS\n'
