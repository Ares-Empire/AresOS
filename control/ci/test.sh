#!/bin/bash
# Shared setup and the full base suite, inside the disposable container.
set -euo pipefail
source control/ci/setup.sh
python3 control/generate.py --check
python3 control/ci/base.py
printf 'Control base suite PASS\n'
