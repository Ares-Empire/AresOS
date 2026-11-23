#!/usr/bin/python3
"""Package 318: the realtime threads of the rig's own frozen game.

    rt.py record <game pid> <game unit> <rig>          after the freeze is confirmed (both RT modes)
    rt.py demote <game pid> <game unit> <rig>          RT=demote, right after record
    rt.py check  <game pid> <game unit> <rig> <mode>   just before the thaw write; exit 3 = INVALID (demote only)

Each command first requires the exact game scope this run created (scope.owned_scope); record and demote also require
it to be frozen. While the game is frozen none of its threads can end, start or ask rtkit for realtime, so a thread ID
checked here can't be reused before the policy change, and the recorded set is exactly the set that is thawed.

Demotion uses `chrt --reset-on-fork --other --pid 0 <tid>`. rtkit grants SCHED_RR|SCHED_RESET_ON_FORK, and only a
CAP_SYS_NICE caller may clear that flag, so a plain `chrt --other` gets EPERM on exactly the threads it targets
(brief review 1, finding 1). Before each change the thread's Tgid (from /proc/<tid>/status, the same global lookup the
kernel's sched_setscheduler uses) must be the game PID. The only policy changes are on threads of the game.
"""
import json
import os
import pathlib
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

PROC = pathlib.Path('/proc')
POLICIES = {0: 'SCHED_OTHER', 1: 'SCHED_FIFO', 2: 'SCHED_RR', 3: 'SCHED_BATCH', 5: 'SCHED_IDLE', 6: 'SCHED_DEADLINE'}
REALTIME = {1, 2}
RESET_ON_FORK = 0x40000000  # os.SCHED_RESET_ON_FORK, as sched_getscheduler(2) reports it
DEMOTE = ['/usr/bin/chrt', '--reset-on-fork', '--other', '--pid', '0']
INVALID = 3


def parse_stat(text):
    """comm, state, rt_priority and policy from a /proc/<pid>/task/<tid>/stat line (proc(5) fields 2, 3, 40, 41).

    The comm sits in parentheses and may itself hold spaces and parentheses, so the fields start after the last ')'."""
    head, rest = text.rsplit(')', 1)
    fields = rest.split()
    return {'comm': head.split('(', 1)[1], 'state': fields[0], 'rt_priority': int(fields[37]), 'policy': int(fields[38])}


def policy_name(value):
    return POLICIES.get(value & ~RESET_ON_FORK, str(value & ~RESET_ON_FORK))


def threads(pid, proc=PROC):
    """(tid, parsed stat) for every thread of pid, by thread ID. A thread that ends while being read is skipped."""
    found = []
    for task in sorted((proc / str(pid) / 'task').iterdir(), key=lambda path: int(path.name)):
        try:
            found.append((int(task.name), parse_stat((task / 'stat').read_text())))
        except (FileNotFoundError, ProcessLookupError):
            pass
    return found


def describe(tid, stat, getscheduler=os.sched_getscheduler):
    entry = {'tid': tid, 'comm': stat['comm'], 'policy': policy_name(stat['policy']), 'priority': stat['rt_priority']}
    try:
        raw = getscheduler(tid)
        entry['flags'] = ['SCHED_RESET_ON_FORK'] if raw & RESET_ON_FORK else []
    except OSError as error:
        entry['flags_error'] = repr(error)
    return entry


def realtime(pid, proc=PROC, getscheduler=os.sched_getscheduler):
    """Every thread of pid whose policy is SCHED_FIFO or SCHED_RR."""
    return [describe(tid, stat, getscheduler) for tid, stat in threads(pid, proc) if stat['policy'] in REALTIME]


def tgid(tid, proc=PROC):
    for line in (proc / str(tid) / 'status').read_text().splitlines():
        if line.startswith('Tgid:'):
            return int(line.split()[1])
    raise ValueError(f'no Tgid for thread {tid}')


def demote(pid, tid, proc=PROC, run=subprocess.run, getscheduler=os.sched_getscheduler):
    """Set one thread of pid to SCHED_OTHER and keep its reset-on-fork flag. Refuses a thread of any other process."""
    owner = tgid(tid, proc)
    if owner != pid:
        raise PermissionError(f'thread {tid} belongs to process {owner}, not to the game {pid}')
    command = [*DEMOTE, str(tid)]
    before = getscheduler(tid)
    result = run(command, capture_output=True, text=True, timeout=5)
    after = getscheduler(tid)
    return {'tid': tid, 'command': ' '.join(command), 'exit': result.returncode, 'stderr': result.stderr.strip(),
            'before': policy_name(before), 'before_reset_on_fork': bool(before & RESET_ON_FORK),
            'after': policy_name(after), 'after_reset_on_fork': bool(after & RESET_ON_FORK)}


def frozen(group):
    events = dict(line.split() for line in (group / 'cgroup.events').read_text().splitlines())
    return events.get('frozen') == '1'


def write(rig, name, record):
    (pathlib.Path(rig) / name).write_text(json.dumps(record, indent=1) + '\n')


def main(argv):
    from scope import owned_scope
    command, pid, unit, rig = argv[0], int(argv[1]), argv[2], pathlib.Path(argv[3])
    group = owned_scope(pid, unit)
    is_frozen = frozen(group)
    record = {'monotonic_ns': time.monotonic_ns(), 'pid': pid, 'frozen': is_frozen}
    if command in ('record', 'demote') and not is_frozen:
        raise RuntimeError(f'rt.py {command} runs only while the game scope is frozen')
    if command == 'record':
        record['threads'] = len(threads(pid))
        record['realtime'] = realtime(pid)
        # Expected: "Max realtime timeout 200000 200000 us" (OpenAL Soft sets soft = hard = rtkit's RTTimeUSecMax).
        record['limits'] = (PROC / str(pid) / 'limits').read_text()
        write(rig, 'rt-freeze.json', record)
        print(f"rt record: {len(record['realtime'])} realtime of {record['threads']} threads", flush=True)
        return 0
    if command == 'demote':
        recorded = json.loads((rig / 'rt-freeze.json').read_text())
        if recorded['pid'] != pid:
            raise ValueError('rt-freeze.json belongs to another game PID')
        record['results'] = []
        for thread in recorded['realtime']:
            try:
                record['results'].append(demote(pid, thread['tid']))
            except FileNotFoundError:
                # Can't happen while frozen; recorded rather than skipped, and the pre-thaw check still decides.
                record['results'].append({'tid': thread['tid'], 'error': 'thread gone'})
        record['end_monotonic_ns'] = time.monotonic_ns()
        record['realtime_after'] = realtime(pid)
        write(rig, 'rt-demote.json', record)
        print(f"rt demote: {len(record['results'])} demoted, {len(record['realtime_after'])} still realtime", flush=True)
        return 0
    if command == 'check':
        mode = argv[4]
        if mode not in ('keep', 'demote'):
            raise ValueError('mode: keep or demote')
        record['mode'] = mode
        record['realtime'] = realtime(pid)
        record['invalid'] = mode == 'demote' and bool(record['realtime'])
        write(rig, 'rt-prethaw.json', record)
        print(f"rt check ({mode}): {len(record['realtime'])} realtime{'; INVALID' if record['invalid'] else ''}", flush=True)
        return INVALID if record['invalid'] else 0
    raise ValueError('command: record, demote or check')


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
