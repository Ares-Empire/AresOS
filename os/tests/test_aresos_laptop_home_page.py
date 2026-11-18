"""Drive the packaged town, finder and hotbar through the real WebKit view."""

import hashlib
import os
from pathlib import Path
import shutil
import threading
import unittest

from laptop_home_headless import ROOT, Headless, engines, headless_available, load_program, scratch, wait_for
from laptop_home_helper import StandIn, png, town

PAGE = ROOT / 'os/config/usr/share/aresos/laptop-home'
IMAGE_FONTS = ROOT / 'os/config/usr/share/fonts/aresos'
STUDY_FONTS = ROOT / 'reviews/44-laptop-home/prototypes/shared/fonts'
PICTURES = ROOT / 'reviews/53c-laptop-home/pictures'
STUDY_PALETTE = dict(zip('abcdefghijklmno', ('#e6e8e6', '#8f918a', '#3b3e44', '#131419', '#a32a2a',
    '#e06c10', '#f0b41e', '#66b120', '#4b6428', '#19828f', '#2c92d0', '#31369c', '#6d27a8', '#b43da8', '#d96e97')))
COMMON = """
const el = selector => document.querySelector(selector);
const all = selector => [...document.querySelectorAll(selector)];
const house = id => el(`.house[data-app="${id}"]`);
const key = key => document.dispatchEvent(new KeyboardEvent('keydown', {key, bubbles: true, cancelable: true}));
const type = text => { for (const c of text) key(c); };
const wait = ms => new Promise(done => setTimeout(done, ms));
const frame = () => el('.house.is-framed, .finder-row.is-framed')?.dataset.app || null;
const inView = item => { const {left, right} = item.getBoundingClientRect(); return left >= 0 && right <= innerWidth; };
const snapshot = () => laptopHome.world.snapshot();
"""
PROBE = """
(() => {
  let frames = 0, draws = 0, first = null;
  const request = window.requestAnimationFrame.bind(window);
  window.requestAnimationFrame = callback => request(time => { frames++; callback(time); });
  for (const name of ['fillRect', 'clearRect']) {
    const draw = CanvasRenderingContext2D.prototype[name];
    CanvasRenderingContext2D.prototype[name] = function (...args) {
      draws++;
      return draw.apply(this, args);
    };
  }
  const observer = new MutationObserver(() => {
    if (document.querySelector('#stage:not([hidden])')) {
      first = [...document.querySelectorAll('.house.is-running')].map(el => el.dataset.app);
      observer.disconnect();
    }
  });
  observer.observe(document, {subtree: true, attributes: true, attributeFilter: ['hidden']});
  window.pageProbe = () => ({frames, draws, first});
})();
"""


def generated_cells(app_id):
    """Give the headless town varied block logos without loading artwork from the laptop."""
    shape, mark, fg, bg = hashlib.sha256(app_id.encode()).digest()[:4]
    colours = tuple(STUDY_PALETTE)
    plate = colours[bg % len(colours)]
    figure = colours[(bg + 3 + fg % 6) % len(colours)]
    cells = []
    for y in range(12):
        for x in range(12):
            dx, dy = abs(x - 5.5), abs(y - 5.5)
            solid = (True, dx * dx + dy * dy < 39, dx + dy < 8, max(dx, dy) < 5 or dx + dy < 6)[shape % 4]
            ink = (dx < 1.5 or dy < 1.5, abs(dx - dy) < 1, 2 < dx + dy < 5,
                   6 < dx * dx + dy * dy < 16, (x // 2 + y // 2) % 2 == 0)[mark % 5]
            block = (figure if ink and max(dx, dy) < 4.5 else plate) if solid else '.'
            cells.append('d' if y >= 9 and 4 <= x <= 7 else block)
    return ''.join(cells)


def generated_town(streets, icon, *, holes=()):
    homes, programs = town(0, streets=streets, holes=holes)
    slots = ['test-web-1', 'test-web-2', 'test-game-1', 'test-work-1', 'test-tool-1', 'test-tool-2', 'test-work-2']
    for home in homes:
        app_id = home['id']
        kind, number = app_id.removeprefix('test-').split('-')
        home['short'], home['cells'] = kind + number, generated_cells(app_id)
        home.pop('slot', None)
        if app_id in slots:
            home['slot'] = slots.index(app_id)
    for app in programs:
        if app['id'] == 'test-work-3':
            app['name'] = 'Test Media Workbench'
    programs.extend([
        dict(id='test-paint', name='Test Paint', generic_name='Image Editor', keywords=['drawing'], icon=str(icon)),
        dict(id='test-viewer', name='Test Viewer', generic_name='Document Viewer', keywords=['pdf'], icon=str(icon)),
        dict(id='test-archive', name='Test Archive', generic_name='Archive Manager', keywords=['pdf']),
    ])
    return homes, programs


@unittest.skipUnless(headless_available() and shutil.which('wlr-randr', path='/usr/bin'),
                     'headless labwc and wlr-randr, Mesa pins, GTK 4 and WebKitGTK 6.0')
class LaptopHomePageTest(unittest.TestCase):
    def setUp(self):
        workspace = scratch()
        self.addCleanup(workspace.cleanup)
        self.path = Path(workspace.name)
        self.icon = self.path / 'icon.png'
        self.icon.write_bytes(png())
        self.helper = StandIn(self.path / 'shell.sock', page_size=4)
        self.helper.palette = STUDY_PALETTE
        self.helper.houses, self.helper.programs = generated_town((7, 4, 5, 8), self.icon)
        self.helper.running = ['test-web-2', 'test-tool-3']

    def gui(self, look, *, fallback=False):
        page = PAGE
        if look == 'night':
            # Select the packaged second look without altering the entry-point URL or bridge.
            page = self.path / 'night'
            shutil.copytree(PAGE, page)
            entry = page / 'index.html'
            entry.write_text(entry.read_text().replace('data-look="day"', 'data-look="night"'))
        fonts = IMAGE_FONTS if fallback else STUDY_FONTS
        return Headless(self.path, self.helper.path, page=page, size='1920x1080', script=PROBE,
                        font_dir=fonts, battery=not fallback)

    def check(self, body, expected):
        self.assertEqual(self.view.evaluate(COMMON + body), expected)

    def picture(self, name):
        if os.environ.get('LAPTOP_HOME_TEST_PICTURES'):
            pictures = Path(os.environ.get('LAPTOP_HOME_TEST_PICTURES_DIR') or PICTURES)
            pictures.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.view.snapshot(), pictures / f'{self.look}-{name}.png')

    def replace_town(self, streets, *, holes=(), edit=None):
        houses, programs = generated_town(streets, self.icon, holes=holes)
        if edit:
            edit(houses)
        self.helper.change_catalogue(str(self.helper.serial), programs, houses)
        self.view.until(f'document.querySelectorAll(".house").length === {len(houses)}')

    def measure_memory(self):
        if not os.environ.get('LAPTOP_HOME_TEST_PSS'):
            return
        pid = self.view.parent()['pid']
        children = wait_for(lambda: (p if {'WebKitWebProcess', 'WebKitNetworkProcess'} <= set(
            (p := engines(pid)).values()) else None))
        pss = {}
        for proc, name in [(pid, 'program'), *children.items()]:
            lines = Path(f'/proc/{proc}/smaps_rollup').read_text().splitlines()
            pss[name] = int(next(line.split()[1] for line in lines if line.startswith('Pss:')))
        print(f'Pinned {self.look} packaged page PSS in KiB: {pss}, total {sum(pss.values())}', flush=True)

    def check_interactions(self):
        self.check("""
            type('/tool');
            return [frame(), all('.house.is-dim').length, el('.finder-q').textContent,
                    el('.finder-hint').textContent, el('.house.is-framed .frame') !== null];
        """, ['test-tool-1', 16, 'tool', 'Enter opens Test Tool 1', True])
        self.check("key('Enter'); return [all('.puff').length, house('test-tool-1').classList.contains('is-opening')];",
                   [9, True])
        wait_for(lambda: self.helper.opens == ['test-tool-1'])
        self.view.until('!document.querySelector(".finder-q").textContent')
        self.check("return house('test-tool-1').classList.contains('is-running');", False)
        self.helper.set_running(['test-tool-1'])
        self.view.until('document.querySelector(".house[data-app=test-tool-1]").classList.contains("is-running")')
        self.check("""
            await wait(720);
            return [all('.puff').length, all('.is-opening').length, all('.house.is-running').map(el => el.dataset.app),
              el('.slot.is-running').dataset.app, getComputedStyle(house('test-tool-1').querySelector('canvas')).filter,
              getComputedStyle(house('test-tool-1').querySelector('.door')).backgroundImage.includes('linear-gradient')];
        """, [0, 0, ['test-tool-1'], 'test-tool-1', 'none', True])
        self.picture('opened')
        self.helper.set_running([])
        self.view.until('!document.querySelector(".is-running")')
        self.check("""
            await wait(180);
            return [getComputedStyle(house('test-tool-1').querySelector('canvas')).filter !== 'none',
              getComputedStyle(house('test-tool-1').querySelector('.door')).backgroundImage];
        """, [True, 'none'])

        self.check("key('1'); house('test-game-1').querySelector('.house-sign').click(); return all('.slot').length;", 9)
        wait_for(lambda: {'test-web-1', 'test-game-1'} <= set(self.helper.opens))
        self.assertCountEqual(self.helper.opens, ['test-tool-1', 'test-web-1', 'test-game-1'])
        self.check("""
            await wait(700);
            el('.slot[data-app=test-tool-2]').click();
            key('ArrowRight'); const before = frame(); key('ArrowDown');
            return [before !== null, frame() !== null && before !== frame()];
        """, [True, True])
        wait_for(lambda: len(self.helper.opens) == 4)
        self.assertEqual(self.helper.opens[-1], 'test-tool-2')
        self.check("""
            await wait(700);
            key('Escape');
            type('pa');
            const paint = frame();
            key('Backspace');
            const query = el('.finder-q').textContent;
            key('Escape');
            type('document');
            const generic = [frame(), el('.finder-row small').textContent, (await el('.finder-row img').decode(), true)];
            key('Escape');
            type('pdf');
            const keyword = all('.finder-row').map(row => row.dataset.app);
            key('Escape');
            return [paint, query, generic, keyword, el('.finder-q').textContent, all('.is-dim').length];
        """, ['test-paint', 'p', ['test-viewer', 'Document Viewer', True], ['test-archive', 'test-viewer'], '', 0])
        self.helper.results['test-paint'] = dict(ok=False, state='failed', error='start_failed',
                                                message='could not start the app')
        self.check("type('pa'); el('.finder-row').click(); return frame();", 'test-paint')
        wait_for(lambda: self.helper.opens[-1] == 'test-paint')
        self.view.until('document.querySelector(".finder-hint").textContent.includes("could not start the app")')
        self.check("""
            const error = el('.finder-hint').textContent;
            await wait(5300);
            const hint = el('.finder-hint').textContent;
            window.dispatchEvent(new Event('blur'));
            return [error, hint, frame(), el('.finder-q').textContent];
        """, ["Couldn't open Test Paint: could not start the app", 'Enter opens Test Paint', None, ''])

    def check_grid(self):
        self.check("""
            const streets = all('.street'), roads = all('.road').map(el => el.getBoundingClientRect());
            const tops = streets.map(el => el.getBoundingClientRect().top);
            const px = name => parseFloat(getComputedStyle(streets[0]).getPropertyValue(name));
            const cell = px('--cell'), pitch = 14 * cell, size = 12 * cell, margin = Math.floor(cell / 2);
            const cols = Math.floor(((960 - 40) / cell - 13) / 14);
            const x = el => parseFloat(el.style.left), end = el => x(el) + parseFloat(el.style.width);
            const houses = all('.house'), lattice = houses.every(el => (x(el) - x(houses[0])) % pitch === 0);
            const firstR = 960 + 15 * cell, lastL = 960 - 15 * cell;
            const plots = streets.every(street => ['L', 'R'].every(side => {
              const row = street.querySelector('.plots-' + side);
              const local = [...street.querySelectorAll(`.house[data-side="${side}"]`)];
              const count = Math.max(cols, ...local.map(el => Number(el.dataset.slot) + 1));
              return Number(row.dataset.n) === count && parseFloat(row.style.width) === (count - 1) * pitch + size + 2 * margin
                && (side === 'L' ? end(row) === lastL + margin : x(row) === firstR - margin)
                && local.every(el => (x(el) - margin - x(row)) % pitch === 0 && x(el) - margin >= x(row)
                  && x(el) + size + margin <= end(row));
            }));
            return {streets: tops, equal: tops.slice(1).every((top, i) => top - tops[i] === 202), roads: roads.length,
              full: roads.every(road => road.left === 0 && road.right === innerWidth && road.height === 16),
              lattice, plots};
        """, dict(streets=[126, 328, 530, 732], equal=True, roads=4, full=True, lattice=True, plots=True))

    def check_terraces(self):
        from PIL import Image

        with Image.open(self.view.snapshot()) as photo:
            self.assertEqual(photo.size, (1920, 1080))
            photo = photo.convert('RGB')
            for base in (312, 514, 716, 918):
                samples = [photo.getpixel((20, y)) for y in (base - 12, base + 1, base + 17, base + 20)]
                self.assertEqual(samples, [(138, 178, 84), (43, 40, 50), (138, 178, 84), (54, 80, 42)])

    def check_empty_plots(self):
        from PIL import Image

        # In the one-house town the entire right side is vacant. Sample inside its first slab and in the next gap.
        with Image.open(self.view.snapshot()) as snapshot:
            photo = snapshot.convert('RGB')
            for base in (312, 514, 716, 918):
                with self.subTest(road_y=base):
                    self.assertEqual(photo.getpixel((1170, base - 3)), (185, 199, 162), 'empty plot slab')
                    self.assertEqual(photo.getpixel((1243, base - 3)), (138, 178, 84), 'turf between plots')

    def check_slid_grid(self):
        self.check("""
            const bounds = id => {
              const {left, right} = house('test-' + id).getBoundingClientRect();
              return [left, right];
            };
            return [snapshot().streetOffsets.system_tools,
              ['web-3', 'game-3', 'work-3', 'tool-7'].map(bounds),
              ['web-6', 'game-6', 'work-6', 'tool-2'].map(bounds)];
        """, [196, [[673, 757]] * 4, [[1261, 1345]] * 4])

    def check_street(self):
        self.replace_town((9, 7, 9, 20))
        if self.look == 'day':
            self.check_grid()
        self.picture('forty-five')
        positions = """return Object.fromEntries(all('.house').map(
            el => [el.dataset.app, [el.dataset.side, Number(el.dataset.slot), parseFloat(el.style.left)]]));"""
        whole = self.view.evaluate(COMMON + positions)
        self.replace_town((9, 7, 9, 20), holes=('test-web-1',))
        removed = self.view.evaluate(COMMON + positions)
        self.assertEqual(whole.pop('test-web-1')[:2], ['L', 0])
        self.assertEqual(removed, whole)
        for app in self.helper.houses:
            place = app['place']
            index, side, slot = int(place[1]), place[2], int(place[3])
            expected = index * (index + 1) // 2 + slot
            gap, pitch = (210, 98) if self.look == 'day' else (200, 102)
            x = 960 - gap / 2 - expected * pitch - 84 if side == 'L' else 960 + gap / 2 + expected * pitch
            self.assertEqual(removed[app['id']], [side, expected, x])
        self.check("""
            return [house('test-web-2').getBoundingClientRect().left > 960,
              house('test-web-3').getBoundingClientRect().right < 960, !inView(house('test-tool-19')),
              all('.street-end:not([hidden])').map(el => el.textContent)];
        """, [True, True, True, ['‹ 2', '2 ›']])
        self.check("""
            type('tool2');
            const counts = all('.street-end:not([hidden])').map(el => el.textContent);
            key('Escape'); type('tool19');
            return [counts, frame()];
        """, [['‹ 0', '1 ›'], 'test-tool-19'])
        self.check("""
            await wait(450);
            const tool = house('test-tool-19'), other = house('test-web-2');
            const group = tool.closest('.street'), view = group.querySelector('.view');
            const mask = getComputedStyle(view).maskImage;
            const shape = tool.querySelector('.frame').getBoundingClientRect();
            const fadeFitsFrame = !document.documentElement.classList.contains('day') ||
              (mask.includes('20px') && mask.includes('40px') && shape.left >= 40 && shape.right <= 1880);
            return [inView(tool), inView(other) && other.getBoundingClientRect().left > 960, fadeFitsFrame];
        """, [True, True, True])
        self.picture('typing')
        self.check("""
            key('Escape'); await wait(390);
            return [!inView(house('test-tool-19')), inView(house('test-tool-1'))];
        """, [True, True])
        self.check("""
            const before = snapshot(), group = house('test-tool-19').closest('.street');
            group.querySelector('.end-L').click();
            let intermediate = false;
            for (let i = 0; i < 24; i++) {
              await new Promise(requestAnimationFrame);
              const current = snapshot(), offset = current.streetOffsets.system_tools;
              if (offset <= 1 || offset >= before.viewport.width / 10 - 20) continue;
              const box = world => world.occluders.find(box => box.id === 'house:test-tool-19');
              const ledge = (world, id) => world.surfaces.find(ledge => ledge.id === id);
              const roof = 'roof:test-tool-19', road = 'street:system_tools';
              const delta = house('test-tool-19').getBoundingClientRect().left - box(before).l;
              const roadOffset = document.documentElement.classList.contains('day') ? 0 : offset;
              intermediate = Math.abs(delta - offset) < 0.1 &&
                Math.abs(box(current).l - box(before).l - offset) < 0.1 &&
                Math.abs(ledge(current, roof).x1 - ledge(before, roof).x1 - offset) < 0.1 &&
                Math.abs(ledge(current, road).x1 - ledge(before, road).x1 - roadOffset) < 0.1;
              break;
            }
            await wait(380);
            return [intermediate, inView(house('test-tool-19')), !inView(house('test-tool-14'))];
        """, [True, True, True])
        if self.look == 'day':
            self.check_slid_grid()
        self.check("""
            type('tool14'); await wait(390);
            const offset = snapshot().streetOffsets.system_tools;
            const day = document.documentElement.classList.contains('day');
            return [frame(), inView(house('test-tool-14')), !day || offset % 98 === 0];
        """, ['test-tool-14', True, True])
        self.check("""
            window.dispatchEvent(new Event('blur')); await wait(390);
            return [frame(), snapshot().streetOffsets.system_tools];
        """, [None, 0])
        self.check("""
            const street = house('test-tool-19').closest('.street');
            street.querySelector('.end-R').click(); await wait(390);
            const right = inView(house('test-tool-20'));
            street.querySelector('.street-sign').click(); await wait(390);
            return [right, snapshot().streetOffsets.system_tools];
        """, [True, 0])

    def check_rest(self):
        result = self.view.evaluate(COMMON + """
            const before = pageProbe();
            const changes = {clock: 0, star: 0, other: 0, animation: 0};
            const animations = () => document.getAnimations().filter(a => a.playState === 'running').length;
            changes.animation = animations();
            const animated = () => changes.animation++;
            document.addEventListener('animationstart', animated, true);
            document.addEventListener('transitionrun', animated, true);
            const observer = new MutationObserver(list => {
              for (const entry of list) {
                const el = entry.target.nodeType === Node.TEXT_NODE ? entry.target.parentNode : entry.target;
                if (el.closest('.clock')) changes.clock++;
                else if (el.matches('.star') && entry.type === 'attributes' && entry.attributeName === 'style')
                  changes.star++;
                else changes.other++;
              }
            });
            observer.observe(document.documentElement, {subtree: true, childList: true, attributes: true,
              characterData: true});
            await wait(13000);
            observer.disconnect();
            document.removeEventListener('animationstart', animated, true);
            document.removeEventListener('transitionrun', animated, true);
            changes.animation += animations();
            const after = pageProbe();
            return {...changes, frames: after.frames - before.frames, draws: after.draws - before.draws};
        """, duration=18)
        self.assertEqual({key: result[key] for key in ('other', 'animation', 'frames', 'draws')},
                         dict(other=0, animation=0, frames=0, draws=0))
        self.assertLessEqual(result['clock'], 2)
        if self.look == 'day':
            self.assertEqual(result['star'], 0)
        else:
            self.assertIn(result['star'], (3, 4))
        self.measure_memory()

    def check_reconnect(self):
        self.helper.set_running(['test-tool-3'])
        self.view.until('document.querySelector(".house[data-app=test-tool-3].is-running")')
        self.helper.drop()
        self.view.until('document.querySelector(".finder-hint").textContent === "Opening is back in a moment"')
        launches = list(self.helper.opens)
        self.check("""
            key('2'); el('.slot[data-app=test-web-2]').click(); house('test-tool-3').click();
            type('tool3'); key('Enter'); key('Escape');
            return [all('.house').length, all('.house.is-running').map(el => el.dataset.app),
              el('.house').getAttribute('aria-disabled')];
        """, [44, ['test-tool-3'], 'true'])
        self.assertEqual(self.helper.opens, launches)
        self.picture('helper-away')
        self.helper.revision = None
        self.helper.running = ['test-web-2']
        self.helper.start()
        self.view.until('document.querySelector(".house[data-app=test-web-2].is-running[aria-disabled=false]")')
        self.check("key('2'); return all('.house').length;", 44)
        wait_for(lambda: len(self.helper.opens) == len(launches) + 1)
        self.assertEqual(self.helper.opens[-1], 'test-web-2')
        self.helper.publish('empty', [])
        self.view.until('!document.querySelector(".house")')
        self.check("return [all('.slot').length, all('.slot[data-app]').length];", [9, 0])

    def play(self, look):
        self.look = look
        with self.helper, self.gui(look) as self.view:
            self.view.until('!!window.pageProbe?.().first && document.querySelectorAll(".house").length === 24')
            self.check(r"""
                return [pageProbe().first.sort(), el('.battery-text').textContent, el('.battery').classList.contains('charging'),
                  /^\d\d:\d\d$/.test(el('.clock-time').textContent), !!el('.clock-date').textContent,
                  getComputedStyle(el('#stage')).transform, all('.star').length];
            """, [['test-tool-3', 'test-web-2'], '68%', True, True, True, 'matrix(1, 0, 0, 1, 0, 0)',
                  0 if look == 'day' else 90])
            if look == 'day':
                self.check_grid()
                self.check_terraces()
            self.picture('home')
            self.check_interactions()
            if look == 'day':
                self.replace_town((1, 0, 0, 0))
                self.check_grid()
                self.check_empty_plots()
            self.check_street()
            self.check_rest()
            self.check_reconnect()

    def test_day(self):
        self.play('day')

    def test_night(self):
        self.play('night')

    def test_saved_town_without_battery_and_place_assignment(self):
        self.look = 'day'
        homes, programs = generated_town((3, 0, 0, 0), self.icon)
        next(home for home in homes if home['id'] == 'test-web-2').pop('place')
        program = load_program()
        gui = self.gui('day', fallback=True)
        program.save_home(gui.home_path, program.page_home(STUDY_PALETTE, homes, {p['id']: p['name'] for p in programs}))
        with gui as self.view:
            self.view.until('document.querySelectorAll(".house").length === 3')
            self.check("""
                return [el('.battery').hidden, el('.finder-hint').textContent,
                  house('test-web-2').dataset.side, house('test-web-2').dataset.slot,
                  house('test-web-2').querySelector('b').textContent,
                  el('#hotbar').getBoundingClientRect().height, all('.slot').length];
            """, [True, 'Opening is back in a moment', 'R', '1', 'Test Web 2', 78, 9])

    def test_full_kept_town_lights_on_first_draw_while_catalogue_is_pending(self):
        houses, programs = town(200)
        for row in houses:
            row.update(id=row['id'].ljust(64, '-'), short='🟦' * 64)
        for row in programs:
            row.update(id=row['id'].ljust(64, '-'), name='🟧' * 64)
        self.helper.houses, self.helper.programs = houses, programs
        self.helper.revision = None
        self.helper.page_size = 25
        lit = houses[0]['id']
        self.helper.running = [lit]
        last_page_requested = threading.Event()
        release_last_page = threading.Event()

        def delay_last_page(request):
            if request['op'] == 'list_apps' and request.get('cursor') == '175':
                last_page_requested.set()
                release_last_page.wait(5)

        self.helper.before_page = delay_last_page
        program = load_program()
        gui = self.gui('day')
        cached = program.page_home(StandIn.palette, houses, {row['id']: row['name'] for row in programs})
        program.save_home(gui.home_path, cached)
        self.assertGreater(gui.home_path.stat().st_size, 2 * program.MAX_MESSAGE)
        self.assertEqual(program.load_home(gui.home_path), cached)
        with self.helper, gui as self.view:
            try:
                self.assertTrue(last_page_requested.wait(4))
                self.view.until('!!window.pageProbe?.().first && document.querySelector("#stage")?.hidden === false')
                self.check("""
                    return [all('.house').length, pageProbe().first, el('.house').getAttribute('aria-disabled'),
                      el('.finder-hint').textContent, aresosHome.programs().length,
                      (await aresosHome.open(el('.house').dataset.app)).state];
                """, [200, [lit], 'true', 'Opening is back in a moment', 0, 'failed'])
                self.assertEqual(self.helper.opens, [])
            finally:
                release_last_page.set()
            self.view.until('document.querySelector(".house.is-running[aria-disabled=false]")')
            self.check("return [all('.house').length, el('.house.is-running').dataset.app, aresosHome.programs().length];",
                       [200, lit, 200])
            self.assertEqual(program.load_home(gui.home_path), cached)
