#!/bin/bash
set -eu
cd /mnt/c/Users/pab/AresOS-14-owner-tools
export TMPDIR="$PWD/.work/14/local/tmp"
export PATH="$PWD/.work/14/local/bin:$PATH"
unset REHEARSAL_PACKAGE
python3 -B .work/14/14zz-walk.py > .work/14/14zz/final-walk.log 2>&1
python3 -B .work/14/14zz-probe-walk.py > .work/14/14zz/probe-walk.log 2>&1
python3 -B .work/14/14zz-syntax.py > .work/14/14zz/strict.log 2>&1
python3 -B .work/14/14zz/whole.py > .work/14/14zz/whole-suite.log 2>&1
