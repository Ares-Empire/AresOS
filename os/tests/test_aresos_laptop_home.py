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


class IconTest(unittest.TestCase):
    """53c's icon limits, now on the native loader: the checks on the opened file, then the decoder child."""

    def setUp(self):
        workspace = scratch()
        self.addCleanup(workspace.cleanup)
        self.root = Path(workspace.name)

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
        self.assertEqual(home.read_icon(str(valid)), valid.read_bytes())
        for path in (self.root / 'missing.png', svg, wide, tall, large, link, fifo, self.root, 'icon.png', None):
            with self.subTest(path=path), self.assertRaises((OSError, ValueError)):
                home.read_icon(str(path) if isinstance(path, Path) else path)

    def test_decoder_child_gets_bytes_and_a_bare_environment(self):
        width, height, rgba = home.decode_png(png(3, 2))
        self.assertEqual((width, height, bytes(rgba)), (3, 2, b'\x99\x73\xc2\xff' * 6))
        width, height, _ = home.decode_png(png(512, 512))
        self.assertEqual((width, height), (512, 512))
        with mock.patch.object(home.subprocess, 'run', wraps=home.subprocess.run) as run:
            home.decode_png(png())
        command, options = run.call_args.args[0], run.call_args.kwargs
        self.assertEqual(command[1:4], ['-I', '-S', '-c'])
        self.assertEqual(options['env'], {'PATH': '/usr/bin', 'LC_ALL': 'C'})
        self.assertTrue(options['close_fds'])
        self.assertEqual(options['input'], png())
        self.assertFalse(any(str(self.root) in part for part in command), 'the path never reaches the child')
        good = png(4, 4)
        broken = bytearray(good)
        broken[40] ^= 0xff   # inside the IDAT chunk: its CRC no longer matches
        for data in (bytes(broken), good[:30], b'GIF89a' + good[6:], png(600, 1), png(1, 600), b''):
            with self.subTest(data=data[:12]), self.assertRaises((home.subprocess.SubprocessError, ValueError)):
                home.decode_png(data)

    def test_decoder_handles_filters_palettes_and_alpha(self):
        import struct
        import zlib

        def chunk(name, data):
            return struct.pack('>I', len(data)) + name + data + struct.pack('>I', zlib.crc32(name + data))

        def picture(colour, depth, rows, extra=b''):
            header = struct.pack('>IIBBBBB', 2, len(rows), depth, colour, 0, 0, 0)
            return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header) + extra
                    + chunk(b'IDAT', zlib.compress(b''.join(rows))) + chunk(b'IEND', b''))

        # RGBA with the Sub, Up, Average and Paeth filters: every row decodes to the same two pixels.
        pixels = bytes([10, 20, 30, 40, 50, 60, 70, 80])
        rows = [b'\0' + pixels, b'\2' + bytes(8), b'\1' + pixels[:4] + bytes(a - b & 255 for a, b in zip(pixels[4:],
                                                                                                         pixels[:4])),
                b'\4' + bytes(8)]
        self.assertEqual(home.decode_png(picture(6, 8, rows)), (2, 4, pixels * 4))
        # A palette of two with transparency, at two bits a pixel; grey at 16 bits keeps its high byte.
        palette = chunk(b'PLTE', bytes([255, 0, 0, 0, 0, 255])) + chunk(b'tRNS', bytes([128]))
        self.assertEqual(home.decode_png(picture(3, 2, [b'\0' + bytes([0b00010000])], palette)),
                         (2, 1, bytes([255, 0, 0, 128, 0, 0, 255, 255])))
        self.assertEqual(home.decode_png(picture(0, 16, [b'\0' + bytes([200, 1, 7, 255])])),
                         (2, 1, bytes([200, 200, 200, 255, 7, 7, 7, 255])))

    def test_icon_surface_contains_and_premultiplies(self):
        import cairo

        surface = home.icon_surface(cairo, 2, 1, bytes([255, 0, 0, 255, 0, 0, 255, 0]))
        self.assertEqual((surface.get_width(), surface.get_height()), (home.ICON_SIZE, home.ICON_SIZE))
        data, stride = surface.get_data(), surface.get_stride()

        def pixel(x, y):
            blue, green, red, alpha = data[y * stride + 4 * x:y * stride + 4 * x + 4]
            return red, green, blue, alpha

        self.assertEqual(pixel(4, 24), (255, 0, 0, 255), 'the opaque red half')
        self.assertEqual(pixel(44, 24)[3], 0, 'the transparent half')
        self.assertEqual(pixel(24, 4), (0, 0, 0, 0), 'contained: nothing above a 2 x 1 icon')


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
