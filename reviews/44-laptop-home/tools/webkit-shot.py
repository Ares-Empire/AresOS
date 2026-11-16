#!/usr/bin/python3
"""Development aid for AresOS package 44 (the laptop-screen home, a design study). Not product code.

Shows one prototype page the way the laptop home would run: the system's web engine (WebKitGTK 6.0) in one
borderless full-screen GTK 4 window, no browser around it, no network (an ephemeral session, and the pages
load nothing from outside). After the page has settled it saves a picture of it and prints one JSON line with
the memory and processor time of this program and every process the engine started for it.

Run it through shots.sh, which gives it a headless compositor of its own. It refuses to start on a display it
was not given by that script, so it can never open a window in the owner's session.

    webkit-shot.py <page address> <picture.png | - | a check's name> [seconds to settle] [seconds to watch]

With "check" it takes no picture: it sends the page the keys and clicks a person would (typing a name, Enter,
a hotbar key, a click on a logo, the arrow keys, Escape) and prints what the page did and what was expected.
"check-street" is Night street's own check, on a town with a removed app and a group past 16: a free place
moves no other house, and a house beyond the screen's edge slides into view when he types its name.
"check-grid" is the day look's own check: the four streets share one grid (equal roads from edge to edge, every
house on one lattice of columns, the same plots on every street); "check-grid-long" also slides a street that is
longer than the screen and looks again. "check-rest" watches a page at rest for 13 seconds: no animation runs and
nothing in the page changes (give the page a fixed clock with &time=).
"""
import json
import os
import sys
import time


# What a person does, and what the page must have done by then. The events are made in the page, so they reach
# the same listeners as real keys and clicks; a real keyboard and mouse were not used.
CHECK = """
const key = k => document.dispatchEvent(new KeyboardEvent('keydown', { key: k, bubbles: true, cancelable: true }));
const wait = ms => new Promise(done => setTimeout(done, ms));
const open = () => [...document.querySelectorAll('.win')].map(w => w.dataset.of).join();
const close = () => document.querySelector('.win-close').click();
const got = {};
for (const k of 'tool') key(k);
got.typing_finds = Home.state.best;
got.others_dim = document.querySelectorAll('[data-app].is-dim').length > 0;
key('Enter'); await wait(700);
got.enter_opens = open();
got.shown_as_running = document.querySelectorAll('[data-app="test-tool-1"].is-running').length > 0;
close();
got.closing_ends_it = open() === '' && !Home.state.running.has('test-tool-1');
key('1'); await wait(700);
got.key_1_opens = open();
close();
document.querySelector('[data-app="test-game-1"]:not(.slot)').click(); await wait(700);
got.click_opens = open();
close();
key('ArrowRight'); key('ArrowDown');
got.arrows_select = !!Home.state.selected;
for (const k of 'pa') key(k);
got.finds_other_programs = Home.state.best;
key('Escape');
got.escape_clears = Home.state.query === '' && document.querySelectorAll('[data-app].is-dim').length === 0;
return JSON.stringify(got);
"""
EXPECTED = {'typing_finds': 'test-tool-1', 'others_dim': True, 'enter_opens': 'test-tool-1', 'shown_as_running': True,
            'closing_ends_it': True, 'key_1_opens': 'test-web-1', 'click_opens': 'test-game-1', 'arrows_select': True,
            'finds_other_programs': 'test-paint', 'escape_clears': True}

# Night street on ?apps=45&hole=test-web-1: test-web-1 (place N0L0) was removed, System & Tools has 20 apps.
CHECK_STREET = """
const key = k => document.dispatchEvent(new KeyboardEvent('keydown', { key: k, bubbles: true, cancelable: true }));
const wait = ms => new Promise(done => setTimeout(done, ms));
const box = id => document.querySelector(`.house[data-app="${id}"]`).getBoundingClientRect();
const side = id => { const r = box(id); return r.left + r.width / 2 < innerWidth / 2 ? 'L' : 'R'; };
const inView = id => { const r = box(id); return r.left >= 0 && r.right <= innerWidth; };
const got = {};
got.hole_moves_nothing = laptopHome.test.holeMovesNothing();
got.web_2_stays_right = side('test-web-2');
got.web_3_stays_left = side('test-web-3');
got.far_house_out_of_view = !inView('test-tool-19');
got.end_sign_counts = [...document.querySelectorAll('.street-end:not([hidden])')].map(e => e.textContent).join(' ');
for (const k of 'tool19') key(k);
await wait(700);
got.typing_finds_it = Home.state.best;
got.its_street_slides_it_into_view = inView('test-tool-19');
got.other_streets_stay = inView('test-web-2') && side('test-web-2') === 'R';
key('Escape');
await wait(700);
got.escape_brings_it_back = !inView('test-tool-19') && inView('test-tool-1');
return JSON.stringify(got);
"""
EXPECTED_STREET = {'hole_moves_nothing': True, 'web_2_stays_right': 'R', 'web_3_stays_left': 'L',
                   'far_house_out_of_view': True, 'end_sign_counts': '‹ 2 2 ›', 'typing_finds_it': 'test-tool-19',
                   'its_street_slides_it_into_view': True, 'other_streets_stay': True, 'escape_brings_it_back': True}


# The day look's grid, on any day page. Everything is read from the page as it is drawn: the roads' and houses'
# boxes on the screen, and where each street's row of plots starts and ends.
CHECK_GRID = """
const key = k => document.dispatchEvent(new KeyboardEvent('keydown', { key: k, bubbles: true, cancelable: true }));
const wait = ms => new Promise(done => setTimeout(done, ms));
const streets = [...document.querySelectorAll('.street')];
const px = name => parseFloat(getComputedStyle(streets[0]).getPropertyValue(name));
const pitch = px('--pitch'), cell = px('--cell'), house = 12 * cell, margin = Math.floor(cell / 2);
const whole = n => ((n % pitch) + pitch) % pitch === 0;
const houses = () => [...document.querySelectorAll('.house')];
const onOneLattice = () => { const xs = houses().map(el => Math.round(el.getBoundingClientRect().left));
  return xs.length > 0 && xs.every(x => whole(x - xs[0])); };
const got = {};
got.streets = streets.length;
const tops = streets.map(s => s.getBoundingClientRect().top);
got.streets_equally_far_apart = tops.every((t, i) => i === 0 || t - tops[i - 1] === tops[1] - tops[0]);
const roads = [...document.querySelectorAll('.road')].map(r => r.getBoundingClientRect());
got.roads = roads.length;
got.roads_equal_and_edge_to_edge = roads.every(r => r.left === 0 && r.right === innerWidth && r.height === roads[0].height);
got.houses_on_one_lattice = onOneLattice();
const plots = side => streets.map(s => s.querySelector('.plots-' + side));
const start = el => parseFloat(el.style.left), end = el => start(el) + parseFloat(el.style.width);
const count = el => Number(el.dataset.n);
const cols = Math.min(...['L', 'R'].flatMap(side => plots(side).map(count)));
got.every_street_has_the_grid_columns = ['L', 'R'].every(side => plots(side).every(el => count(el) >= cols))
  && plots('L').every(el => end(el) === end(plots('L')[0])) && plots('R').every(el => start(el) === start(plots('R')[0]))
  && innerWidth - end(plots('L')[0]) === start(plots('R')[0]);
const outer = start(plots('R')[0]) + margin + (cols - 1) * pitch + house;
got.the_grid_fills_the_screen = outer <= innerWidth - 40 && outer + pitch > innerWidth - 40;
got.every_house_stands_on_a_plot = houses().every(el => {
  const x = parseFloat(el.style.left), row = el.closest('.street').querySelector(x < innerWidth / 2 ? '.plots-L' : '.plots-R');
  return whole(x - margin - start(row)) && x - margin >= start(row) && x + house + margin <= end(row); });
got.long_street_slides_on_the_lattice = null;
const far = document.querySelector('.house[data-app="test-tool-19"]');
if (far) {
  for (const k of 'tool19') key(k);
  await wait(700);
  const box = far.getBoundingClientRect();
  got.long_street_slides_on_the_lattice = box.left >= 0 && box.right <= innerWidth && onOneLattice();
  key('Escape');
  await wait(700);
}
return JSON.stringify(got);
"""
EXPECTED_GRID = {'streets': 4, 'streets_equally_far_apart': True, 'roads': 4, 'roads_equal_and_edge_to_edge': True,
                 'houses_on_one_lattice': True, 'every_street_has_the_grid_columns': True,
                 'the_grid_fills_the_screen': True, 'every_house_stands_on_a_plot': True,
                 'long_street_slides_on_the_lattice': None}

# A page at rest: nothing in it may move or change. The page gets a fixed clock (&time=), so not even the minute.
CHECK_REST = """
const wait = ms => new Promise(done => setTimeout(done, ms));
let changes = 0;
new MutationObserver(list => { changes += list.length; }).observe(document.documentElement,
  { subtree: true, childList: true, attributes: true, characterData: true });
await wait(13000);
return JSON.stringify({ animations_running: document.getAnimations().filter(a => a.playState === 'running').length,
  page_changes: changes });
"""
EXPECTED_REST = {'animations_running': 0, 'page_changes': 0}

CHECKS = {'check': (CHECK, EXPECTED), 'check-street': (CHECK_STREET, EXPECTED_STREET),
          'check-grid': (CHECK_GRID, EXPECTED_GRID),
          'check-grid-long': (CHECK_GRID, {**EXPECTED_GRID, 'long_street_slides_on_the_lattice': True}),
          'check-rest': (CHECK_REST, EXPECTED_REST)}


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


SIZES = {'Pss': 'pss_kib', 'Rss': 'rss_kib', 'Pss_Anon': 'anon_kib', 'Pss_File': 'file_kib', 'Pss_Shmem': 'shmem_kib'}


def process(pid):
    """Name, memory (KiB) and processor seconds of one process, or None if it is gone. Pss is split three ways:
    anonymous (its working memory), file (program and library files it maps) and shmem (shared memory, which
    holds the graphics buffers it shares with the compositor and its other processes)."""
    try:
        with open(f'/proc/{pid}/comm') as handle:
            name = handle.read().strip()
        sizes = {}
        with open(f'/proc/{pid}/smaps_rollup') as handle:
            for line in handle:
                key, _, rest = line.partition(':')
                if key in SIZES:
                    sizes[key] = int(rest.split()[0])
        with open(f'/proc/{pid}/stat', 'rb') as handle:
            fields = handle.read().rsplit(b')', 1)[1].split()
        ticks = int(fields[11]) + int(fields[12])
    except (OSError, ValueError, IndexError):
        return None
    return dict({'pid': pid, 'name': name, 'cpu_s': ticks / os.sysconf('SC_CLK_TCK')},
                **{field: sizes.get(key, 0) for key, field in SIZES.items()})


def measure():
    return [p for p in map(process, descendants(os.getpid())) if p]


def drawing_libraries():
    """Which graphics libraries this program and the engine's processes loaded: says who drew (a chip or software)."""
    found = set()
    for pid in descendants(os.getpid()):
        try:
            with open(f'/proc/{pid}/maps') as handle:
                for line in handle:
                    name = line.rsplit('/', 1)[-1].strip()
                    if any(word in name for word in ('nvidia', 'gallium', '_dri.so', 'LLVM', 'vulkan')):
                        found.add(name.split('.so')[0])
        except OSError:
            pass
    return sorted(found)


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
        result['processes'] = [{k: p[k] for k in ('name', *SIZES.values())} for p in after]
        for field in SIZES.values():
            result[field.replace('_kib', '_mib')] = round(sum(p[field] for p in after) / 1024, 1)
        result['drawing_libraries'] = drawing_libraries()
        if watch:
            before = result.pop('_before')
            seconds = time.monotonic() - before['at']
            spent = sum(p['cpu_s'] for p in after) - sum(p['cpu_s'] for p in before['processes'])
            result['idle_cpu_percent_of_one_core'] = round(100 * spent / seconds, 2)
            # Which process spent it: the window program (it puts the engine's pictures on the screen) or the
            # engine's page process (it draws the page).
            earlier = {p['pid']: p['cpu_s'] for p in before['processes']}
            for p, shown in zip(after, result['processes']):
                shown['cpu_percent'] = round(100 * (p['cpu_s'] - earlier.get(p['pid'], 0)) / seconds, 1)
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

        script, expected = CHECKS.get(picture, (None, None))

        def checked(view, answer):
            got = json.loads(view.call_async_javascript_function_finish(answer).to_string())
            wrong = {name: got.get(name) for name, value in expected.items() if got.get(name) != value}
            print(json.dumps({'page': result['page'], 'engine': result['engine'], 'checks': len(expected),
                              'passed': len(expected) - len(wrong), 'wrong': wrong}), flush=True)
            app.quit()

        def settled():
            if script:
                view.call_async_javascript_function(script, -1, None, None, None, None, checked)
            elif picture == '-':
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
