#!/bin/bash
set -eu
cd /mnt/c/Users/pab/AresOS-14-owner-tools
export TMPDIR="$PWD/.work/14/local/tmp"
export PATH="$PWD/.work/14/local/bin:$PATH"
unset REHEARSAL_PACKAGE
python3 -B .work/14/14zzb-walk.py > .work/14/14zzb/final-walk.log 2>&1
python3 -B .work/14/14zzb-probe-walk.py > .work/14/14zzb/probe-walk.log 2>&1
python3 -B .work/14/14zzb-syntax.py > .work/14/14zzb/strict.log 2>&1
python3 -B .work/14/14zzb/whole.py > .work/14/14zzb/whole-suite.log 2>&1
