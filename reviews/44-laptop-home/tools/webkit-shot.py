#!/usr/bin/python3
"""Development aid for AresOS package 44 (the laptop-screen home, a design study). Not product code.

Shows one prototype page the way the laptop home would run: the system's web engine (WebKitGTK 6.0) in one
borderless full-screen GTK 4 window, no browser around it, no network (an ephemeral session, and the pages
load nothing from outside). After the page has settled it saves a picture of it and prints one JSON line with
the memory and processor time of this program and every process the engine started for it.

Run it through shots.sh, which gives it a headless compositor of its own. It refuses to start on a display it
was not given by that script, so it can never open a window in the owner's session.

    webkit-shot.py <page address> <picture.png | -> [seconds to settle] [seconds to watch the processor]
"""
import json
import os
import sys
import time


def descendants(root):
    """PIDs of root and everything started below it."""
    parents = {}
    for name in os.listdir('/proc'):
        if name.isdigit():
            try:
                with open(f'/proc/{name}/stat', 'rb') as handle:
                    # The parent is the second field after the last ')' (the name may hold spaces).
                    parents[int(name)] = int(handle.read().rsplit(b')', 1)[1].split()[1])
            except (OSError, ValueError, IndexError):
                pass
    found, grew = {root}, True
    while grew:
        grew = False
        for pid, parent in parents.items():
            if parent in found and pid not in found:
                found.add(pid)
                grew = True
    return sorted(found)


def process(pid):
    """Name, proportional and resident memory (KiB) and processor seconds of one process, or None if it is gone."""
    try:
        with open(f'/proc/{pid}/comm') as handle:
            name = handle.read().strip()
        sizes = {}
        with open(f'/proc/{pid}/smaps_rollup') as handle:
            for line in handle:
                key, _, rest = line.partition(':')
                if key in ('Pss', 'Rss', 'Pss_Anon'):
                    sizes[key] = int(rest.split()[0])
        with open(f'/proc/{pid}/stat', 'rb') as handle:
            fields = handle.read().rsplit(b')', 1)[1].split()
        ticks = int(fields[11]) + int(fields[12])
    except (OSError, ValueError, IndexError):
        return None
    return {'pid': pid, 'name': name, 'pss_kib': sizes.get('Pss', 0), 'rss_kib': sizes.get('Rss', 0),
            'anon_kib': sizes.get('Pss_Anon', 0), 'cpu_s': ticks / os.sysconf('SC_CLK_TCK')}


def measure():
    return [p for p in map(process, descendants(os.getpid())) if p]


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    if os.environ.get('PKG44_HEADLESS') != '1' or os.environ.get('WAYLAND_DISPLAY') in (None, '', 'wayland-0'):
        sys.exit('webkit-shot.py: run me through shots.sh (a headless compositor of its own).')
    address, picture = sys.argv[1], sys.argv[2]
    settle = float(sys.argv[3]) if len(sys.argv) > 3 else 1.5
    watch = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0

    import gi
    gi.require_version('Gtk', '4.0')
    gi.require_version('WebKit', '6.0')
    from gi.repository import Gio, GLib, Gtk, WebKit

    app = Gtk.Application(application_id='aresos.laptop-home.prototype', flags=Gio.ApplicationFlags.NON_UNIQUE)
    result = {'engine': f'WebKitGTK {WebKit.get_major_version()}.{WebKit.get_minor_version()}.{WebKit.get_micro_version()}',
              'page': address.rsplit('/prototypes/', 1)[-1]}

    def finish():
        after = measure()
        result['processes'] = [{k: p[k] for k in ('name', 'pss_kib', 'rss_kib', 'anon_kib')} for p in after]
        result['pss_mib'] = round(sum(p['pss_kib'] for p in after) / 1024, 1)
        result['rss_mib'] = round(sum(p['rss_kib'] for p in after) / 1024, 1)
        if watch:
            before = result.pop('_before')
            spent = sum(p['cpu_s'] for p in after) - sum(p['cpu_s'] for p in before['processes'])
            result['idle_cpu_percent_of_one_core'] = round(100 * spent / (time.monotonic() - before['at']), 2)
        print(json.dumps(result), flush=True)
        app.quit()
        return False

    def activate(app):
        window = Gtk.ApplicationWindow(application=app, title='AresOS laptop home (prototype)')
        window.set_decorated(False)
        window.set_default_size(1920, 1080)
        view = WebKit.WebView(network_session=WebKit.NetworkSession.new_ephemeral())
        if os.environ.get('PKG44_ACCEL') == 'never':
            # Draw the page in software inside the engine (no graphics-chip memory in its processes).
            view.get_settings().set_hardware_acceleration_policy(WebKit.HardwareAccelerationPolicy.NEVER)
            result['acceleration'] = 'never'
        window.set_child(view)
        window.fullscreen()
        window.present()

        def snapped(view, answer):
            texture = view.get_snapshot_finish(answer)
            result['picture'] = f'{texture.get_width()}x{texture.get_height()}'
            texture.save_to_png(picture)
            watched()

        def watched():
            if not watch:
                return finish()
            result['_before'] = {'at': time.monotonic(), 'processes': measure()}
            GLib.timeout_add(int(watch * 1000), finish)

        def settled():
            if picture == '-':
                watched()
            else:
                view.get_snapshot(WebKit.SnapshotRegion.VISIBLE, WebKit.SnapshotOptions.NONE, None, snapped)
            return False

        def changed(view, event):
            if event == WebKit.LoadEvent.FINISHED:
                GLib.timeout_add(int(settle * 1000), settled)

        view.connect('load-changed', changed)
        view.load_uri(address)

    app.connect('activate', activate)
    app.run([])


if __name__ == '__main__':
    main()
