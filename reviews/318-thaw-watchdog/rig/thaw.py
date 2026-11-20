#!/usr/bin/python3
"""Package 318: the thaw sampler and exit watcher. Read-only: it never signals, attaches to or changes the game.

    thaw.py <game pid> <rig> <keep|demote> [--hold SECONDS]

Started by lifecycle.sh's rig_thaw just before the thaw write; the write waits for <rig>/thaw-ready, which appears
after the first sample. Then:
  - every 10 ms, for each thread recorded at the freeze (rt-freeze.json) and any OpenAL Soft thread ("alsoft-*"):
    schedstat's first field (time on CPU, ns), voluntary and nonvoluntary context switches, state and policy, into
    thaw-samples.csv. Any sleep resets RLIMIT_RTTIME's count, and only a voluntary switch shows that the thread
    blocked: a 10 ms state sample can't see a short sleep;
  - every 100 ms, every thread of the game with a realtime policy, into thaw-scan.jsonl;
  - for 3 s (keep) or 10 s (demote), so the whole catch-up is measured; <rig>/thaw-sampled marks the end;
  - all along, a pidfd on the game until --hold seconds (60) after the return request. At the exit it reads the
    zombie's wait status from /proc/<pid>/stat (field 52, as package 49's observe-return.py did) and whether the rig's
    cleanup had already started (the cleanup_start mark), into exit.json.
It stops at the game's exit, at the hold deadline, or on SIGTERM (recorded as "stopped").
"""
import argparse
import json
import os
import pathlib
import select
import signal
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import records
import rt

TICK_NS = 10_000_000
SCAN_EVERY = 10  # ticks: 100 ms
WINDOW_S = {'keep': 3, 'demote': 10}
COLUMNS = 'monotonic_ns,tid,cpu_ns,voluntary,nonvoluntary,state,policy\n'


def marks(rig):
    found = {}
    try:
        for line in (rig / 'marks.txt').read_text().splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1].isdigit():
                found.setdefault(parts[0], int(parts[1]))
    except FileNotFoundError:
        pass
    return found


def sample(pid, tid):
    """One row for one thread, or None once the thread (or the game) is gone."""
    base = f'/proc/{pid}/task/{tid}/'
    try:
        with open(base + 'schedstat') as source:
            cpu = int(source.read().split()[0])
        switches = {}
        with open(base + 'status') as source:
            for line in source:
                key, _, value = line.partition(':')
                if key in ('voluntary_ctxt_switches', 'nonvoluntary_ctxt_switches'):
                    switches[key] = int(value)
        with open(base + 'stat') as source:
            stat = rt.parse_stat(source.read())
    except (FileNotFoundError, ProcessLookupError, IndexError, ValueError):
        return None
    return (f"{time.monotonic_ns()},{tid},{cpu},{switches.get('voluntary_ctxt_switches', '')},"
            f"{switches.get('nonvoluntary_ctxt_switches', '')},{stat['state']},{rt.policy_name(stat['policy'])}\n")


def watched(pid, rig):
    """The recorded realtime threads, plus any OpenAL Soft thread of the game (in case its mixer wasn't realtime)."""
    tids = {}
    try:
        recorded = json.loads((rig / 'rt-freeze.json').read_text())
        if recorded.get('pid') == pid:
            tids.update({t['tid']: True for t in recorded.get('realtime', [])})
    except (FileNotFoundError, ValueError):
        pass
    try:
        for tid, stat in rt.threads(pid):
            if stat['comm'].startswith('alsoft-'):
                tids.setdefault(tid, False)
    except OSError:
        pass
    return tids


def exit_status(pid, starttime):
    """The wait status of the game's zombie, before Gradle (its parent) reaps it."""
    try:
        fields = pathlib.Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
    except (FileNotFoundError, ProcessLookupError):
        return {'source': None, 'note': 'already reaped'}
    if fields[19] != starttime:
        return {'source': None, 'note': 'PID reused'}
    status = int(fields[49])
    found = {'source': 'zombie', 'state': fields[0], 'wait_status': status}
    if os.WIFSIGNALED(status):
        found.update(signal=os.WTERMSIG(status), exit_code=None)
    else:
        found.update(signal=None, exit_code=os.WEXITSTATUS(status))
    return found


def watch(pid, rig, mode, hold_s=60.0):
    rig = pathlib.Path(rig)
    start = time.monotonic_ns()
    seen = marks(rig)
    return_ns = seen.get('return_start', start)
    sample_end = start + WINDOW_S[mode] * 1_000_000_000
    hold_end = return_ns + int(hold_s * 1_000_000_000)
    record = {'pid': pid, 'mode': mode, 'watch_start_ns': start, 'return_start_ns': return_ns,
              'sample_end_ns': sample_end, 'hold_until_ns': hold_end, 'outcome': None}
    records.status(rig, 'thaw-watch-start')
    ticks = 0
    samples = (rig / 'thaw-samples.csv').open('w')
    scans = (rig / 'thaw-scan.jsonl').open('w')
    samples.write(COLUMNS)

    def stop(*_):
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, stop)
    try:
        try:
            fd = os.pidfd_open(pid)
            starttime = pathlib.Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19]
        except (ProcessLookupError, FileNotFoundError):
            record.update(outcome='gone at start', exit_detected_ns=start)
            return record
        tids = watched(pid, rig)
        record['sampled_threads'] = [{'tid': tid, 'recorded_realtime': recorded} for tid, recorded in tids.items()]
        next_tick = start
        sampling = True
        while True:
            now = time.monotonic_ns()
            if sampling and now >= sample_end:
                sampling = False
                samples.flush()
                records.status(rig, 'thaw-sample-end')
                (rig / 'thaw-sampled').write_text(f'{now}\n')
            if sampling and now >= next_tick:
                for tid in tids:
                    row = sample(pid, tid)
                    if row:
                        samples.write(row)
                if ticks % SCAN_EVERY == 0:
                    try:
                        found = rt.realtime(pid)
                        scans.write(json.dumps({'monotonic_ns': time.monotonic_ns(), 'realtime': found}) + '\n')
                        scans.flush()
                    except OSError:
                        pass
                ticks += 1
                if ticks == 1:
                    samples.flush()
                    (rig / 'thaw-ready').write_text(f'{time.monotonic_ns()}\n')
                # Keep the 10 ms grid; after a stall, resume from now rather than sampling in a burst.
                next_tick += TICK_NS
                if next_tick <= time.monotonic_ns():
                    next_tick = time.monotonic_ns() + TICK_NS
            now = time.monotonic_ns()
            if now >= hold_end and not sampling:
                record.update(outcome='alive', alive_at_ns=now, after_return_ms=round((now - return_ns) / 1e6, 3))
                return record
            wake = min(next_tick, sample_end) if sampling else hold_end
            if select.select([fd], [], [], max(0, wake - time.monotonic_ns()) / 1e9)[0]:
                detected = time.monotonic_ns()
                record.update(exit_status(pid, starttime))
                cleanup = marks(rig).get('cleanup_start')
                record.update(outcome='exited', exit_detected_ns=detected,
                              after_return_ms=round((detected - return_ns) / 1e6, 3),
                              after_watch_start_ms=round((detected - start) / 1e6, 3),
                              cleanup_start_ns=cleanup,
                              cleanup_started_before_exit=cleanup is not None and cleanup <= detected)
                return record
    finally:
        if record['outcome'] is None:
            record['outcome'] = 'stopped'
            record['stopped_ns'] = time.monotonic_ns()
        record['samples'] = ticks
        samples.close()
        scans.close()
        records.status(rig, 'thaw-watch-end')
        (rig / 'exit.json').write_text(json.dumps(record, indent=1) + '\n')
        for name in ('thaw-ready', 'thaw-sampled'):
            if not (rig / name).exists():
                (rig / name).write_text(f'{time.monotonic_ns()}\n')
        print(f"thaw watch: {record['outcome']} after {ticks} samples", flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('pid', type=int)
    parser.add_argument('rig')
    parser.add_argument('mode', choices=sorted(WINDOW_S))
    parser.add_argument('--hold', type=float, default=60.0)
    arguments = parser.parse_args()
    watch(arguments.pid, arguments.rig, arguments.mode, arguments.hold)
