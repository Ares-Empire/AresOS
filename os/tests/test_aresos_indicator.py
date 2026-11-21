"""Package 320's look, layout, and passive surface contract. No display or device connection."""
import contextlib
import io
import json
import os
from pathlib import Path
import runpy
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / 'os/config/usr'
PACK = CONFIG / 'share/aresos/look'
FONT = CONFIG / 'share/fonts/aresos/Jersey10-Regular.ttf'
indicator = SimpleNamespace(**runpy.run_path(str(CONFIG / 'libexec/aresos-indicator')))
SETTINGS = runpy.run_path(str(CONFIG / 'libexec/aresos-settings'))


class ContentTest(unittest.TestCase):
    def test_levels_include_partial_floor_full_and_above_limit(self):
        for level, counts in ((0, (0, 0)), (1, (0, 1)), (62, (12, 1)), (100, (20, 0)), (150, (20, 0))):
            with self.subTest(level=level):
                kinds = [indicator.step_kind(i, level, False) for i in range(20)]
                self.assertEqual((kinds.count('lit'), kinds.count('part')), counts)
        self.assertEqual(indicator.content('show-volume', '150', None, 'Speakers'),
                         ('speaker', 'Speakers', '150%', 'value', 150))

    def test_muted_keeps_the_level_in_grey_and_the_status_in_red(self):
        self.assertEqual(indicator.content('volume-down', '62 muted', None, 'HDMI'),
                         ('speaker-muted', 'HDMI', 'muted', 'warn', 62))
        self.assertEqual([indicator.step_kind(i, 62, True) for i in range(20)], ['muted'] * 12 + ['unlit'] * 8)

    def test_microphone_has_two_states_and_no_bar(self):
        self.assertEqual(indicator.content('mic-mute', 'on', None, ''), ('microphone', 'Microphone', 'on', 'value', None))
        self.assertEqual(indicator.content('mic-mute', 'off', None, ''),
                         ('microphone-off', 'Microphone', 'off', 'warn', None))

    def test_missing_device_and_screen_notes(self):
        for action, reading, monitor, title, status in (
            ('brightness-up', 'none', object(), 'Brightness', 'not available here'),
            ('brightness-down', '25', None, 'Laptop screen', 'is off'),
            ('mute', 'none', None, 'Sound', 'no output found'),
            ('mic-mute', 'none', None, 'Microphone', 'none found'),
        ):
            with self.subTest(action=action):
                self.assertEqual(indicator.content(action, reading, monitor, '')[1:], (title, status, 'quiet', None))

    def test_laptop_connector_and_headless_override(self):
        def monitor(connector, valid=True):
            return SimpleNamespace(get_connector=lambda: connector, is_valid=lambda: valid)

        invalid, external, builtin = monitor('eDP-0', False), monitor('HEADLESS-1'), monitor('eDP-1')
        self.assertIs(indicator.laptop_monitor([invalid, external, builtin]), builtin)
        self.assertIs(indicator.laptop_monitor([external, builtin], 'HEADLESS-1'), external)
        self.assertIsNone(indicator.laptop_monitor([invalid, external]))

    def test_all_look_settings_resolve_to_a(self):
        for look in SETTINGS['CHOICES']['look']:
            self.assertEqual(indicator.look_folder(look), indicator.PACK)

    def test_level_layout_dimensions_for_each_size(self):
        gui = SimpleNamespace(cairo=Mock(), Pango=Mock(SCALE=1024), PangoCairo=Mock())
        pack = indicator.Pack(gui.cairo, PACK)
        state = indicator.content('volume-down', '62', None, 'Speakers')
        with patch.object(indicator.Plate, 'ink_width', return_value=20):
            for size, dimensions in (('small', (350, 60)), ('medium', (525, 90)), ('large', (700, 120))):
                with self.subTest(size=size):
                    scale = indicator.SCALES[size]
                    plate = indicator.Plate(gui, pack, scale, state)
                    self.assertEqual((plate.width * scale, plate.height * scale), dimensions)


class PipeWireTest(unittest.TestCase):
    @staticmethod
    def graph(node_props=None, device_props=None, routes=()):
        node = {'node.name': 'alsa_output.pci.analog-stereo', 'media.class': 'Audio/Sink', 'device.id': 42,
                'card.profile.device': 7, 'device.profile.name': 'analog-stereo', **(node_props or {})}
        return [
            {'type': 'PipeWire:Interface:Metadata', 'props': {'metadata.name': 'default'}, 'metadata': [
                {'subject': 0, 'key': 'default.audio.sink', 'value': {'name': node['node.name']}}]},
            {'type': 'PipeWire:Interface:Node', 'id': 52, 'info': {'props': node}},
            {'type': 'PipeWire:Interface:Device', 'id': 42, 'info': {
                'props': device_props or {}, 'params': {'Route': routes, 'EnumRoute': [
                    {'direction': 'Output', 'device': 7, 'name': 'analog-output-headphones'}]}}},
        ]

    def test_speakers_and_headphones_share_the_same_sink(self):
        routes = [{'direction': 'Output', 'device': 2, 'name': 'hdmi-output-0'},
                  {'direction': 'Input', 'device': 7, 'name': 'analog-input-headset-mic'},
                  {'direction': 'Output', 'device': 7, 'name': 'analog-output-speaker'}]
        graph = self.graph(routes=routes)
        self.assertEqual(indicator.sink_name(graph), 'Speakers')
        routes[2] = {'direction': 'Output', 'device': 7, 'name': '[Out] Headphones',
                     'info': [2, 'port.type', 'headphones', 'route.hw-mute', 'true']}
        self.assertEqual(indicator.sink_name(graph), 'Headphones')
        routes.pop()
        self.assertEqual(indicator.sink_name(graph), 'Volume')

    def test_hdmi_uses_the_route_or_profile(self):
        graph = self.graph(routes=[{'direction': 'Output', 'device': 7, 'name': 'hdmi-output-0'}])
        self.assertEqual(indicator.sink_name(graph), 'HDMI')
        self.assertEqual(indicator.sink_name(self.graph({'device.profile.name': 'hdmi-stereo'})), 'HDMI')

    def test_bluetooth_prefers_the_devices_own_name_and_handles_unknown_outputs(self):
        graph = self.graph({'node.description': 'Generic audio', 'device.api': 'bluez5'},
                           {'device.alias': '  <b>Maße Ж</b>\nHeadset '})
        self.assertEqual(indicator.sink_name(graph), '<b>Maße Ж</b> Headset')
        self.assertEqual(indicator.sink_name([]), 'Volume')
        self.assertEqual(indicator.sink_name(self.graph()), 'Volume')

    def test_dump_is_bounded_and_failure_keeps_the_volume_label(self):
        call = Mock(side_effect=indicator.subprocess.TimeoutExpired('pw-dump', 0.3))
        with patch.object(indicator.subprocess, 'run', call):
            self.assertEqual(indicator.output_name(), 'Volume')
        self.assertEqual(call.call_args.args, (['/usr/bin/pw-dump', '-N'],))
        self.assertEqual(call.call_args.kwargs['timeout'], 0.3)
        with patch.object(indicator.subprocess, 'run', return_value=SimpleNamespace(stdout=json.dumps(self.graph()))):
            self.assertEqual(indicator.output_name(), 'Volume')


class SurfaceTest(unittest.TestCase):
    def setUp(self):
        self.window = Mock()
        self.cairo = SimpleNamespace(Region=object, Error=RuntimeError)
        self.gtk = Mock()
        self.gtk.Window.return_value = self.window
        self.layer = Mock()
        self.gui = SimpleNamespace(Gtk=self.gtk, layer=self.layer, cairo=self.cairo)
        self.plate = SimpleNamespace(width=175, height=30, scale=3,
                                    pack=SimpleNamespace(sizes=SimpleNamespace(top_margin=8, bottom_margin=64)))

    def test_passive_layer_is_configured_and_input_is_empty_before_visibility(self):
        setup = []
        self.window.connect_after.side_effect = lambda _, callback: setup.append(callback)
        self.window.realize.side_effect = lambda: setup[0](self.window)
        self.assertIs(indicator.layer_window(self.gui, self.plate, 'top', None), self.window)
        self.layer.set_namespace.assert_called_once_with(self.window, 'aresos-indicator')
        self.layer.set_layer.assert_called_once_with(self.window, self.layer.Layer.OVERLAY)
        self.layer.set_keyboard_mode.assert_called_once_with(self.window, self.layer.KeyboardMode.NONE)
        self.layer.set_exclusive_zone.assert_called_once_with(self.window, -1)
        self.layer.set_anchor.assert_called_once_with(self.window, self.layer.Edge.TOP, True)
        self.layer.set_margin.assert_called_once_with(self.window, self.layer.Edge.TOP, 24)
        self.layer.set_monitor.assert_not_called()
        self.window.set_default_size.assert_called_once_with(525, 90)
        self.window.get_surface().set_input_region.assert_called_once()
        self.window.set_visible.assert_not_called()
        self.window.present.assert_not_called()

    def test_bottom_scaled_margin_and_explicit_monitor(self):
        monitor = object()
        self.plate.scale = 4
        indicator.layer_window(self.gui, self.plate, 'bottom', monitor)
        self.layer.set_anchor.assert_called_once_with(self.window, self.layer.Edge.BOTTOM, True)
        self.layer.set_margin.assert_called_once_with(self.window, self.layer.Edge.BOTTOM, 256)
        self.layer.set_monitor.assert_called_once_with(self.window, monitor)

    def test_unsupported_or_old_protocol_logs_once_without_creating_a_window(self):
        for supported, version in ((False, 4), (True, 0)):
            with self.subTest(supported=supported, version=version):
                self.gui.Gdk = SimpleNamespace(Display=SimpleNamespace(get_default=object))
                self.gui.GdkWayland = SimpleNamespace(WaylandDisplay=object)
                self.gtk.init_check.return_value = True
                self.layer.is_supported.return_value = supported
                self.layer.get_protocol_version.return_value = version
                log = io.StringIO()
                with contextlib.redirect_stderr(log):
                    self.assertEqual(indicator.run(self.gui, (1, 'mute', '42')), 1)
                self.assertEqual(log.getvalue().splitlines(),
                                 ['aresos-indicator: the compositor has no usable layer-shell protocol'])
                self.gtk.Window.assert_not_called()

    def test_window_that_is_not_a_layer_after_setup_exits_without_mapping(self):
        self.layer.is_layer_window.side_effect = [True, False]
        app = Mock()
        display = Mock()
        display.get_monitors().get_n_items.return_value = 1
        settings = Mock(return_value=SETTINGS['DEFAULTS'])
        state = indicator.Indicator(self.gui, app, display, settings)
        self.addCleanup(state.worker.shutdown)
        state.request = ('mic-mute', 'on')
        log = io.StringIO()
        with contextlib.redirect_stderr(log), patch.dict(indicator.Indicator.present.__globals__,
                                                         {'Pack': Mock(), 'Plate': Mock(return_value=self.plate)}):
            state.present('Volume')
        self.assertEqual(log.getvalue().splitlines(),
                         ['aresos-indicator: cannot show the plate (window did not stay a layer surface)'])
        self.assertTrue(state.failed)
        self.window.destroy.assert_called_once()
        self.window.set_visible.assert_not_called()
        self.window.present.assert_not_called()
        app.quit.assert_called_once()


class RequestsTest(unittest.TestCase):
    def setUp(self):
        self.glib = Mock()
        self.glib.get_monotonic_time.return_value = 10000
        self.glib.timeout_add.side_effect = range(10, 20)
        self.state = indicator.Indicator(SimpleNamespace(GLib=self.glib), Mock(), Mock(), Mock())
        self.addCleanup(self.state.worker.shutdown)

    def test_reversed_show_calls_keep_the_newest_level_and_deadlines(self):
        reply = Mock()
        for values in ((8, 'volume-up', '65'), (7, 'volume-up', '60')):
            self.state.on_show(None, None, None, None, 'Show', SimpleNamespace(unpack=lambda: values), reply)
        self.assertEqual(reply.return_value.call_count, 2)
        self.assertEqual(self.state.last, 8)
        self.assertEqual(self.state.request, ('volume-up', '65'))
        self.assertEqual([call.args[0] for call in self.glib.timeout_add.call_args_list], [1500, 60000])
        self.glib.idle_add.assert_called_once()

    def test_next_event_resets_both_timers_and_hiding_discards_pending_audio(self):
        self.state.show(8, 'volume-up', '65')
        self.state.show(9, 'show-volume', '65')
        self.assertEqual([call.args for call in self.glib.source_remove.call_args_list], [(10,), (11,)])
        self.glib.idle_add.assert_called_once()
        window = Mock()
        self.state.window = window
        self.state.hide()
        self.state.present = Mock()
        self.state.audio_ready('Headphones')
        self.state.present.assert_not_called()
        window.destroy.assert_called_once()

    def test_invalid_reading_does_not_supersede_a_valid_request(self):
        self.state.show(8, 'mic-mute', 'off')
        self.state.show(9, 'mic-mute', '123')
        self.assertEqual((self.state.last, self.state.request), (8, ('mic-mute', 'off')))

    def test_show_volume_reads_the_settings_and_replaces_the_visible_surface(self):
        state = self.state
        state.gui.cairo = SimpleNamespace(Error=RuntimeError)
        state.gui.Gtk = Mock()
        state.display.get_monitors().get_n_items.return_value = 1
        state.settings.side_effect = [SETTINGS['DEFAULTS'], {'look': 'C', 'indicator-size': 'small',
                                                            'indicator-place': 'bottom'}]
        windows = [Mock(), Mock()]
        layer = Mock(side_effect=windows)
        pack = Mock()
        plate = Mock(return_value=SimpleNamespace(level=65))
        with (contextlib.redirect_stderr(io.StringIO()),
              patch.dict(indicator.Indicator.present.__globals__, {'Pack': pack, 'Plate': plate, 'layer_window': layer})):
            for sequence in (1, 2):
                state.show(sequence, 'show-volume', '65')
                state.audio_ready('Speakers')
        self.assertEqual(state.settings.call_count, 2)
        self.assertEqual(pack.call_count, 2)
        self.assertEqual([call.args[2] for call in plate.call_args_list], [3, 2])
        self.assertEqual([call.args[2:] for call in layer.call_args_list], [('top', None), ('bottom', None)])
        windows[0].destroy.assert_called_once()
        for window in windows:
            window.set_visible.assert_called_once_with(True)

    def test_cold_arguments_are_forwarded_and_loader_preload_is_cleared(self):
        def run(gui, first):
            self.assertIs(gui, self.state.gui)
            self.assertEqual(first, (5, 'mic-mute', 'on'))
            self.assertNotIn('LD_PRELOAD', os.environ)
            return 0

        with (patch.dict(os.environ, {'DBUS_SESSION_BUS_ADDRESS': 'fixture', 'LD_PRELOAD': 'fixture'}, clear=True),
              patch.dict(indicator.main.__globals__, {'load_gui': lambda: self.state.gui, 'run': run})):
            self.assertEqual(indicator.main(['5', 'mic-mute', 'on']), 0)


class PainterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import cairo
            import gi

            gi.require_version('Pango', '1.0')
            gi.require_version('PangoCairo', '1.0')
            from gi.repository import Pango, PangoCairo
            from PIL import Image
        except (ImportError, ValueError) as error:
            raise unittest.SkipTest(f'offscreen painter needs Pango, pycairo and Pillow ({error})') from error
        font_map = PangoCairo.FontMap.new()
        if not hasattr(font_map, 'add_font_file'):
            raise unittest.SkipTest('offscreen painter needs Pango 1.56 to load the bundled font into a private font map')
        font_map.add_font_file(str(FONT))
        pc = SimpleNamespace(FontMap=SimpleNamespace(get_default=lambda: font_map),
                             context_set_font_options=PangoCairo.context_set_font_options,
                             layout_path=PangoCairo.layout_path)
        cls.gui = SimpleNamespace(cairo=cairo, Pango=Pango, PangoCairo=pc)
        cls.pack = indicator.Pack(cairo, PACK)
        cls.Image = Image
        cls.study = runpy.run_path(str(ROOT / 'reviews/312-component-study/tools/look.py'))

    def image(self, width, height, draw):
        cairo = self.gui.cairo
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        draw(cairo.Context(surface))
        result = io.BytesIO()
        surface.write_to_png(result)
        return self.Image.open(result).convert('RGBA')

    def test_level_layout_and_every_sprite_pixel_at_each_scale_including_limit(self):
        for scale in (2, 3, 4):
            for flash in (False, True):
                with self.subTest(scale=scale, flash=flash):
                    state = indicator.content('brightness-up', '100', True, '')
                    plate = indicator.Plate(self.gui, self.pack, scale, state)
                    self.assertEqual((plate.width * scale, plate.height * scale), (175 * scale, 30 * scale))
                    study_look = self.study['LookA'](str(FONT))
                    study_look.text = Mock()
                    plate.text = Mock()
                    expected = self.study['indicator'](
                        study_look, dict(kind='level', what='brightness', label='Laptop screen', level=100, limit=flash),
                        self.study['ICONS_A'])
                    actual = self.image(175 * scale, 30 * scale, lambda cr: plate.draw(cr, flash))
                    self.assertEqual(actual.tobytes(), self.study['up'](expected, scale).tobytes())

    def test_jersey_letter_shapes_at_each_scale_have_the_study_masks(self):
        study_look = self.study['LookA'](str(FONT))
        for scale in (2, 3, 4):
            plate = indicator.Plate(self.gui, self.pack, scale, ('speaker', 'Speakers', '62%', 'value', 62))
            for char in 'Aaßj%1':
                with self.subTest(scale=scale, char=char):
                    w, h = 24 * scale, 24 * scale
                    def draw(cr):
                        cr.set_antialias(self.gui.cairo.ANTIALIAS_NONE)
                        plate.text(cr, plate.layout(char), 2, 4, 'ink')

                    actual = self.image(w, h, draw)
                    expected = self.Image.new('RGBA', (24, 24))
                    study_look.text(expected, 2, 4, char, study_look.ink)
                    self.assertEqual(actual.tobytes(), self.study['up'](expected, scale).tobytes())

    def test_plain_bluetooth_name_ellipsizes_and_fallback_uses_pack_colours(self):
        label = '<b>Ж Headphones</b> ' * 12
        plate = indicator.Plate(self.gui, self.pack, 3, ('speaker', label, '62%', 'value', 62))
        self.assertEqual(plate.label.get_text(), label)
        self.assertTrue(plate.label.is_ellipsized())
        self.assertEqual(plate.layout('Ж').get_unknown_glyphs_count(), 0)
        actual = self.image(525, 90, plate.draw)
        colours = {self.Image.new('RGBA', (1, 1), colour).getpixel((0, 0))
                   for colour in self.pack.data['colours'].values()}
        self.assertLessEqual({colour for _, colour in actual.getcolors(maxcolors=525 * 90)}, {(0, 0, 0, 0), *colours})


if __name__ == '__main__':
    unittest.main()
