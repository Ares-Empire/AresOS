#!/bin/bash
set -eu
cd /mnt/c/Users/pab/AresOS-14-owner-tools
export TMPDIR="$PWD/.work/14/local/tmp"
export PATH="$PWD/.work/14/local/bin:$PATH"
unset REHEARSAL_PACKAGE
python3 -B .work/14/14zy-walk.py > .work/14/14zy/final-walk.log 2>&1
python3 -B .work/14/14zy-probe-walk.py > .work/14/14zy/probe-walk.log 2>&1
python3 -B .work/14/14zy-syntax.py > .work/14/14zy/strict.log 2>&1
python3 -B .work/14/14zy/whole.py > .work/14/14zy/whole-suite.log 2>&1
