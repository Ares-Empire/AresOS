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
WORK = HERE.parents[2]/'.work/pkg318/lifecycle'
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
exec systemd-run --user --scope --quiet --collect --unit="pkg318-rig-$$" -- python3 -I "$1" "$RIG"
''')
(WORK/'trial.sh').write_text(f'''#!/usr/bin/bash
set -euo pipefail
here={shlex.quote(str(HERE))}
WT={shlex.quote(str(HERE.parents[2]))}
RIG=$1
export RIG
PKG49_GAME_UNIT="pkg318-game-failure-$2-$$.scope"
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
if [[ $2 == compositor ]]; then
    python3 -I -c 'import os,pathlib,time; pathlib.Path(os.environ["RIG"],"foreground-pid").write_text(str(os.getpid())); time.sleep(300)'
fi
if [[ $2 == frozen-* || $2 == invalid || $2 == normal ]]; then
    # Package 318: stand-ins log each scope and rt request; nothing writes a real cgroup.freeze or policy here.
    rig_scope() {{ echo "$3 $(mono)" >>"$RIG/scope-calls"; }}
    rig_rt() {{ echo "rt-$1 $(mono)" >>"$RIG/scope-calls"; [[ $1 == check ]] || return 0; return "$RT_CHECK"; }}
    RT=demote RT_CHECK=0 PKG318_THAW_HOLD=1
    # As in a real run, an INVALID run's watcher holds past the 10 s sampling and sees the cleanup end the game.
    [[ $2 != invalid ]] || {{ RT_CHECK=3; PKG318_THAW_HOLD=30; }}
    game=$(<"$RIG/game-pid")
    frozen=1
    rig_scope "$game" "$PKG49_GAME_UNIT" freeze "$RIG"
    rig_rt record "$game" "$PKG49_GAME_UNIT" "$RIG"
    mark frozen_ready
    case $2 in
        frozen-error) false ;;
        invalid|normal)
            mark return_start
            rig_return_thaw
            rig_hold
            mark done
            exit 0 ;;
    esac
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
            if scenario=='compositor': until(lambda: (rig/'foreground-pid').exists())
            peers=[int(p) for p in (rig/'peer-pids').read_text().split()]
            game=int((rig/'game-pid').read_text())
            owned=[*peers,game]
            if scenario=='compositor':owned.append(int((rig/'foreground-pid').read_text()))
            fds=[os.pidfd_open(p) for p in owned]
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
            units=subprocess.check_output(['systemctl','--user','list-units','--all','--plain','--no-legend',game_unit,'pkg318-rig-*'],text=True)
            assert not units.strip(), units
            failure=json.loads((rig/'health-failure.json').read_text())
            row={'scenario':scenario,'exit':code,'seconds':round(elapsed,3),'all_owned_processes_exited':True,'scopes_gone':True,'lock_free':True,'reason':failure['reason']}
            results.append(row)
            print(f'{scenario}: PASS exit {code}, processes/scopes gone, lock free ({elapsed:.3f}s)',flush=True)
        finally:
            if proc.poll() is None:
                proc.terminate();proc.wait(timeout=30)


def calls(rig):
    return [line.split() for line in (rig/'scope-calls').read_text().splitlines()]


# Package 318: thaw on every exit path. Each scenario freezes (a stand-in request), then ends one way. Required: exactly
# one thaw after the freeze, through the real watcher, before cleanup stopped the stand-in game; the exit watcher saw the
# exit and whether cleanup had started; no process, scope or lock left behind.
expected = {'frozen-health': ('exited', True), 'frozen-term': ('exited', True), 'frozen-error': ('exited', True),
            'invalid': ('exited', True), 'normal': ('alive', None)}
for scenario, (outcome, after_cleanup) in expected.items():
    rig=WORK/(scenario+'-'+str(os.getpid()))
    rig.mkdir()
    with (rig/'output.txt').open('w') as out:
        proc=subprocess.Popen(['bash',str(WORK/'trial.sh'),str(rig),scenario],stdout=out,stderr=subprocess.STDOUT)
        try:
            until(lambda: (rig/'marks.txt').exists() and 'frozen_ready' in (rig/'marks.txt').read_text())
            peers=[int(p) for p in (rig/'peer-pids').read_text().split()]
            game=int((rig/'game-pid').read_text())
            fds=[]
            for pid in (*peers,game):
                try: fds.append(os.pidfd_open(pid))
                except ProcessLookupError: pass  # frozen-error may already have cleaned up
            start=time.monotonic()
            if scenario=='frozen-health':
                target=os.pidfd_open(peers[1]); signal.pidfd_send_signal(target,signal.SIGKILL); os.close(target)
            elif scenario=='frozen-term':
                proc.send_signal(signal.SIGTERM)
            code=proc.wait(timeout=30)
            elapsed=time.monotonic()-start
            want_code={'invalid':3,'normal':0}.get(scenario)
            assert (code==want_code) if want_code is not None else code!=0, (scenario,'exit',code)
            assert all(select.select([fd],[],[],2)[0] for fd in fds), (scenario,'owned process remains')
            for fd in fds: os.close(fd)
            with (rig/'test.lock').open('a') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            game_unit=(rig/'game-unit').read_text().strip()
            units=subprocess.check_output(['systemctl','--user','list-units','--all','--plain','--no-legend',game_unit,'pkg318-rig-*'],text=True)
            assert not units.strip(), units
            log=calls(rig)
            actions=[c[0] for c in log if not c[0].startswith('rt-')]
            assert actions==['freeze','thaw'], (scenario,actions)
            thaw_ns=int(next(c[1] for c in log if c[0]=='thaw'))
            ready_ns=int((rig/'thaw-ready').read_text())
            assert ready_ns<=thaw_ns, (scenario,'watcher not sampling before the thaw')
            record=json.loads((rig/'exit.json').read_text())
            assert record['outcome']==outcome, (scenario,record)
            marks=dict(line.split() for line in (rig/'marks.txt').read_text().splitlines())
            assert 'cleanup_start' in marks, scenario
            if outcome=='exited':
                assert record['exit_detected_ns']>thaw_ns, (scenario,'game ended before its thaw')
                assert record['cleanup_started_before_exit'] is after_cleanup, (scenario,record)
            if scenario=='invalid':
                assert 'invalid' in marks and json.loads((rig/'invalid.json').read_text())['reason'], scenario
                assert ('rt-check' in [c[0] for c in log]), scenario
                assert (rig/'thaw-sampled').exists(), scenario
            if scenario=='normal':
                assert 'held' in marks and int(marks['held'])<int(marks['cleanup_start']), scenario
            row={'scenario':scenario,'exit':code,'seconds':round(elapsed,3),'requests':actions,'thaw_after_watcher_ready':True,
                 'exit_watcher':record['outcome'],'cleanup_started_before_exit':record.get('cleanup_started_before_exit'),
                 'all_owned_processes_exited':True,'scopes_gone':True,'lock_free':True}
            results.append(row)
            print(f'{scenario}: PASS exit {code}, one thaw after the watcher was ready, watcher {record["outcome"]}, '
                  f'processes/scopes gone, lock free ({elapsed:.3f}s)',flush=True)
        finally:
            if proc.poll() is None:
                proc.terminate();proc.wait(timeout=30)
(HERE.parent/'verification').mkdir(exist_ok=True)
(HERE.parent/'verification/lifecycle.json').write_text(json.dumps(results,indent=2)+'\n')
