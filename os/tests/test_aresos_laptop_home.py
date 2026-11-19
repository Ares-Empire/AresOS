"""Laptop-home resources, window rules, and 1.2 synchronization without a display."""

import json
import os
from pathlib import Path
import queue
import stat
import string
from types import SimpleNamespace
import unittest
from unittest import mock

from laptop_home_headless import load_program, scratch, wait_for
from laptop_home_helper import INSTANCE, TOKEN, StandIn, png, town


home = load_program()


class ResourcesTest(unittest.TestCase):
    def setUp(self):
        workspace = scratch()
        self.addCleanup(workspace.cleanup)
        self.root = Path(workspace.name)
        page = self.root / 'page'
        page.mkdir()
        self.resources = home.Resources(page)

    def test_packaged_types_and_containment(self):
        root = self.resources.root
        for filename, mime in (('index.html', 'text/html'), ('mod.js', 'text/javascript'), ('town.json', 'application/json'),
                               ('home.css', 'text/css'), ('mono.woff2', 'font/woff2'), ('picture.svg', 'image/svg+xml')):
            (root / filename).write_bytes(b'ok')
            self.assertEqual(self.resources.read(f'aresos-home://page/{filename}'), (mime, b'ok'))

        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'hidden.js').write_bytes(b'private')
        (root / 'leak.js').symlink_to(outside / 'hidden.js')
        (root / 'outside').symlink_to(outside, target_is_directory=True)
        for uri in ('aresos-home://page/../outside/hidden.js', 'aresos-home://page/%2e%2e/outside/hidden.js',
                    'aresos-home://page/%2findex.html', 'aresos-home://page/leak.js', 'aresos-home://page/outside/hidden.js',
                    'aresos-home://other/index.html', 'aresos-home://page/BRIDGE.md',
                    'https://page/index.html', 'http://page/index.html', 'file:///index.html', 'data:text/plain,x'):
            with self.subTest(uri=uri), self.assertRaises((ValueError, OSError)):
                self.resources.read(uri)

    def test_only_the_catalogue_icon_and_png_limits(self):
        valid = self.root / 'icon.png'
        valid.write_bytes(png(512, 512))
        svg = self.root / 'icon.svg'
        svg.write_bytes(b'<svg xmlns="http://www.w3.org/2000/svg"/>')
        wide = self.root / 'wide.png'
        wide.write_bytes(png(513, 1))
        tall = self.root / 'tall.png'
        tall.write_bytes(png(1, 513))
        large = self.root / 'large.png'
        large.write_bytes(png() + bytes(home.MAX_ICON))
        link = self.root / 'link.png'
        link.symlink_to(valid)
        fifo = self.root / 'fifo.png'
        os.mkfifo(fifo)
        self.resources.icons = dict(ok=str(valid), svg=str(svg), wide=str(wide), tall=str(tall), large=str(large),
                                    link=str(link), fifo=str(fifo), directory=str(self.root), relative='icon.png')
        self.assertEqual(self.resources.read('aresos-home://icon/ok'), ('image/png', valid.read_bytes()))
        for app_id in ('missing', 'ok/../ok', 'svg', 'wide', 'tall', 'large', 'link', 'fifo', 'directory', 'relative'):
            with self.subTest(app_id=app_id), self.assertRaises((OSError, ValueError)):
                self.resources.read(f'aresos-home://icon/{app_id}')


class WindowAndPowerTest(unittest.TestCase):
    def test_only_edp_is_selected_and_the_layer_is_configured(self):
        external, laptop = [SimpleNamespace(get_connector=lambda connector=name: connector)
                            for name in ('HDMI-A-1', 'eDP-2')]
        self.assertIs(home.laptop_monitor([external, laptop]), laptop)
        self.assertIsNone(home.laptop_monitor([external]))
        window = mock.Mock()
        layer = mock.Mock(Layer=SimpleNamespace(BACKGROUND='background'),
                          Edge=SimpleNamespace(TOP='top', BOTTOM='bottom', LEFT='left', RIGHT='right'),
                          KeyboardMode=SimpleNamespace(ON_DEMAND='on demand'))
        layer.get_protocol_version.return_value = 4
        home.place_window(window, laptop, layer)
        layer.init_for_window.assert_called_once_with(window)
        layer.set_layer.assert_called_once_with(window, 'background')
        layer.set_monitor.assert_called_once_with(window, laptop)
        layer.set_keyboard_mode.assert_called_once_with(window, 'on demand')
        self.assertEqual(layer.set_anchor.call_args_list,
                         [mock.call(window, edge, True) for edge in ('top', 'bottom', 'left', 'right')])
        window.fullscreen_on_monitor.assert_not_called()
        self.assertTrue(window.connect.call_args.args[1](window))
        home.place_window(window, laptop, None)
        window.fullscreen_on_monitor.assert_called_once_with(laptop)

    def test_upower_supply_and_missing_service(self):
        class BusError(Exception):
            pass

        gio = mock.Mock()
        glib = SimpleNamespace(Error=BusError, Variant=lambda signature, value: (signature, value))
        dbus = gio.bus_get_sync.return_value
        dbus.call_sync.return_value.unpack.return_value = (
            {'Type': 2, 'IsPresent': True, 'Percentage': 69.5, 'State': 1},)
        self.assertEqual(home.power_status(gio, glib), {'battery': {'level': 70, 'charging': True}})
        self.assertEqual(dbus.call_sync.call_args.args[:4], (
            'org.freedesktop.UPower', '/org/freedesktop/UPower/devices/DisplayDevice',
            'org.freedesktop.DBus.Properties', 'GetAll'))
        dbus.call_sync.side_effect = BusError
        with mock.patch.object(home, 'sysfs_battery', return_value=home.NO_BATTERY) as fallback:
            self.assertEqual(home.power_status(gio, glib), {'battery': None})
            fallback.assert_called_once_with()

    def test_sysfs_battery_fallback(self):
        with scratch() as directory:
            root = Path(directory)
            self.assertEqual(home.sysfs_battery(root), {'battery': None})
            for name, scope in [('BAT0', 'Device'), ('BAT1', 'System')]:
                battery = root / name
                battery.mkdir()
                for key, value in dict(type='Battery', scope=scope, present='1', capacity='74',
                                       status='Charging').items():
                    (battery / key).write_text(value)
            self.assertEqual(home.sysfs_battery(root), {'battery': {'level': 74, 'charging': True}})
            (root / 'BAT1/status').write_text('Discharging')
            self.assertEqual(home.sysfs_battery(root), {'battery': {'level': 74, 'charging': False}})
            (root / 'BAT1/present').write_text('0')
            self.assertEqual(home.sysfs_battery(root), {'battery': None})


class SyncTest(unittest.TestCase):
    def setUp(self):
        workspace = scratch()
        self.addCleanup(workspace.cleanup)
        self.root = Path(workspace.name)
        self.path = self.root / 'state/home.json'
        self.helper = StandIn(self.root / 'shell.sock', page_size=2)
        self.updates = queue.Queue()
        self.state = {}
        self.peer = None
        self.addCleanup(self.helper.drop)
        self.client = home.HelperView(self.helper.path, INSTANCE, TOKEN, self.path, self.publish,
                                      lambda callback, *args: callback(*args))

    def start(self):
        self.client.start()
        self.addCleanup(self.client.stop)

    def publish(self, peer, changed, _icons):
        self.updates.put((peer, changed))

    def until(self, predicate):
        while True:
            self.peer, changes = self.updates.get(timeout=10)
            self.state.update(changes)
            if predicate():
                return

    def open(self, app_id):
        results = queue.Queue()
        self.client.open(self.peer, app_id, results.put)
        return results.get(timeout=6)

    def test_complete_cache_null_restart_empty_publish_and_catalogue_change(self):
        self.helper.running = ['test-web-2']
        self.helper.start()
        self.start()
        self.until(lambda: self.state.get('helper') is True)
        self.assertEqual(len(self.state['home']['apps']), 12)
        self.assertEqual(len(self.state['programs']), 12)
        self.assertEqual(self.state['running'], ['test-web-2'])
        self.assertEqual(self.state['home']['apps'][-1]['name'], 'Test Work 3')
        cached = home.load_home(self.path)
        self.assertEqual(cached, self.state['home'])
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])
        self.assertEqual(self.open('test-web-1'), {'state': 'starting'})
        self.helper.results['test-web-1'] = dict(ok=False, state='failed', message='not_installed')
        self.assertEqual(self.open('test-web-1'), {'state': 'failed', 'message': 'not_installed'})

        self.helper.drop()
        self.until(lambda: self.state.get('helper') is False)
        self.assertEqual(self.state['home'], cached)
        self.assertEqual(self.state['running'], ['test-web-2'])
        self.assertEqual(self.open('test-web-1'), home.UNAVAILABLE)
        self.assertEqual(self.helper.opens, ['test-web-1', 'test-web-1'])
        self.helper.revision = None
        self.helper.running = ['test-tool-1']
        self.helper.start()
        self.until(lambda: self.state.get('helper') is True)
        self.assertEqual(self.state['home'], cached)
        self.assertEqual(home.load_home(self.path), cached)
        self.assertEqual(self.state['running'], ['test-tool-1'])
        self.assertEqual(self.open('test-web-1')['message'], 'not_installed')

        self.helper.publish('empty', [])
        self.until(lambda: self.state['home']['apps'] == [])
        self.assertEqual(home.load_home(self.path)['apps'], [])
        houses, catalogue = town(8, holes=['test-web-1'], unpinned=['test-tool-1'])
        catalogue[-1]['name'] = 'New name'
        self.helper.publish('new-town', houses)
        self.until(lambda: len(self.state['home']['apps']) == 6)
        before = len(self.helper.requests)
        self.helper.change_catalogue('new-catalogue', catalogue, houses[:-1])
        self.until(lambda: len(self.state['home']['apps']) == 5)
        self.assertEqual(self.state['programs'][-1]['name'], 'New name')
        self.assertTrue({'get_home', 'list_apps'} <= {r['op'] for r in self.helper.requests[before:]})

    def test_revision_change_between_pages_restarts_the_transaction(self):
        self.helper.start()

        def change(request):
            if request['op'] == 'get_home' and 'cursor' in request:
                self.helper.before_page = None
                self.helper.revision = 'new'
                self.helper.houses, self.helper.programs = town(4, holes=['test-game-1'])

        self.helper.before_page = change
        self.start()
        self.until(lambda: self.state.get('helper') is True)
        self.assertEqual([app['id'] for app in home.load_home(self.path)['apps']],
                         ['test-tool-1', 'test-web-1', 'test-work-1'])
        first_pages = [r for r in self.helper.requests if r['op'] == 'get_home' and 'cursor' not in r]
        self.assertEqual(len(first_pages), 2)

    def test_reconnect_intervals_keep_retrying_at_two_seconds(self):
        self.helper.start()
        self.helper.answer = lambda peer, request: peer.send(id=request['id'], ok=False, error='busy')
        self.start()
        wait_for(lambda: len(self.helper.requests) >= 5, duration=8)
        for first, second, expected in zip(self.helper.connections, self.helper.connections[1:], (0.5, 1, 2, 2)):
            self.assertAlmostEqual(second - first, expected, delta=0.35)
        self.until(lambda: self.state.get('helper') is False)
        self.assertTrue(self.updates.empty())
        self.assertEqual(len({row['id'] for row in self.helper.requests}), 5)

    def test_cache_reader_ignores_internal_fields_and_handles_bad_data(self):
        self.assertEqual(home.load_home(self.path), home.EMPTY_HOME)
        self.path.parent.mkdir()
        self.path.write_text('{')
        self.assertEqual(home.load_home(self.path), home.EMPTY_HOME)
        row = {'id': 'test-web-1', 'short': 'web', 'name': 'Test Web 1', 'group': 'internet', 'cells': 'a' * 144}
        self.path.write_text(json.dumps({'palette': {'a': '#abcdef'}, 'apps': [dict(row, exec_name='internal')]}))
        self.assertEqual(home.load_home(self.path), {'palette': {'a': '#abcdef'}, 'apps': [row]})

    def test_full_multibyte_cache_round_trips_at_the_helper_limits(self):
        palette = dict.fromkeys(string.ascii_letters + string.digits, '#abcdef')
        rows = [dict(id=f'app-{n:060d}', short='🟦' * 64, name='🟧' * 64, group='a' * 64,
                     place='a' * 32, slot=8, cells='a' * 144) for n in range(200)]
        kept = {'palette': palette, 'apps': rows}
        home.save_home(self.path, kept)
        self.assertGreater(self.path.stat().st_size, 2 * home.MAX_MESSAGE)
        self.assertEqual(home.load_home(self.path), kept)

    def test_writer_refuses_an_unreadable_cache_and_keeps_the_previous_file(self):
        row = dict(id='test-web-1', short='web', name='Test Web 1', group='internet', cells='a' * 144)
        kept = {'palette': {'a': '#abcdef'}, 'apps': [row]}
        home.save_home(self.path, kept)
        for change in ({'cells': 'a'}, {'name': 'x' * (home.MAX_HOME_BYTES + 1)}):
            with self.subTest(field=next(iter(change))):
                with self.assertRaises(ValueError):
                    home.save_home(self.path, dict(kept, apps=[dict(row, **change)]))
                self.assertEqual(home.load_home(self.path), kept)
                self.assertEqual(list(self.path.parent.iterdir()), [self.path])
