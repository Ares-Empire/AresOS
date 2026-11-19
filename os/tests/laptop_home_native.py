"""Native GTK 4/Cairo comparison for laptop_home_memory, with the same layer surface."""

import json
import os
from pathlib import Path
import signal
import subprocess
import sys

from laptop_home_headless import layer_state


def run(path):
    setup = json.loads((path / 'setup.json').read_text())
    subprocess.run(['/usr/bin/wlr-randr', '--output', 'HEADLESS-1', '--custom-mode', setup['size']], check=True)
    os.environ.pop('LD_PRELOAD', None)
    os.environ['GDK_DISABLE'] = 'gl,vulkan'
    import gi

    gi.require_version('Gtk4LayerShell', '1.0')
    gi.require_version('Gtk', '4.0')
    from gi.repository import Gdk, Gio, GLib, Gtk, Gtk4LayerShell

    app = Gtk.Application(application_id='aresos.laptop-home', flags=Gio.ApplicationFlags.NON_UNIQUE)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, app.quit)

    def activate(app):
        window = Gtk.ApplicationWindow(application=app)
        monitor = next(m for m in Gdk.Display.get_default().get_monitors() if m.get_connector() == 'HEADLESS-1')
        layer = Gtk4LayerShell
        window.set_decorated(False)
        layer.init_for_window(window)
        layer.set_namespace(window, 'aresos.laptop-home')
        layer.set_monitor(window, monitor)
        layer.set_layer(window, layer.Layer.BACKGROUND)
        for edge in (layer.Edge.TOP, layer.Edge.BOTTOM, layer.Edge.LEFT, layer.Edge.RIGHT):
            layer.set_anchor(window, edge, True)
        layer.set_keyboard_mode(window, layer.KeyboardMode.ON_DEMAND)
        area = Gtk.DrawingArea()

        def draw(_area, cr, width, height):
            cr.scale(width / 1920, height / 1080)
            cr.set_source_rgb(0.56, 0.73, 0.88)
            cr.paint()
            for row, houses in enumerate((9, 7, 9, 20)):
                base = 312 + 202 * row
                cr.set_source_rgb(0.42, 0.61, 0.29)
                cr.rectangle(0, base - 16, 1920, 202)
                cr.fill()
                cr.set_source_rgb(0.17, 0.16, 0.20)
                cr.rectangle(0, base, 1920, 16)
                cr.fill()
                for house in range(houses):
                    cr.set_source_rgb(0.45 + (house % 3) * 0.12, 0.35 + row * 0.07, 0.52)
                    cr.rectangle(30 + house * 94, base - 60, 72, 60)
                    cr.fill()
            parent = path / 'parent.json'
            if not parent.exists():
                pending = parent.with_suffix('.tmp')
                pending.write_text(json.dumps(dict(pid=os.getpid(), size=[width, height],
                                                   drm_hidden=not Path('/dev/dri').exists(),
                                                   renderer={'gsk': window.get_renderer().__gtype__.name},
                                                   layer=layer_state(window, layer))))
                pending.rename(parent)
                if setup.get('redraw'):
                    # 53f's measurement rests after one redraw; the control draws a second frame the same way.
                    GLib.timeout_add(500, lambda: area.queue_draw() and False)

        area.set_draw_func(draw)
        window.set_child(area)
        window.present()

    app.connect('activate', activate)
    return app.run([])


if __name__ == '__main__':
    sys.exit(run(Path(sys.argv[1])))
