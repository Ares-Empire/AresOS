#!/usr/bin/python3
"""Cover actions on the live game scope this run created; no ancestor or unrelated cgroup writes."""
import json, os, pathlib, re, subprocess, sys, time


def owned_scope(pid, unit):
    if not re.fullmatch(r'pkg49-game-[a-z0-9-]+-\d+\.scope', unit):
        raise ValueError('not a package 49 game scope')
    actual = next(line.split('::', 1)[1].strip() for line in pathlib.Path(f'/proc/{pid}/cgroup').read_text().splitlines()
                  if line.startswith('0::'))
    wanted = subprocess.check_output(['systemctl', '--user', 'show', '-P', 'ControlGroup', unit], text=True).strip()
    if not wanted or actual != wanted or pathlib.PurePosixPath(actual).name != unit:
        raise ValueError('PID is not in the exact scope this run created')
    group = pathlib.Path('/sys/fs/cgroup') / actual.lstrip('/')
    if str(pid) not in (group / 'cgroup.procs').read_text().split():
        raise ValueError('game PID left its scope')
    return group


def jcmd(pid, command):
    executable = pathlib.Path(os.environ.get('JAVA_HOME', os.path.expanduser('~/.local/opt/jdk-25'))) / 'bin/jcmd'
    run = subprocess.run([str(executable), str(pid), command], capture_output=True, text=True, timeout=60)
    return {'command': command, 'exit': run.returncode, 'stdout': run.stdout, 'stderr': run.stderr}


def action(pid, unit, what, out):
    group = owned_scope(pid, unit)
    record = {'action': what, 'monotonic_ns': time.monotonic_ns(), 'pid': pid, 'scope': unit}
    try:
        if what == 'gc-trim':
            record['commands'] = [jcmd(pid, 'GC.run'), jcmd(pid, 'System.trim_native_heap')]
            if any(c['exit'] for c in record['commands']):
                raise RuntimeError('jcmd cover action failed')
        elif what.startswith('reclaim:'):
            amount = what.split(':', 1)[1]
            if amount not in {'300M', '600M'}:
                raise ValueError('only planned reclaim amounts allowed')
            # EAGAIN means a partial reclaim, not a successful request. Preserve it and both endpoints.
            record['before'] = {n: (group / n).read_text().strip() for n in ('memory.current', 'memory.swap.current')}
            try:
                (group / 'memory.reclaim').write_text(amount + ' swappiness=max\n')
                record['result'] = 'completed'
            except OSError as error:
                record['result'] = 'error'
                record['errno'] = error.errno
                record['error'] = str(error)
                if error.errno != 11:
                    raise
            record['after'] = {n: (group / n).read_text().strip() for n in ('memory.current', 'memory.swap.current')}
        elif what in {'freeze', 'thaw'}:
            (group / 'cgroup.freeze').write_text('1\n' if what == 'freeze' else '0\n')
            deadline = time.monotonic() + 10
            while True:
                events = dict(line.split() for line in (group / 'cgroup.events').read_text().splitlines())
                if events['frozen'] == ('1' if what == 'freeze' else '0'):
                    break
                if time.monotonic() > deadline:
                    raise TimeoutError('freezer did not reach requested state')
                time.sleep(.02)
            record['result'] = 'confirmed'
        else:
            raise ValueError('unknown action')
    except Exception as error:
        record['failure'] = repr(error)
        raise
    finally:
        record['end_monotonic_ns'] = time.monotonic_ns()
        with (pathlib.Path(out) / 'actions.jsonl').open('a') as sink:
            sink.write(json.dumps(record) + '\n')
        print(json.dumps(record), flush=True)


if __name__ == '__main__':
    action(int(sys.argv[1]), *sys.argv[2:])
