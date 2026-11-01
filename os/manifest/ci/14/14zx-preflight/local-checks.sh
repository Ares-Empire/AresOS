#!/bin/bash
set -eu
cd /mnt/c/Users/pab/AresOS-14-owner-tools
export TMPDIR="$PWD/.work/14/local/tmp"
export PATH="$PWD/.work/14/local/bin:$PATH"
unset REHEARSAL_PACKAGE
python3 -B .work/14/14zx-walk.py > .work/14/14zx/final-walk.log 2>&1
python3 -B .work/14/14zx-probe-walk.py > .work/14/14zx/probe-walk.log 2>&1
python3 -B .work/14/14zx-syntax.py > .work/14/14zx/strict.log 2>&1
python3 -B .work/14/14zx/whole.py > .work/14/14zx/whole-suite.log 2>&1
