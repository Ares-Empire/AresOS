"""Package 30b: a reviewed hint says how a program must be started (`gpu` and `environment`).

Everything is synthetic: no real program, window or compositor, and never Lunar Client. Whether there is an NVIDIA
card is injected wherever a test needs a fixed answer, so the tests pass on a machine with or without one.
"""
import dataclasses
import json
import shutil
from unittest import mock

from test_aresos_shell import shell, Base, REGISTRY, INSTANCE, NONCE
from test_aresos_shell_discovery import DiscoveryBase
from test_aresos_shell_windows import DiscoveredBase

SDL = {'SDL_VIDEO_DRIVER': 'wayland'}
SDL_PAIRS = (('SDL_VIDEO_DRIVER', 'wayland'),)


def lunar(**start):
    """Lunar's hint; without start settings, as package 30 shipped it. Built inside the tests, so that each test
    also runs, and fails on its own, against the helper without this change."""
    return shell.Hint('lunarclient.desktop', ('com.mojang.minecraft',), (), **start)


STEAM = shell.Hint('steam.desktop', (), ('steam_app_',))
# The image's hint files, read by the helper under test (the socket checks below run against both helpers).
IMAGE_HINTS = shell.load_hints
# What the helper's own session holds: the plain values, its own SDL choice, and keys every start drops.
SESSION = {'HOME': '/var/home/ares', 'PATH': '/usr/bin', 'WAYLAND_DISPLAY': 'wayland-0', 'SDL_VIDEO_DRIVER': 'x11'}
INHERITED = {**SESSION, **{key: 'inherited' for key in shell.GPU_KEYS},
             **{key: 'private' for key in shell.PRIVATE_ENVIRONMENT}}


class HintFormatTest(DiscoveryBase):
    """The two new keys, validated as strictly as the rest of a hint file."""

    def hint(self, name, data):
        folder = self.registry / 'hints'
        folder.mkdir(exist_ok=True)
        (folder / name).write_text(data if isinstance(data, str) else json.dumps(data))

    def load(self):
        return shell.load_hints(str(self.registry / 'hints'))

    def test_each_accepted_form(self):
        # Fails without the change: the old helper refuses every file with gpu or environment.
        printable = ''.join(map(chr, range(0x20, 0x7f)))  # all 95 printable ASCII characters
        bounds = ['x', 'v' * 128, printable, '${HOME} $PATH', ' ', '~', 'wayland,x11', '0']
        forms = {
            'gpu': ({'gpu': 'discrete'}, dict(gpu='discrete')),
            'environment': ({'environment': SDL}, dict(environment=SDL_PAIRS)),
            'both': ({'gpu': 'discrete', 'environment': SDL}, dict(gpu='discrete', environment=SDL_PAIRS)),
            'with-identity': ({'app_ids': ['org.with.Game'], 'app_id_prefixes': ['with_game_'], 'gpu': 'discrete',
                               'environment': SDL},
                              dict(app_ids=('org.with.Game',), app_id_prefixes=('with_game_',), gpu='discrete',
                                   environment=SDL_PAIRS)),
            # Values at the bounds arrive exactly as written, never expanded.
            **{f'bound{n}': ({'environment': {'SDL_VIDEO_DRIVER': value}},
                             dict(environment=(('SDL_VIDEO_DRIVER', value),))) for n, value in enumerate(bounds)},
            # An empty object names nothing that is not allowed; it counts as no start setting (refused alone, below).
            'empty-environment': ({'app_ids': ['org.empty.Game'], 'environment': {}},
                                  dict(app_ids=('org.empty.Game',))),
        }
        for name, (data, _) in forms.items():
            self.hint(name + '.json', {'schema': 1, 'desktop_id': name + '.desktop', **data})
        with self.assertNoLogs(shell.LOG, level='ERROR'):
            hints = self.load()
        self.assertEqual(hints, {name + '.desktop': shell.Hint(name + '.desktop', **fields)
                                 for name, (_, fields) in forms.items()})

    def test_each_refusal_refuses_the_whole_file_with_a_log_line(self):
        # A control: the old helper refuses these too (as unknown keys). It pins the new keys' own checks.
        good = {'schema': 1, 'desktop_id': 'good.desktop', 'app_ids': ['org.good.Game']}
        self.hint('broken.json', good)
        self.assertEqual(set(self.load()), {'good.desktop'})  # the file is fine without the broken part
        broken = {
            'gpu-integrated': dict(good, gpu='integrated'), 'gpu-null': dict(good, gpu=None),
            'gpu-true': dict(good, gpu=True), 'gpu-list': dict(good, gpu=['discrete']),
            'gpu-case': dict(good, gpu='Discrete'),
            'environment-list': dict(good, environment=[['SDL_VIDEO_DRIVER', 'wayland']]),
            'environment-string': dict(good, environment='SDL_VIDEO_DRIVER=wayland'),
            'environment-null': dict(good, environment=None),
            'allowed-beside-another': dict(good, environment={'SDL_VIDEO_DRIVER': 'wayland', 'SDL_AUDIO_DRIVER': 'x'}),
            'empty-environment-alone': {'schema': 1, 'desktop_id': 'good.desktop', 'environment': {}},
            'other-key': dict(good, env=SDL), 'schema-2': dict(good, schema=2, gpu='discrete'),
            'name-twice': '{"schema": 1, "desktop_id": "good.desktop", "app_ids": ["org.good.Game"], '
                          '"environment": {"SDL_VIDEO_DRIVER": "wayland", "SDL_VIDEO_DRIVER": "x11"}}',
            'key-twice': '{"schema": 1, "desktop_id": "good.desktop", "gpu": "discrete", "gpu": "discrete"}',
        }
        # The allowlist is exact names: other SDL_ names are refused too, among them the ones that load a library
        # or write a file (REVIEW-1, SHOULD 1) and SDL 2's spelling of the allowed one.
        names = ['SDL_OPENGL_LIBRARY', 'SDL_VULKAN_LIBRARY', 'SDL_AUDIO_DRIVER', 'SDL_AUDIO_DISK_OUTPUT_FILE',
                 'SDL_VIDEODRIVER', 'SDL_VIDEO_DRIVER_', 'SDL_1', 'SDL__',
                 'LD_PRELOAD', 'PATH', 'DRI_PRIME', '__NV_PRIME_RENDER_OFFLOAD', 'ARESOS_LAUNCH_NONCE',
                 'sdl_video_driver', 'Sdl_VIDEO_DRIVER', 'SDL_', 'SDL_' + 'A' * 61, 'SDL_VIDEO DRIVER',
                 'SDL_VIDEO-DRIVER', 'SDL_VIDEO.DRIVER', 'SDL_video_driver', 'XSDL_VIDEO_DRIVER', 'SDL_VIDEO_DRIVER\n',
                 'SDL_VIDEO_DRIVERÉ', 'SDL_VIDEO_DRIVER=x', '']
        values = ['', 'v' * 129, 1, 0, None, True, ['wayland'], {'x': 'y'}, 'way\nland', 'wayland\n', 'way\tland',
                  'wayländ', '\x7f', '\x00']
        broken.update({f'name {name!r}': dict(good, environment={name: 'x'}) for name in names})
        broken.update({f'value {value!r}': dict(good, environment={'SDL_VIDEO_DRIVER': value}) for value in values})
        for case, data in broken.items():
            with self.subTest(case):
                self.hint('broken.json', data)
                with self.assertLogs(shell.LOG, level='ERROR') as logs:
                    self.assertEqual(self.load(), {})  # its window identity goes too
                self.assertEqual(len(logs.output), 1, logs.output)
                self.assertIn('broken.json is invalid', logs.output[0])

    def test_a_hint_with_start_settings_only(self):
        # Fails without the change.
        self.write('tool.desktop')  # no GPU wish of its own
        before = self.catalogue()[0]['tool']
        self.hint('tool.json', {'schema': 1, 'desktop_id': 'tool.desktop', 'gpu': 'discrete', 'environment': SDL})
        app = self.catalogue()[0]['tool']
        self.assertEqual((before.gpu, before.environment), (None, ()))
        self.assertEqual((app.gpu, app.environment), ('discrete', SDL_PAIRS))
        # Its window identities stay its own; nothing else about it changes.
        self.assertEqual(dataclasses.replace(app, gpu=None, environment=()), before)

    def test_a_changed_start_setting_changes_the_1_1_revision_alone(self):
        # Fails without the change (the old helper refuses both files, so the revisions are equal). REVIEW-1, nit 1:
        # through the catalogue's own path, a hint's value counts toward the 1.1 revision, changes no row a client is
        # sent, and leaves the 1.0 list and revision alone.
        self.write('tool.desktop')
        helper = shell.Helper.__new__(shell.Helper)  # app_row reads nothing of the helper
        seen = {}
        for value in ('wayland', 'x11'):
            self.hint('tool.json', {'schema': 1, 'desktop_id': 'tool.desktop',
                                    'environment': {'SDL_VIDEO_DRIVER': value}})
            apps, revision = self.catalogue()
            self.assertEqual(apps['tool'].environment, (('SDL_VIDEO_DRIVER', value),))
            seen[value] = (revision, [helper.app_row(app, details=True) for app in apps.values()],
                           shell.load_legacy(str(self.registry), lambda path: True))
        self.assertNotEqual(seen['wayland'][0], seen['x11'][0])
        self.assertEqual(seen['wayland'][1:], seen['x11'][1:])

    def test_a_hint_asks_for_the_nvidia_card_and_never_takes_the_entrys_wish_away(self):
        # Fails without the change (plain); own is a control that passes either way.
        self.write('plain.desktop')
        self.write('own.desktop', PrefersNonDefaultGPU='true')
        self.hint('plain.json', {'schema': 1, 'desktop_id': 'plain.desktop', 'gpu': 'discrete'})
        self.hint('own.json', {'schema': 1, 'desktop_id': 'own.desktop', 'environment': SDL})
        apps = self.catalogue()[0]
        self.assertEqual(apps['plain'].gpu, 'discrete')
        self.assertEqual(apps['own'].gpu, 'discrete')

    def test_lunars_shipped_hint_loads_with_both_settings(self):
        # Fails without the change: the old file has neither, and the old helper refuses the new file.
        self.assertEqual(shell.load_hints(str(REGISTRY / 'hints')), {
            'lunarclient.desktop': lunar(gpu='discrete', environment=SDL_PAIRS), 'steam.desktop': STEAM})
        shutil.copytree(REGISTRY / 'hints', self.registry / 'hints')
        # Lunar's entry as installed: no PrefersNonDefaultGPU and no game category.
        self.write('lunarclient.desktop', Name='Lunar Client', StartupWMClass='lunarclient')
        app = self.catalogue()[0]['lunarclient']
        self.assertEqual((app.gpu, app.environment), ('discrete', SDL_PAIRS))
        self.assertIn('com.mojang.minecraft', app.app_ids)

    def test_a_registry_app_never_gets_a_hints_start_settings(self):
        # A control: registry entries, and the desktop entries they replace, keep their own start.
        for name in ('browser.json', 'notepad.json', 'terminal.json'):
            (self.registry / name).write_text((REGISTRY / name).read_text())
        self.write('google-chrome.desktop')
        self.hint('chrome.json', {'schema': 1, 'desktop_id': 'google-chrome.desktop', 'gpu': 'discrete',
                                  'environment': SDL})
        apps = self.catalogue()[0]
        self.assertNotIn('google-chrome', apps)
        launcher = shell.ScopeLauncher(popen=None, environ=dict(INHERITED), nvidia=lambda: True)
        self.assertEqual({app.id: launcher.environment(app) for app in apps.values()},
                         dict.fromkeys(('browser', 'notepad', 'terminal'), SESSION))


class LaunchEnvironmentTest(DiscoveredBase):
    """The environment each start gets, through the helper's own open_app route."""

    def setUp(self):
        super().setUp()
        self.nvidia_present = False
        self.driver = mock.Mock(side_effect=lambda: self.nvidia_present)

    def launcher(self):
        return shell.ScopeLauncher(popen=self.popen, run=self.systemctl, environ=dict(INHERITED), nvidia=self.driver)

    def started(self, app_id, request_id):
        reply = self.open(app_id, request_id)
        self.assertTrue(reply['ok'], reply)
        argv, options = self.popen.call_args.args[0], self.popen.call_args.kwargs
        return argv[argv.index('--') + 1:], options['env']

    def test_the_start_environment_with_and_without_an_nvidia_card(self):
        # Fails without the change: Lunar starts with the session's SDL value and on the Intel card.
        for present in (False, True):
            with self.subTest(nvidia=present):
                self.nvidia_present = present
                self.start(tracked=False, journal=f'{self.journal}-{present}')
                _, env = self.started('lunarclient', f'o-{present}')
                self.assertEqual(env, SESSION | SDL | (shell.NVIDIA_OFFLOAD if present else {}))

    def test_another_program_started_next_gets_neither(self):
        # Fails without the change at Lunar's start; every other program is the control.
        self.nvidia_present = True
        self.start(tracked=False)
        expected = {'lunarclient': SESSION | SDL | shell.NVIDIA_OFFLOAD, 'discord': SESSION, 'btop': SESSION,
                    'terminal': SESSION, 'notepad': SESSION, 'browser': SESSION}
        for n, (app_id, env) in enumerate(expected.items()):
            with self.subTest(app_id):
                self.assertEqual(self.started(app_id, f'o-{n}')[1], env)
        self.assertEqual(self.helper_.launcher.environ, INHERITED)  # the helper's own environment never changes

    def test_a_terminal_entry_gets_its_hints_start_settings(self):
        # Fails without the change.
        self.nvidia_present = True
        hints = dict(shell.load_hints(str(REGISTRY / 'hints')))
        hints['btop.desktop'] = shell.parse_hint({'schema': 1, 'desktop_id': 'btop.desktop', 'gpu': 'discrete',
                                                  'environment': SDL})
        with mock.patch.object(shell, 'load_hints', return_value=hints):
            self.start(tracked=False)
        argv, env = self.started('btop', 'o-1')
        self.assertEqual(argv, ['/usr/bin/foot', '--app-id=aresos.app.btop', '/usr/bin/btop'])
        self.assertEqual(env, SESSION | SDL | shell.NVIDIA_OFFLOAD)

    def test_the_nvidia_values_come_after_the_hints(self):
        # The brief's order. The parser never lets a hint name these keys; this pins the launcher's order alone.
        self.nvidia_present = True
        app = dataclasses.replace(shell.discovered_app('x.desktop', '/test/x.desktop', {
            'Type': 'Application', 'Name': 'X', 'Exec': '/usr/bin/x'}, lambda path: True), gpu='discrete',
            environment=(('__NV_PRIME_RENDER_OFFLOAD', '0'), ('SDL_VIDEO_DRIVER', 'wayland')))
        self.assertEqual(self.launcher().environment(app), SESSION | SDL | shell.NVIDIA_OFFLOAD)

    def test_nothing_new_on_the_socket(self):
        # A control: with the image's hints, list_apps (with app_details) answers the same as with package 30's
        # Lunar hint, and no start setting appears in any message the helper sends.
        rows = {}
        for name, hints in (('before', {'lunarclient.desktop': lunar(), 'steam.desktop': STEAM}), ('now', None)):
            with mock.patch.object(shell, 'load_hints', side_effect=lambda folder: hints or IMAGE_HINTS(folder)):
                helper = self.start(tracked=False, journal=f'{self.journal}-{name}')
            rows[name] = self.request(helper, self.conn, 'list_apps', 'l-1')['apps']
            self.assertEqual(self.request(helper, self.conn, 'open_app', 'o-1', app_id='lunarclient')['state'],
                             'starting')
            sent = json.dumps(self.conn.sent)
            self.assertNotIn('SDL_', sent)
            self.assertNotIn('wayland', sent.replace('wayland-0', ''))
            self.assertNotIn('discrete', sent)
        self.assertEqual(rows['now'], rows['before'])
        self.assertIn('lunarclient', [row['id'] for row in rows['now']])


class LegacyClientTest(DiscoveredBase):
    """A 1.0 client: the registry alone, exactly as before."""

    def test_a_1_0_client_is_untouched(self):
        # A control: with the image's hints a 1.0 client gets the same answers as with package 30's Lunar hint.
        answers = {}
        for name, hints in (('before', {'lunarclient.desktop': lunar()}), ('now', IMAGE_HINTS(REGISTRY / 'hints'))):
            apps, revision = shell.load_registry(REGISTRY)
            apps['lunarclient'] = self.app('lunarclient')
            apps = shell.apply_hints(apps, hints)
            self.popen.reset_mock()
            helper = shell.Helper(str(REGISTRY), INSTANCE, NONCE, f'{self.journal}-{name}',
                                  registry=(apps, revision), launcher=shell.ScopeLauncher(
                                      popen=self.popen, run=self.systemctl, environ=dict(INHERITED),
                                      nvidia=lambda: True),
                                  clock=self.clock, executable=lambda path: True)
            self.addCleanup(helper.watcher.stop)
            conn = Base.connect(self, helper)  # a 1.0 hello
            answers[name] = [self.request(helper, conn, 'list_apps', 'l-1'),
                             self.request(helper, conn, 'open_app', 'o-1', app_id='lunarclient'),
                             self.request(helper, conn, 'open_app', 'o-2', app_id='terminal')]
            self.assertEqual(self.popen.call_count, 1)  # Terminal only
            self.assertEqual(self.popen.call_args.kwargs['env'], SESSION)
        self.assertEqual(answers['now'][0], answers['before'][0])
        self.assertEqual(answers['now'][1], answers['before'][1])
        self.assertEqual(answers['now'][1]['error'], 'unknown_app')
        self.assertEqual(answers['now'][2]['state'], 'starting')
