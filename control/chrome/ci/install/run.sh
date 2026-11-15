#!/bin/bash
# Entry of the install-proof container (brief 18c-b, item 2): `pack` runs pack.py's tests and the node
# cross-check, `proof` the five cases on the pinned Chrome. CI only.
set -euo pipefail
test "${GITHUB_ACTIONS:-}" = true
test -f /.dockerenv
test "$(uname -s)" = Linux
cd /workspace
case "${1:-}" in
  pack)
    python3 -c 'import cryptography, sys; print("python", sys.version.split()[0], "cryptography", cryptography.__version__)'
    python3 -B -m unittest discover -s control/chrome/ci/install -p 'test_*.py' -v
    node --version
    node --test control/chrome/ci/install/*.test.mjs
    ;;
  proof)
    exec python3 -B control/chrome/ci/install/proof.py
    ;;
  *)
    echo 'Usage: run.sh pack|proof' >&2
    exit 2
    ;;
esac
