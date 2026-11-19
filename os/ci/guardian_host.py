"""Package 25, the guardian: the host's side of the check build's VM proof (brief 25, Acceptance: the VM).

vm.py's two passes are the brief's two boots. Pass 1 (`save`): the power key with a save that takes 5 s, a peer
that never reads, a lid event during the save and no app window open. Pass 2 (`hang`): a game that never answers
and ignores SIGTERM. The guest's side is os/ci/overlay/guardian.py; `watch` runs between the power key and the
power-off, `check` afterwards on the stopped guest's journal (offline-boot.jsonl, read from its disk by
offline_journal.py). Times are the journal's monotonic times; the probe's are the same clock.
"""
import json
import pathlib
import re
import time

SCENARIOS = {'1': 'save', '2': 'hang'}
GUARD = 'aresos-guardian.service'
GAME_UNIT = 'aresos-ci-game.service'
# The lead's fix 6: the guard unit's limit, the game scope's limit, and a margin.
POWER_OFF_BOUND = 85 + 15 + 20
# A black frame: at most this share of its pixels is brighter than BLACK_LEVEL (a pointer the size of 24 x 24).
BLACK_LEVEL = 8
BLACK_SHARE = 0.001
SAVE_SECONDS = 5.0


def scenario(vm_pass):
    return SCENARIOS[str(vm_pass)]


def lit_share(path):
    """The share of a picture's pixels that are not black."""
    from PIL import Image  # vm.py's own dependency; the journal check below needs none
    with Image.open(path) as image:
        extrema = image.convert('L').point(lambda value: 255 if value > BLACK_LEVEL else 0).histogram()
    return extrema[255] / max(1, sum(extrema))


def watch(kind, camera, running, screenshot, keys, evidence):
    """Keep any live observation failure for check(), so the caller can always read the stopped guest's journal."""
    try:
        result = capture(kind, camera, running, screenshot, keys, evidence)
    except Exception as error:
        # This includes QMP disappearing mid-frame. A missing black frame fails the offline check.
        result = dict(black=False, error=f'{type(error).__name__}: {error}')
    (evidence / 'guardian-watch.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def capture(kind, camera, running, screenshot, keys, evidence):
    """Photograph the screen between the fixture receiving save_world and sending its answer. The journal
    follower and systemd share ttyS0, so only the fixture's dedicated virtio port cues the camera."""
    began = time.monotonic()
    saving = b'ready\nsaving\n'
    while not camera.read_bytes().startswith(saving):
        assert running(), 'the VM powered off before the host saw the fixture\'s saving marker'
        assert time.monotonic() - began < 60, 'no saving marker within 60 s of the power key'
        time.sleep(0.1)
    asked = time.monotonic() - began
    # The save takes 5 s in the first boot and never ends in the second: the black screen must be up inside that.
    limit = time.monotonic() + (4.0 if kind == 'save' else 15.0)
    shares = []
    while True:
        screenshot('guardian-black.png')
        assert camera.read_bytes() == saving, 'the fixture save window ended before the frame was captured'
        share = lit_share(evidence / 'guardian-black.png')
        shares.append(round(share, 5))
        if share <= BLACK_SHARE or time.monotonic() >= limit:
            break
        time.sleep(0.2)
    result = dict(save_asked_after=round(asked, 2), black_lit_shares=shares, black=share <= BLACK_SHARE,
                  black_after=round(time.monotonic() - began, 2))
    if kind == 'hang' and running():
        keys(['ctrl', 'alt', 'f3'])
        result['console_key_sent_after'] = round(time.monotonic() - began, 2)
        time.sleep(3)
        if running():
            screenshot('guardian-tty3.png')
    return result


def text(record, key='MESSAGE'):
    value = record.get(key)
    return value if isinstance(value, str) else ''


def stamp(record):
    return int(record['__MONOTONIC_TIMESTAMP'])


def tagged(records, identifier, tag):
    """(time, parsed JSON) of every line a watcher wrote with this tag."""
    found = []
    for record in records:
        if record.get('SYSLOG_IDENTIFIER') == identifier and text(record).startswith(tag + ' '):
            try:
                found.append((stamp(record), json.loads(text(record)[len(tag) + 1:])))
            except ValueError:
                pass
    return found


def check(evidence, kind, armed, watched, seconds, before_lit):
    """The proof, from the stopped guest's journal. Returns the summary it also writes to guardian.json."""
    evidence = pathlib.Path(evidence)
    journal = evidence / 'offline-boot.jsonl'
    assert journal.is_file(), ('the guard cannot be proven without the guest\'s offline journal '
                               '(offline_journal.py reported it unreadable)')
    records = [json.loads(line) for line in journal.read_text(errors='replace').splitlines() if line.strip()]
    records = [record for record in records if '__MONOTONIC_TIMESTAMP' in record]
    records.sort(key=stamp)

    def first(what, predicate, after=0, required=True):
        for record in records:
            if stamp(record) >= after and predicate(record):
                return stamp(record)
        assert not required, f'the offline journal has no record of: {what}'
        return None

    def systemd(record, unit):
        return record.get('_PID') == '1' and record.get('UNIT') == unit

    def game(marker):
        pattern = re.compile('GUARDIAN_GAME ' + marker)
        return lambda r: r.get('SYSLOG_IDENTIFIER') == 'aresos-ci-game' and pattern.fullmatch(text(r))

    def began_to_stop(unit, after):
        return first(f'{unit} begins to stop', lambda r: systemd(r, unit) and text(r).startswith(
            ('Stopping ', 'Unmounting ')), after, required=False)

    key = first('the power key', lambda r: text(r) == 'Power key pressed short.')
    guard_began = first('the guard\'s stop begins', lambda r: systemd(r, GUARD) and text(r).startswith('Stopping '), key)
    guard_ended = first('the guard\'s stop ends', lambda r: systemd(r, GUARD) and r.get('JOB_TYPE') == 'stop'
                        and 'JOB_RESULT' in r, guard_began)
    save_request = game(r'save_asked id=[0-9]+')
    request = next((r for r in records if stamp(r) >= guard_began and save_request(r)), None)
    assert request is not None, 'the offline journal has no fixture save request after the guard began to stop'
    asked, request_id = stamp(request), text(request).rsplit('=', 1)[1]
    java_exit = first('the game\'s wrapper ends', lambda r: systemd(r, GAME_UNIT) and 'EXIT_STATUS' in r, guard_began)
    java_status = next(r['EXIT_STATUS'] for r in records if stamp(r) == java_exit and systemd(r, GAME_UNIT)
                       and 'EXIT_STATUS' in r)
    recovery = ('polkit.service', 'getty@tty3.service')
    others = (armed['session_scope'], 'greetd.service', 'user@1001.service', armed['home_mount'], *recovery)
    stops = {unit: began_to_stop(unit, key) for unit in others}
    stopped = {unit: first(f'{unit} stopped', lambda r: systemd(r, unit) and r.get('JOB_TYPE') == 'stop'
                           and r.get('JOB_RESULT') == 'done', key, required=False) for unit in recovery}
    shutdown = first('shutdown.target reached', lambda r: systemd(r, 'shutdown.target') and r.get('JOB_TYPE') == 'start'
                     and r.get('JOB_RESULT') == 'done', key, required=False)
    samples = tagged(records, 'aresos-ci-probe', 'GUARDIAN_PROBE')
    samples = [(int(sample['t'] * 1_000_000), sample) for _, sample in samples if isinstance(sample.get('t'), (int, float))]
    labwc_gone = min((when for when, sample in samples if when >= key and not sample['labwc']), default=None)
    recorded = [value for when, value in tagged(records, 'aresos-ci-record', 'GUARDIAN_RECORD') if when >= guard_ended]
    assert recorded, 'the stop record was not read after the guard\'s stop ended'
    record = recorded[0]
    stop = record.get('stop') or {}
    # What the guard's command printed (the supervisor's reply): its stream belongs to the guard unit.
    said = ' '.join(text(r) for r in records if guard_began <= stamp(r) <= guard_ended and r.get('_PID') != '1'
                    and (r.get('_SYSTEMD_UNIT') == GUARD or r.get('SYSLOG_IDENTIFIER') == 'aresos-desktop'))

    def seconds_after_key(value):
        return None if value is None else round((value - key) / 1_000_000, 3)

    summary = dict(scenario=kind, power_off_seconds=round(seconds, 1), guard_stop_began=seconds_after_key(guard_began),
                   save_asked=seconds_after_key(asked), java_exited=seconds_after_key(java_exit),
                   java_status=java_status, guard_stop_ended=seconds_after_key(guard_ended),
                   guard_stop_seconds=round((guard_ended - guard_began) / 1_000_000, 3),
                   began_to_stop={unit: seconds_after_key(when) for unit, when in stops.items()},
                   recovery_stopped={unit: seconds_after_key(when) for unit, when in stopped.items()},
                   shutdown_target=seconds_after_key(shutdown),
                   labwc_gone=seconds_after_key(labwc_gone), record=record, guard_said=said[:500],
                   black=watched, frame_before_lit_share=round(before_lit, 5), armed=armed)
    (evidence / 'guardian.json').write_text(json.dumps(summary, indent=2) + '\n')

    # Common to both boots.
    assert not [r for r in records if 'ordering cycle' in text(r).lower()], 'systemd found an ordering cycle'
    assert seconds <= POWER_OFF_BOUND, f'power-off took {seconds:.0f} s, more than {POWER_OFF_BOUND} s'
    assert key < guard_began < asked < guard_ended, summary
    # Only after the guard's stop ended did anything it guards begin to stop.
    for unit, when in stops.items():
        assert when is None or when > guard_ended, (f'{unit} began to stop before the guard\'s stop ended', summary)
    assert stops[armed['session_scope']] is not None and stops['user@1001.service'] is not None, summary
    # The stopped guest's journal must contain both completions. It can close before the final shutdown targets.
    for unit, end in stopped.items():
        assert stops[unit] is not None and end is not None and stops[unit] <= end, (f'missing stop for {unit}', summary)
        assert shutdown is None or end < shutdown, (f'{unit} stopped after shutdown.target', summary)
    assert labwc_gone is None or labwc_gone > guard_ended, ('labwc ended before the guard\'s stop ended', summary)
    # While the guard's stop ran, the probe saw all of them, the game's wrapper and the socket, and the home writable.
    # A sample's answers are up to a moment older than its time, and the stop ends a moment before the guard's
    # stop does: the first second and the last are left out.
    second = 1_000_000
    during = [sample for when, sample in samples
              if asked + second <= when <= (java_exit - second // 2 if kind == 'save' else guard_ended - second)]
    assert len(during) >= 3, ('the probe has too few samples from the stop', len(during))
    for sample in during:
        assert sample['labwc'] and sample['wrapper'] and sample['socket'] and sample['home'], sample
        assert all(sample['units'].get(name) == 'active' for name in ('session', 'greetd', 'user', 'home_mount')), sample
        assert sample['stopping'], ('the supervisor answered that no stop runs', sample)
    # Black: the host's frame during the save, the black window, and the supervisor's own word; not before the key.
    assert watched['black'], ('the screen was not black during the save', watched)
    expected_cues = b'ready\nsaving\n' + (b'answering\n' if kind == 'save' else b'')
    assert (evidence / 'guardian-camera.log').read_bytes() == expected_cues, 'incomplete or unexpected fixture camera cues'
    assert before_lit > 0.01, ('the frame before the power key was black already, so black proves nothing', before_lit)
    assert any(sample['black'] and sample['black_window'] for sample in during), 'no black window during the stop'
    # The lid block, from the supervisor's own context: its word, and logind's list when the lid watcher ran.
    summary['lid_block_held'] = any(sample['lid_block'] for sample in during)
    assert not [r for r in records if stamp(r) >= key and (
        r.get('SYSLOG_IDENTIFIER') == 'systemd-sleep' or text(r).startswith(('Suspending', 'Hibernating'))
        or (text(r).startswith('Reached target') and 'leep' in text(r)))], 'the machine began to sleep'

    if kind == 'save':
        answered = first('the game answers the same save', game(f'save_answered id={request_id}'), asked)
        closing = first('the game closes on SIGTERM', game('closing'), answered)
        assert (answered - asked) / 1_000_000 >= SAVE_SECONDS - 0.5, ('the save did not take its 5 s', summary)
        assert answered < closing <= java_exit < guard_ended, summary
        assert java_status == '143', ('Java did not end with 143 after SIGTERM', java_status)
        assert (stop.get('save'), stop.get('close'), stop.get('status'), stop.get('open'), stop.get('kind')) == (
            'saved', 'exited', 143, False, 'shutdown'), record
        assert not record.get('latched') and not record.get('fallback_record') and not record.get('jvm_alive'), record
        assert 'Stopped: the home was saved first; Minecraft closed.' in said, said
        # A peer that never reads is dropped, and the stop goes on.
        peers = [value for _, value in tagged(records, 'aresos-ci-probe', 'GUARDIAN_PROBE_PEER')]
        assert any(peer.get('dropped') for peer in peers), ('the peer that never reads was not dropped', peers)
        # The lid closed during the save, and nothing came of it.
        lids = [value for _, value in tagged(records, 'aresos-ci-lid', 'GUARDIAN_LID') if value.get('closed')]
        assert lids and asked <= int(lids[0]['t'] * 1_000_000) <= answered, ('no lid event during the save', lids)
        assert lids[0]['logind_lid_closed'] == 'b true', lids
        summary.update(save_answered=seconds_after_key(answered), lid=lids[0], peer_dropped=True)
        if not (summary['lid_block_held'] and lids[0]['aresos_lid_blocks']):
            # The brief (3.4): a lid block that fails is one log line and never fails the stop. Reported for step 8.
            print('REPORTED, NOT BLOCKING: logind did not list AresOS\'s lid block during the save', lids[0], flush=True)
    else:
        assert first('an answer to the save', game(r'save_answered.*'), asked, required=False) is None, summary
        ignored = first('the game ignores SIGTERM', game('sigterm_ignored'), asked)
        assert 25 <= (ignored - asked) / 1_000_000 <= 35 and ignored < guard_ended, summary
        # The guard ends when the supervisor's one deadline does, inside its own limit; the game is still there.
        assert 55 <= summary['guard_stop_seconds'] <= 85, summary
        assert record.get('jvm_alive') is True and java_exit > guard_ended, summary
        assert stop.get('close') == 'overrun' and stop.get('save') not in ('saved', 'nothing', None), record
        assert stop.get('sigterm') is True and stop.get('kind') == 'shutdown', record
        assert 'Not a confirmed stop' in said and 'could not be confirmed as saved first' in said, said
        # systemd's limit for the game scope ends it: 15 s after the user manager began to stop.
        killed_after = (java_exit - stops['user@1001.service']) / 1_000_000
        assert 10 <= killed_after <= 30, ('the game scope\'s 15 s limit did not end the game', killed_after, summary)
        # A text console still switches behind the black screen.
        assert 'console_key_sent_after' in watched, ('the host did not send Ctrl+Alt+F3', watched)
        console = next((when for when, sample in samples if asked <= when < guard_ended and sample['tty'] == 'tty3'
                        and sample['units'].get('guard') == 'deactivating' and sample['stopping']
                        and sample['black'] and sample['black_window']), None)
        assert console is not None, 'the probe did not see tty3 behind the black screen during the guard stop'
        summary.update(sigterm_ignored=seconds_after_key(ignored), game_killed_after_user_stop=round(killed_after, 2),
                       console_switched=True, tty3_seen=seconds_after_key(console))
    (evidence / 'guardian.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(f'GUARDIAN_VM_PASSED ({kind}): guard stop {summary["guard_stop_began"]} s to {summary["guard_stop_ended"]} s '
          f'after the power key, then {", ".join(f"{unit} at {when} s" for unit, when in summary["began_to_stop"].items())}; '
          f'record save={stop.get("save")} close={stop.get("close")}; power-off after {seconds:.0f} s', flush=True)
    return summary
