#!/usr/bin/python3
# DEVELOPMENT AID of package 25 (the real-game check).
"""usage: summary.py <tag>

One table row for each launch of `series.sh <tag>`, from the evidence in reviews/25-guardian/runs/, and whether
anything in it is not as the check expects: a block on the disk before its save, a block missing after Java's exit
or in the reopened game, another exit status than 143, a stop that is not `saved` and `exited`. Exit 1 then, and
when a launch of the series has no evidence yet. Only reads."""
import json
import pathlib
import re
import sys

RUNS = pathlib.Path(__file__).resolve().parents[1] / 'runs'
TAG = sys.argv[1]
ORDER = [f'{name}-{TAG}' for name in ('close-1', 'stop-1', 'close-2', 'stop-2', 'close-3', 'stop-3', 'verify')]

rows, odd, reopened, closes, paths, missing = [], [], [], 0, 0, []
for name in ORDER:
    path = RUNS / f'{name}.json'
    if not path.exists():
        missing.append(name)
        continue
    run = json.loads(path.read_text())
    env = run.get('environment') or {}
    if not run.get('shown') or not env.get('runtime_folder_is_the_runs_own') or env.get('gate') != env.get('gate_expected'):
        odd.append(f'{name}: shown={run.get("shown")} why={run.get("why")} environment={env}')
    for seen in run.get('reopened') or []:
        reopened.append((name, seen['block'], seen['in_the_reopened_game'], seen['on_the_disk']))
        if seen['in_the_reopened_game'] is not True or seen['on_the_disk'] is not True:
            odd.append(f'{name}: reopened {seen}')
    if run.get('mode') == 'close' and run.get('close'):
        close = run['close']
        fine = (close.get('block_on_disk_before_sigterm') is False and close.get('exited') is True
                and close.get('exit_status') == 143 and close.get('block_on_disk_after_exit') is True
                and close.get('first_block_on_disk_after_exit') is True
                and close.get('written_after_sigterm') == {'level.dat': True, 'player data': True}
                and run.get('gradle_saw_exit_value') == 143)
        if not fine:
            odd.append(f'{name}: {close}')
        closes += 1
        written = close.get('written_after_sigterm') or {}
        rows.append(
            f'| `{name}` | block {close["block"]} '
            f'{"not on the disk" if close.get("block_on_disk_before_sigterm") is False else "ON THE DISK ALREADY"} '
            f'| SIGTERM by the rig, {close.get("ms_from_the_blocks_answer_to_sigterm")} ms after the game\'s answer; '
            f'no save asked | block {close["block"]} '
            f'{"on the disk" if close.get("block_on_disk_after_exit") is True else "NOT ON THE DISK"}; `level.dat` '
            f'{"written" if written.get("level.dat") else "NOT written"} and the player\'s data '
            f'{"written" if written.get("player data") else "NOT written"} after the signal '
            f'| {close.get("exit_status")} | {close.get("seconds_to_exit")} s from SIGTERM to exit |')
    elif run.get('mode') == 'stop' and run.get('path'):
        way = run['path']
        record, save, stop = way.get('stop_record') or {}, way.get('save') or {}, way.get('stop') or {}
        fine = (way.get('adopted') and way.get('hello_accepted') and way.get('state') == 'IN_WORLD'
                and way.get('save_block_on_disk_before_save') is False and save.get('exit') == 0
                and way.get('save_block_on_disk_after_saved') is True
                and way.get('stop_block_on_disk_before_stop') is False and stop.get('exit') == 0
                and record == {'open': False, 'kind': 'stop', 'phase': 'ended', 'save': 'saved', 'sigterm': True,
                               'close': 'exited', 'status': 143}
                and way.get('exit_status') == 143 and way.get('blocks_on_disk_after_exit') == [True, True, True]
                and way.get('prism_started') is False)
        if not fine:
            odd.append(f'{name}: {way}')
        paths += 1
        blocks = way.get('blocks') or {}
        phases = '; '.join(re.sub(r'^stop \(stop\) ', '', phase) for phase in (way.get('stop_phases') or [])[1:])
        rows.append(
            f'| `{name}` | block {blocks.get("before_save")} '
            f'{"not on the disk" if way.get("save_block_on_disk_before_save") is False else "ON THE DISK ALREADY"} '
            f'before `save`; block {blocks.get("before_stop")} '
            f'{"not on the disk" if way.get("stop_block_on_disk_before_stop") is False else "ON THE DISK ALREADY"} '
            f'before `stop` | adopted, hello accepted, `{way.get("state")}`; `save`: exit {save.get("exit")}, '
            f'{save.get("seconds")} s, block {blocks.get("before_save")} '
            f'{"on the disk" if way.get("save_block_on_disk_after_saved") is True else "NOT ON THE DISK"} after it; '
            f'`stop`: exit {stop.get("exit")}, record `{record.get("save")}`, `{record.get("close")}` '
            f'| blocks {blocks.get("first")}, {blocks.get("before_save")}, {blocks.get("before_stop")} '
            f'{"on the disk" if way.get("blocks_on_disk_after_exit") == [True, True, True] else "NOT ALL ON THE DISK"} '
            f'| {way.get("exit_status")} | `stop` {stop.get("seconds")} s as a command ({phases}) |')
    elif run.get('mode') == 'verify':
        rows.append(f'| `{name}` | | reopened once more, quit by closing the window | | '
                    f'{run.get("gradle_saw_exit_value")} | |')

lines = [f'**The runs** (series `{TAG}`, one launch of the real game each; `reviews/25-guardian/runs/<run>.json`): the '
         f'close alone {closes} times, the path {paths} times.', '',
         '| Run | Before | What ran | After Java\'s exit | Java\'s status | Time |', '|---|---|---|---|---|---|', *rows, '']
by_run = {}
for name, block, game, disk in reopened:
    by_run.setdefault(name, []).append((block, game, disk))
said = '; '.join(f'`{name}`: {", ".join(str(block) for block, _, _ in found)}' for name, found in by_run.items())
everything = all(game is True and disk is True for _, _, game, disk in reopened)
lines.append(f'Reopened ({len(reopened)} blocks, each asked of the next launch\'s game and read from the region file; '
             f'{"all there" if everything else "NOT ALL THERE"}): {said}.')
if missing:
    lines += ['', '**Not run:** ' + ', '.join(f'`{name}`' for name in missing) + '.']
print('\n'.join(lines))
if missing:
    print('no evidence yet: ' + ', '.join(missing))
print('ODD:\n' + '\n'.join(odd) if odd else 'nothing odd')
sys.exit(1 if odd or missing else 0)
