"""Package 320: aresos-level, the six keys' command (briefs/320-indicator.md, What to build 1 and Decision 1).

Every run uses level_sandbox: stand-in brightnessctl, wpctl and indicator at the image's absolute paths, a scratch
HOME and XDG_RUNTIME_DIR and a private bus in a private namespace. The real device tools never run.
"""
import os
import pathlib
import unittest

import level_sandbox as sandbox
from level_sandbox import BACKLIGHT, LED, Sandbox

ROOT = pathlib.Path(__file__).resolve().parents[2]
LEVEL = ROOT / 'os/config/usr/libexec/aresos-level'

# The keys' commands as rc.xml ran them until package 320, now the script's, with two changes: volume up also ends
# mute, and brightness touches the backlight class only, its floor 1 % of the maximum in raw units (Decision 7;
# brightnessctl 0.5.1 reads --min-value with atol). Each action's last command is its read-back.
COMMANDS = {
    'brightness-up': ['/usr/bin/brightnessctl --quiet --class=backlight set 5%+',
                      '/usr/bin/brightnessctl --class=backlight --machine-readable info'],
    'brightness-down': ['/usr/bin/brightnessctl --class=backlight max',
                        '/usr/bin/brightnessctl --quiet --class=backlight --min-value=960 set 5%-',
                        '/usr/bin/brightnessctl --class=backlight --machine-readable info'],
    'volume-up': ['/usr/bin/wpctl set-volume --limit 1.0 @DEFAULT_AUDIO_SINK@ 5%+',
                  '/usr/bin/wpctl set-mute @DEFAULT_AUDIO_SINK@ 0',
                  '/usr/bin/wpctl get-volume @DEFAULT_AUDIO_SINK@'],
    'volume-down': ['/usr/bin/wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-',
                    '/usr/bin/wpctl get-volume @DEFAULT_AUDIO_SINK@'],
    'mute': ['/usr/bin/wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle', '/usr/bin/wpctl get-volume @DEFAULT_AUDIO_SINK@'],
    'mic-mute': ['/usr/bin/wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle',
                 '/usr/bin/wpctl get-volume @DEFAULT_AUDIO_SOURCE@'],
    'show-volume': ['/usr/bin/wpctl get-volume @DEFAULT_AUDIO_SINK@'],
}


class LevelCase(unittest.TestCase):
    def setUp(self):
        problem = sandbox.unavailable()
        if problem:
            # CI's runner allows the namespace (os-image.yml turns AppArmor's switch off); there it must run.
            if os.environ.get('GITHUB_ACTIONS') == 'true':
                self.fail(problem)
            self.skipTest(problem)

    def box(self, **options):
        box = Sandbox(**options)
        self.addCleanup(box.close)
        return box

    def needs_gio(self):
        problem = sandbox.gio_missing()
        if problem:
            if os.environ.get('GITHUB_ACTIONS') == 'true':
                self.fail(problem)
            self.skipTest(problem)

    def run_ok(self, box, scenario, **options):
        result = box.run(scenario, **options)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn('SETTLE-TIMEOUT', result.stdout)
        return result

    def readings(self, box):
        """What the plate was told, in order: (sequence, action, reading) from starts and calls."""
        return [(int(row['argv'][0]), *row['argv'][1:]) if row['kind'] == 'start' else
                (row['sequence'], row['action'], row['reading'])
                for row in box.events() if row['kind'] == 'start' or (row['kind'] == 'show' and row['via'] == 'bus')]


class CommandsTest(LevelCase):
    def test_each_action_runs_exactly_its_commands_in_order(self):
        box = self.box()
        self.run_ok(box, ''.join(f'mark {action}; $L {action}; settle\n' for action in COMMANDS))
        groups, current = {}, None
        for row in box.calls():
            if row.startswith('== '):
                current = groups.setdefault(row[3:], [])
            else:
                current.append(row)
        self.assertEqual(groups, COMMANDS)

    def test_an_unknown_action_changes_nothing(self):
        box = self.box()
        result = box.run('$L louder; echo "rc=$?"; $L; echo "rc=$?"; settle\n')
        self.assertEqual(result.stdout.split(), ['rc=2', 'rc=2'])
        self.assertIn('usage: aresos-level', result.stderr)
        self.assertEqual(box.calls(), [])

    def test_the_script_names_every_program_by_its_absolute_path(self):
        text = LEVEL.read_text()
        for name in ('flock', 'timeout', 'gdbus', 'setsid', 'env', 'mv', 'sleep', 'brightnessctl', 'wpctl'):
            self.assertIn(f'/usr/bin/{name}', text)
        self.assertIn('INDICATOR=/usr/libexec/aresos-indicator', text)
        self.assertNotRegex(text, r'(?m)^[^#]*\bPATH=')


class LevelsTest(LevelCase):
    def test_volume_up_ends_mute_volume_down_and_mute_keep_the_level(self):
        box = self.box(sink={'volume': 0.40, 'mute': True})
        self.run_ok(box, '$L volume-down; settle\n')
        self.assertEqual(box.state()['sink'], {'volume': 0.35, 'mute': True})
        self.run_ok(box, '$L volume-up; settle\n')
        self.assertEqual(box.state()['sink'], {'volume': 0.40, 'mute': False})
        self.run_ok(box, '$L mute; settle\n')
        self.assertEqual(box.state()['sink'], {'volume': 0.40, 'mute': True})
        self.run_ok(box, '$L mute; settle; $L mic-mute; settle\n')
        self.assertEqual(box.state()['sink'], {'volume': 0.40, 'mute': False})
        self.assertTrue(box.state()['source']['mute'])

    def test_volume_stops_at_100_percent_and_brightness_at_the_maximum(self):
        box = self.box(devices=[dict(BACKLIGHT, cur=94000)], sink={'volume': 0.98, 'mute': False})
        self.run_ok(box, '$L volume-up; settle; $L volume-up; settle; $L brightness-up; settle; $L brightness-up; settle\n')
        self.assertEqual(box.state()['sink']['volume'], 1.0)
        self.assertEqual(box.state()['devices'][0]['cur'], 96000)

    def test_an_led_is_never_changed_and_brightness_reads_not_available(self):
        led = dict(LED, cur=1)
        box = self.box(devices=[led], indicator='crash')
        self.run_ok(box, '$L brightness-down; settle; $L brightness-up; settle\n')
        self.assertEqual(box.state()['devices'], [led])
        self.assertTrue(all('--class=backlight' in call for call in box.calls()), box.calls())
        self.assertEqual([reading[1:] for reading in self.readings(box)],
                         [('brightness-down', 'none'), ('brightness-up', 'none')])

    def test_a_large_backlight_floors_at_one_percent_of_its_maximum(self):
        box = self.box(devices=[dict(BACKLIGHT, cur=2000)], indicator='crash')
        self.run_ok(box, '$L brightness-down; settle; $L brightness-down; settle; $L brightness-up; settle\n')
        self.assertIn('/usr/bin/brightnessctl --quiet --class=backlight --min-value=960 set 5%-', box.calls())
        self.assertEqual(box.state()['devices'][0]['cur'], 5760)
        self.assertEqual([reading[2] for reading in self.readings(box)], ['1', '1', '6'])

    def test_a_small_backlight_floors_at_one_raw_unit_at_least(self):
        box = self.box(devices=[dict(BACKLIGHT, cur=2, max=50)])
        self.run_ok(box, '$L brightness-down; settle; $L brightness-down; settle\n')
        self.assertEqual(box.state()['devices'][0]['cur'], 1)
        self.assertIn('/usr/bin/brightnessctl --quiet --class=backlight --min-value=1 set 5%-', box.calls())

    def test_the_readings_are_numbers_and_fixed_words(self):
        box = self.box(sink={'volume': 0.62, 'mute': False}, indicator='crash')
        self.run_ok(box, '$L show-volume; settle; $L mute; settle; $L mic-mute; settle; $L mic-mute; settle\n')
        self.assertEqual(self.readings(box), [(1, 'show-volume', '62'), (2, 'mute', '62 muted'),
                                              (3, 'mic-mute', 'off'), (4, 'mic-mute', 'on')])
        loud = self.box(sink={'volume': 1.5, 'mute': False}, indicator='crash')
        self.run_ok(loud, '$L show-volume; settle\n')
        self.assertEqual(self.readings(loud), [(1, 'show-volume', '150')])

    def test_no_sound_output_or_microphone_reads_none(self):
        box = self.box(indicator='crash')
        box.write_state(devices=[BACKLIGHT], sink=None, source=None, hang=[])
        self.run_ok(box, '$L volume-up; settle; $L mic-mute; settle\n')
        self.assertEqual([reading[1:] for reading in self.readings(box)], [('volume-up', 'none'), ('mic-mute', 'none')])


class SurvivesTest(LevelCase):
    """The key's change never depends on the plate."""

    def assert_fast_change(self, box, scenario='', env=None):
        result = self.run_ok(box, scenario + 't0=$(now); $L volume-up; echo "rc=$? ms=$(($(now) - t0))"; settle 15\n',
                             env=env)
        rc, ms = result.stdout.split()[-2:]
        self.assertEqual(rc, 'rc=0', result.stderr)
        self.assertLess(int(ms[3:]), 1000, result.stdout)
        self.assertEqual(box.state()['sink'], {'volume': 0.45, 'mute': False})
        return result

    def test_without_the_indicator(self):
        result = self.assert_fast_change(self.box())
        self.assertIn('/usr/libexec/aresos-indicator is missing or not executable', result.stderr)

    def test_with_an_indicator_that_is_not_executable(self):
        box = self.box(indicator='not-executable')
        result = self.assert_fast_change(box)
        self.assertIn('missing or not executable', result.stderr)
        self.assertEqual(box.events(), [])

    def test_with_an_indicator_that_crashes_at_start(self):
        box = self.box(indicator='crash')
        result = self.assert_fast_change(box)
        self.assertIn('the indicator ended (status 3) before it took its bus name', result.stderr)

    def test_without_a_session_bus_or_a_runtime_folder(self):
        box = self.box(indicator='crash')
        self.assert_fast_change(box, scenario='unset DBUS_SESSION_BUS_ADDRESS\n')
        result = self.run_ok(box, 'env -u DBUS_SESSION_BUS_ADDRESS $L volume-down; settle\n'
                                  'env -u XDG_RUNTIME_DIR $L volume-down; settle\n')
        self.assertEqual(box.state()['sink'], {'volume': 0.35, 'mute': False})
        self.assertIn('no usable XDG_RUNTIME_DIR', result.stderr)
        self.assertEqual(box.events(), [])

    def test_with_an_indicator_that_never_takes_its_name(self):
        box = self.box(indicator='never-own')
        result = self.run_ok(box, 't0=$(now); $L volume-up; echo "ms=$(($(now) - t0))"; settle 15; alive\n'
                                  'flock -n $R/aresos-indicator.launch echo LAUNCH-FREE\n')
        self.assertLess(int(result.stdout.split()[0][3:]), 1000)
        self.assertEqual(box.state()['sink'], {'volume': 0.45, 'mute': False})
        self.assertEqual([row['kind'] for row in box.events()], ['start', 'term'])
        self.assertNotIn('ALIVE', result.stdout)
        self.assertIn('LAUNCH-FREE', result.stdout)
        self.assertIn('did not take its bus name within 5 s and was ended', result.stderr)

    def test_with_an_indicator_that_never_answers(self):
        self.needs_gio()
        box = self.box(indicator={'silent': True})
        result = self.run_ok(box, '$L volume-up; settle 15\n'
                                  't0=$(now); $L volume-down; echo "ms=$(($(now) - t0))"; settle 15\n'
                                  'echo "notifier ms=$(($(now) - t0))"\n')
        self.assertLess(int(result.stdout.split()[0][3:]), 1000)
        # The call is cut at half a second, and a timeout never starts a second program.
        self.assertLess(int(result.stdout.split()[-1][3:]), 3000)
        self.assertEqual(len(box.events('start')), 1)
        self.assertEqual(box.state()['sink'], {'volume': 0.40, 'mute': False})


class LockTest(LevelCase):
    def test_a_second_key_changes_at_once_while_the_first_read_back_hangs(self):
        box = self.box(hang=['wpctl get-volume'])
        result = self.run_ok(box, '$L volume-up\n'
                                  'pending() { [[ $(ps -o state= -p "$first") == S ]]; }\n'
                                  'for _ in {1..100}; do\n'
                                  '  { read -r first < "$STANDIN_DIR/read-blocked"; } 2>/dev/null && pending && break\n'
                                  '  sleep 0.01\n'
                                  'done\n'
                                  '[[ -n $first ]] && pending || { echo "first read did not block" >&2; exit 1; }\n'
                                  'flock -n $R/aresos-level.lock echo LOCK-FREE\n'
                                  't0=$(now); $L volume-up; echo "ms=$(($(now) - t0))"\n'
                                  'cat "$STANDIN_DIR/state.json"; echo\n'
                                  'pending || { echo "first read finished before the second change" >&2; exit 1; }\n'
                                  'settle 15\n')
        self.assertIn('LOCK-FREE', result.stdout)
        self.assertLess(int(result.stdout.split('ms=')[1].split()[0]), 900)
        self.assertIn('"volume": 0.5', result.stdout)
        self.assertNotIn('stayed busy', result.stderr)
        self.assertEqual(box.calls().count('/usr/bin/wpctl get-volume @DEFAULT_AUDIO_SINK@'), 2)

    def test_the_change_waits_for_the_lock_at_most_one_second(self):
        box = self.box()
        result = self.run_ok(box, '(flock $R/aresos-level.lock sleep 4 &) ; sleep 0.3\n'
                                  't0=$(now); $L volume-up; echo "ms=$(($(now) - t0))"\n'
                                  'cat "$STANDIN_DIR/state.json"; echo; settle 15\n')
        ms = int(result.stdout.split('ms=')[1].split()[0])
        self.assertGreaterEqual(ms, 950)
        self.assertLess(ms, 2500)
        self.assertIn('"volume": 0.45', result.stdout)
        self.assertIn('the change lock stayed busy for 1 s; changing anyway', result.stderr)

    def test_the_sequence_rises_and_a_broken_counter_starts_again(self):
        box = self.box(indicator='crash')
        self.run_ok(box, '$L show-volume; settle; $L show-volume; settle\n'
                         'echo garbage > $R/aresos-level.seq; $L show-volume; settle; ls $R\n')
        self.assertEqual([reading[0] for reading in self.readings(box)], [1, 2, 1])
        self.assertFalse((box.runtime / 'aresos-level.seq.new').exists())

    def test_the_indicator_inherits_neither_lock_and_gets_the_layer_library_first(self):
        box = self.box(indicator='crash', layer_library=True)
        self.run_ok(box, '$L show-volume; settle\n')
        start = box.events('start')[0]
        self.assertEqual(start['preload'], '/usr/lib64/libgtk4-layer-shell.so.0')
        self.assertFalse([name for name in start['files'] if name.endswith(('.lock', '.launch'))], start['files'])

    def test_no_layer_library_means_no_preload(self):
        if os.path.exists('/usr/lib64/libgtk4-layer-shell.so.0'):
            self.skipTest('this system has the layer library')
        box = self.box(indicator='crash')
        self.run_ok(box, '$L show-volume; settle\n')
        self.assertIsNone(box.events('start')[0]['preload'])


class ColdLaunchTest(LevelCase):
    def setUp(self):
        super().setUp()
        self.needs_gio()

    def test_a_running_indicator_gets_the_call_in_order(self):
        box = self.box(indicator={})
        self.run_ok(box, '$L volume-up; settle; $L volume-down; settle; $L mic-mute; settle\n')
        self.assertEqual(len(box.events('start')), 1)
        self.assertEqual(self.readings(box), [(1, 'volume-up', '45'), (2, 'volume-down', '40'), (3, 'mic-mute', 'off')])

    def test_two_quick_first_presses_start_exactly_one_program(self):
        box = self.box(indicator={'own_delay': 0.5})
        self.run_ok(box, '$L volume-up & $L volume-up & wait; settle 15\n')
        self.assertEqual(len(box.events('start')), 1)
        self.assertEqual(sorted(reading[0] for reading in self.readings(box)), [1, 2])

    def test_a_key_held_from_cold_starts_one_program_and_ends_on_the_last_level(self):
        box = self.box(indicator={})
        result = self.run_ok(box, 'for i in $(seq 12); do $L volume-down; sleep 0.04; done; settle 20; alive\n')
        self.assertEqual(len(box.events('start')), 1)
        self.assertEqual(max(self.readings(box)), (12, 'volume-down', '0'))
        self.assertEqual(result.stdout.count('ALIVE'), 1)

    def test_a_program_that_never_takes_its_name_is_ended_before_the_next_one_starts(self):
        box = self.box(indicator='never-own')
        result = self.run_ok(box, '$L volume-up & sleep 0.2; $L volume-up & wait; settle 20; alive\n', timeout=60)
        self.assertEqual(box.state()['sink'], {'volume': 0.50, 'mute': False})
        kinds = [row['kind'] for row in box.events()]
        self.assertEqual(kinds, ['start', 'term', 'start', 'term'])
        self.assertNotIn('ALIVE', result.stdout)


if __name__ == '__main__':
    unittest.main()
