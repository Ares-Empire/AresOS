"""Real user scopes, FIFO stand-ins and the production lifecycle. No game, CUDA or owner display."""
import fcntl
import json
import os
from pathlib import Path
import select
import shlex
import signal
import subprocess
import time

HERE = Path(__file__).resolve().parent
WORK = HERE.parents[2]/'.work/pkg49b/lifecycle'
WORK.mkdir(parents=True, exist_ok=True)
# The starter execs systemd-run, as start.sh does. A second scope stands in for the game.
(WORK/'peers.py').write_text('''import os, pathlib, subprocess, sys, time
rig=pathlib.Path(sys.argv[1])
os.mkfifo(rig/'vin')
reader=subprocess.Popen([sys.executable,'-I','-c',"import sys,time;\\nwhile True:\\n with open(sys.argv[1]) as f:\\n  for line in f: time.sleep(.01)",str(rig/'vin')])
child=subprocess.Popen(['sleep','300'])
(rig/'env').write_text(f'LABWC_PID={os.getpid()}\\nVINPUT_PID={reader.pid}\\n')
(rig/'peer-pids').write_text(f'{os.getpid()} {reader.pid} {child.pid}')
while True: time.sleep(1)
''')
(WORK/'game.py').write_text("import os,pathlib,time; pathlib.Path(os.environ['RIG'],'game-pid').write_text(str(os.getpid())); time.sleep(300)")
(WORK/'start.sh').write_text('''#!/usr/bin/bash
exec systemd-run --user --scope --quiet --collect --unit="pkg49b-rig-$$" -- python3 -I "$1" "$RIG"
''')
(WORK/'trial.sh').write_text(f'''#!/usr/bin/bash
set -euo pipefail
here={shlex.quote(str(HERE))}
WT={shlex.quote(str(HERE.parents[2]))}
RIG=$1
export RIG
PKG49_GAME_UNIT="pkg49b-game-failure-$2-$$.scope"
export PKG49_GAME_UNIT
echo "$PKG49_GAME_UNIT" >"$RIG/game-unit"
exec {{lock}}>>"$RIG/test.lock"
flock -n "$lock"
source "$here/lifecycle.sh"
rig_start bash {shlex.quote(str(WORK/'start.sh'))} {shlex.quote(str(WORK/'peers.py'))}
systemd-run --user --scope --quiet --collect --unit="$PKG49_GAME_UNIT" -- python3 -I {shlex.quote(str(WORK/'game.py'))} &
while [[ ! -e $RIG/peer-pids || ! -e $RIG/game-pid ]]; do sleep .02; done
mark stand_ready
# Open a FIFO writer during a flight; the reader's death must also abort a long sleep with no next write.
if [[ $2 == flight ]]; then
    vin key w down
    mark flight_start
fi
sleep 300
vin rel 200 0 15
exit 0
''')


def until(predicate, seconds=10):
    deadline=time.monotonic()+seconds
    while not predicate():
        assert time.monotonic()<deadline, 'stand-in readiness timeout'
        time.sleep(.02)


results=[]
for scenario in ('standing','flight','compositor'):
    rig=WORK/(scenario+'-'+str(os.getpid()))
    rig.mkdir()
    with (rig/'output.txt').open('w') as out:
        proc=subprocess.Popen(['bash',str(WORK/'trial.sh'),str(rig),scenario],stdout=out,stderr=subprocess.STDOUT)
        try:
            until(lambda: (rig/'marks.txt').exists() and ('flight_start' if scenario=='flight' else 'stand_ready') in (rig/'marks.txt').read_text())
            peers=[int(p) for p in (rig/'peer-pids').read_text().split()]
            game=int((rig/'game-pid').read_text())
            fds=[os.pidfd_open(p) for p in [*peers,game]]
            target=peers[0 if scenario=='compositor' else 1]
            targetfd=os.pidfd_open(target)
            start=time.monotonic()
            signal.pidfd_send_signal(targetfd,signal.SIGKILL)
            os.close(targetfd)
            code=proc.wait(timeout=12)
            elapsed=time.monotonic()-start
            assert code!=0, (scenario,'silent success')
            assert elapsed<10, (scenario,elapsed)
            assert all(select.select([fd],[],[],1)[0] for fd in fds), (scenario,'owned process remains')
            for fd in fds: os.close(fd)
            with (rig/'test.lock').open('a') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            game_unit=(rig/'game-unit').read_text().strip()
            units=subprocess.check_output(['systemctl','--user','list-units','--all','--plain','--no-legend',game_unit,'pkg49b-rig-*'],text=True)
            assert not units.strip(), units
            failure=json.loads((rig/'health-failure.json').read_text())
            row={'scenario':scenario,'exit':code,'seconds':round(elapsed,3),'all_owned_processes_exited':True,'scopes_gone':True,'lock_free':True,'reason':failure['reason']}
            results.append(row)
            print(f'{scenario}: PASS exit {code}, processes/scopes gone, lock free ({elapsed:.3f}s)',flush=True)
        finally:
            if proc.poll() is None:
                proc.terminate();proc.wait(timeout=30)
(HERE.parent/'verification/lifecycle.json').write_text(json.dumps(results,indent=2)+'\n')
