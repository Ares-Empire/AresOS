"""The native laptop home: its layout model on its own, and the real window through the test channel."""

from datetime import datetime
import os
from pathlib import Path
import shutil
import threading
import time
import unittest

from laptop_home_headless import ROOT, Headless, headless_available, load_program, scratch, wait_for
from laptop_home_helper import IMAGE_FONTS, STUDY_FONTS, STUDY_PALETTE, StandIn, generated_town, png, town

program = load_program()
PICTURES = ROOT / 'reviews/53f-native-home/pictures'
CLOCK = '2026-11-19T09:41:00'
RUNNING = ['test-web-2', 'test-tool-3']
GOLD_HI, GOLD, TURF, SLAB, PAVING, BANK_EDGE = (237, 202, 119), (207, 162, 79), (138, 178, 84), (185, 199, 162), \
    (43, 40, 50), (54, 80, 42)
WALL, NIGHT_ROAD, DOOR_FRAME = (13, 13, 16), (24, 24, 28), (19, 20, 25)


def make_town(look, streets, *, holes=(), running=RUNNING, online=True, opener=None, timers=None):
    houses, programs = generated_town(streets, Path('/nonexistent/icon.png'), holes=holes)
    home = program.page_home(STUDY_PALETTE, houses, {row['id']: row['name'] for row in programs})
    catalogue, _ = program.catalogue(programs)
    timers = timers if timers is not None else []
    result = program.Town(look, home, now=lambda: datetime.fromisoformat(CLOCK), opener=opener,
                          schedule=lambda ms, callback: timers.append((ms, callback)) or len(timers))
    result.apply(dict(home=home, programs=catalogue, running=list(running), status=program.NO_BATTERY,
                      helper=online), ['home', 'programs', 'running', 'status', 'helper'])
    return result, houses


def houses_of(scene):
    return {house['id']: house for street in scene['streets'] for house in street['houses']}


def street_of(scene, key):
    return next(street for street in scene['streets'] if street['key'] == key)


def in_view(house):
    return house['left'] >= 0 and house['left'] + house['size'] <= program.WIDTH


def end_labels(scene):
    return [end['label'] for street in scene['streets'] for end in street['ends'].values() if end['cut']]


# GTK 4 links the Vulkan loader and libepoxy, which maps glvnd's libEGL and libGLX dispatchers; those load no
# driver by themselves. A GPU driver shows as a vendor library (libEGL_mesa, libGLX_nvidia, libvulkan_intel), Mesa's
# gallium or LLVM, or anything NVIDIA's.
DRIVERS = ('libegl_', 'libglx_', 'libvulkan_', 'libgallium', 'libllvm', 'nvidia', '/dri/', 'webkit')


def drivers_mapped(pid):
    return sorted({line.split()[-1] for line in Path(f'/proc/{pid}/maps').read_text().lower().splitlines()
                   if '/' in line and any(name in line for name in DRIVERS)})


def centre(rect):
    return rect[0] + rect[2] / 2, rect[1] + rect[3] / 2


class GeometryTest(unittest.TestCase):
    def check_grid(self, scene):
        streets, grid = scene['streets'], scene['grid']
        cell, pitch, size, cols = grid['cell'], grid['pitch'], grid['size'], grid['cols']
        margin = cell // 2
        self.assertEqual([street['top'] for street in streets], [126, 328, 530, 732])
        # REVIEW-3 finding 6: each street stands on its own terrace, whose road is at the street's foot.
        self.assertEqual([street['base'] for street in streets], [312, 514, 716, 918])
        self.assertTrue(all(street['road'] == dict(rect=[0, street['base'], 1920, 16], slides=False,
                                                   joint=(960 - grid['gap'] // 2) % (2 * cell))
                            for street in streets))
        houses = list(houses_of(scene).values())
        self.assertTrue(all((house['x'] - houses[0]['x']) % pitch == 0 for house in houses), 'lattice')
        first_right, last_left = 960 + 15 * cell, 960 - 15 * cell
        for street in streets:
            for plots in street['plots']:
                side = plots['side']
                local = [house for house in street['houses'] if house['side'] == side]
                # REVIEW-3 finding 6: the plot count is per street and side, at least the screen's columns.
                count = max([cols] + [house['slot'] + 1 for house in local])
                with self.subTest(street=street['key'], side=side):
                    self.assertEqual(plots['count'], count)
                    self.assertEqual(plots['width'], (count - 1) * pitch + size + 2 * margin)
                    self.assertEqual(plots['slabs'], [plots['left'] + k * pitch for k in range(count)])
                    if side == 'L':
                        self.assertEqual(plots['left'] + plots['width'], last_left + margin)
                    else:
                        self.assertEqual(plots['left'], first_right - margin)
                    for house in local:
                        self.assertEqual((house['x'] - margin - plots['left']) % pitch, 0)
                        self.assertGreaterEqual(house['x'] - margin, plots['left'])
                        self.assertLessEqual(house['x'] + size + margin, plots['left'] + plots['width'])

    def test_day_grid_and_terraces(self):
        for streets in ((7, 4, 5, 8), (1, 0, 0, 0), (9, 7, 9, 20)):
            with self.subTest(streets=streets):
                self.check_grid(make_town('day', streets)[0].scene())

    def test_places_by_day_and_night(self):
        for look, (gap, pitch) in (('day', (210, 98)), ('night', (200, 102))):
            whole = {house['id']: [house['side'], house['slot'], house['x']]
                     for house in houses_of(make_town(look, (9, 7, 9, 20))[0].scene()).values()}
            town, houses = make_town(look, (9, 7, 9, 20), holes=('test-web-1',))
            removed = {house['id']: [house['side'], house['slot'], house['x']]
                       for house in houses_of(town.scene()).values()}
            self.assertEqual(whole.pop('test-web-1')[:2], ['L', 0])
            self.assertEqual(removed, whole)
            for app in houses:
                place = app['place']
                index, side, slot = int(place[1]), place[2], int(place[3])
                expected = index * (index + 1) // 2 + slot
                x = 960 - gap // 2 - expected * pitch - 84 if side == 'L' else 960 + gap // 2 + expected * pitch
                self.assertEqual(removed[app['id']], [side, expected, x], (look, app['id']))
            if look == 'night':
                # Night street: the road runs from the farthest house to the farthest house, two blocks beyond.
                street = street_of(town.scene(), 'system_tools')
                self.assertEqual(street['road']['rect'][0], 960 - 100 - 9 * 102 - 84 - 14)
                self.assertTrue(street['road']['slides'])

    def check_slides(self, look):
        day = look == 'day'
        town, _ = make_town(look, (9, 7, 9, 20))

        def house(scene, app_id):
            return houses_of(scene)[f'test-{app_id}']

        scene = town.scene()
        self.assertGreater(house(scene, 'web-2')['left'], 960)
        self.assertLess(house(scene, 'web-3')['left'] + house(scene, 'web-3')['size'], 960)
        self.assertFalse(in_view(house(scene, 'tool-19')))
        self.assertEqual(end_labels(scene), ['‹ 2', '2 ›'])
        for key in 'tool2':
            town.key(key)
        self.assertEqual(end_labels(town.scene()), ['‹ 0', '1 ›'])
        town.key('Escape')
        for key in 'tool19':
            town.key(key)
        scene = town.scene()
        tool, other = house(scene, 'tool-19'), house(scene, 'web-2')
        self.assertEqual(scene['framed'], 'test-tool-19')
        self.assertTrue(in_view(tool))
        self.assertTrue(in_view(other) and other['left'] > 960)
        if day:
            # A framed house beside a cut end: its whole frame stays inside the fade, EDGE from the side.
            frame = tool['frame']
            self.assertTrue(frame[0] >= 40 and frame[0] + frame[2] <= 1880, frame)
            self.assertEqual(street_of(scene, 'system_tools')['offset'] % 98, 0)
        town.key('Escape')
        scene = town.scene()
        self.assertFalse(in_view(house(scene, 'tool-19')))
        self.assertTrue(in_view(house(scene, 'tool-1')))
        street = street_of(scene, 'system_tools')
        hit = town.click(*centre(street['ends']['L']['rect']))
        self.assertEqual((hit['kind'], hit['side']), ('end', 'L'))
        scene = town.scene()
        self.assertTrue(street_of(scene, 'system_tools')['by_hand'])
        self.assertTrue(in_view(house(scene, 'tool-19')))
        self.assertFalse(in_view(house(scene, 'tool-14')))
        if day:
            def bounds(app_id):
                found = house(scene, app_id)
                return [found['left'], found['left'] + found['size']]

            self.assertEqual(street_of(scene, 'system_tools')['offset'], 196)
            self.assertEqual([bounds(app_id) for app_id in ('web-3', 'game-3', 'work-3', 'tool-7')], [[673, 757]] * 4)
            self.assertEqual([bounds(app_id) for app_id in ('web-6', 'game-6', 'work-6', 'tool-2')],
                             [[1261, 1345]] * 4)
        for key in 'tool14':
            town.key(key)
        scene = town.scene()
        self.assertEqual(scene['framed'], 'test-tool-14')
        self.assertTrue(in_view(house(scene, 'tool-14')))
        if day:
            self.assertEqual(street_of(scene, 'system_tools')['offset'] % 98, 0)
        town.blur()
        scene = town.scene()
        self.assertEqual((scene['framed'], street_of(scene, 'system_tools')['offset']), (None, 0))
        town.click(*centre(street_of(scene, 'system_tools')['ends']['R']['rect']))
        self.assertTrue(in_view(house(town.scene(), 'tool-20')))
        town.click(*centre(street_of(town.scene(), 'system_tools')['sign']['rect']))
        self.assertEqual(street_of(town.scene(), 'system_tools')['offset'], 0)

    def test_slide_targets_hand_slides_and_end_counts_by_day(self):
        self.check_slides('day')

    def test_slide_targets_hand_slides_and_end_counts_by_night(self):
        self.check_slides('night')

    def test_hand_slide_moves_the_frame_to_a_visible_match(self):
        town, _ = make_town('day', (9, 7, 9, 20))
        for key in 'tool1':
            town.key(key)
        scene = town.scene()
        self.assertEqual(scene['framed'], 'test-tool-1')
        town.click(*centre(street_of(scene, 'system_tools')['ends']['L']['rect']))
        scene = town.scene()
        visible = street_of(scene, 'system_tools')['visible']
        self.assertIn(scene['framed'], visible)
        self.assertTrue(scene['framed'].startswith('test-tool-1'))


class FinderTest(unittest.TestCase):
    def test_ranking_keys_and_hit_regions(self):
        opened = []
        timers = []
        town, _ = make_town('day', (7, 4, 5, 8), timers=timers,
                            opener=lambda app_id, callback: opened.append((app_id, callback)))
        for key in '/tool':
            town.key(key)
        scene = town.scene()
        dims = [house for house in houses_of(scene).values() if house['dim']]
        self.assertEqual([scene['framed'], len(dims), scene['query'], scene['finder']['hint']],
                         ['test-tool-1', 16, 'tool', 'Enter opens Test Tool 1'])
        self.assertTrue(houses_of(scene)['test-tool-1']['framed'])
        town.key('Enter')
        self.assertEqual([app_id for app_id, _ in opened], ['test-tool-1'])
        self.assertEqual(town.scene()['finder']['hint'], 'Enter opens Test Tool 1')
        self.assertTrue(houses_of(town.scene())['test-tool-1']['opening'])
        opened[-1][1]({'state': 'starting'})
        self.assertEqual(town.scene()['query'], '')
        opening = next(timer for timer in timers if timer[0] == 600)   # the caret's 550 ms blinks wait too
        timers.remove(opening)
        opening[1]()
        self.assertFalse(houses_of(town.scene())['test-tool-1']['opening'])
        town.key('1')
        self.assertEqual(opened[-1][0], 'test-web-1')
        sign = houses_of(town.scene())['test-game-1']['box']
        self.assertEqual(town.click(sign[0] + sign[2] / 2, sign[1] + 4)['id'], 'test-game-1')
        slot = next(slot for slot in town.scene()['slots'] if slot['id'] == 'test-tool-2')
        town.click(*centre(slot['rect']))
        self.assertEqual([app_id for app_id, _ in opened], ['test-tool-1', 'test-web-1', 'test-game-1', 'test-tool-2'])
        town.key('ArrowRight')
        before = town.scene()['framed']
        town.key('ArrowDown')
        self.assertTrue(before is not None and town.scene()['framed'] not in (None, before))
        town.key('Escape')
        for key in 'pa':
            town.key(key)
        self.assertEqual(town.scene()['framed'], 'test-paint')
        town.key('Backspace')
        self.assertEqual(town.scene()['query'], 'p')
        town.key('Escape')
        for key in 'document':
            town.key(key)
        scene = town.scene()
        self.assertEqual([scene['framed'], scene['finder']['rows'][0]['kind']], ['test-viewer', 'Document Viewer'])
        town.key('Escape')
        for key in 'pdf':
            town.key(key)
        self.assertEqual([row['id'] for row in town.scene()['finder']['rows']], ['test-archive', 'test-viewer'])
        town.key('Escape')
        scene = town.scene()
        self.assertEqual((scene['query'], [h for h in houses_of(scene).values() if h['dim']]), ('', []))
        # A failure shows on the typing line for five seconds; the query stays.
        for key in 'pa':
            town.key(key)
        row = town.scene()['finder']['rows'][0]
        self.assertEqual(town.click(*centre(row['rect']))['id'], 'test-paint')
        opened[-1][1]({'state': 'failed', 'message': 'could not start the app'})
        self.assertEqual(town.scene()['finder']['hint'], "Couldn't open Test Paint: could not start the app")
        expire = next(callback for ms, callback in timers if ms == 5000)
        expire()
        self.assertEqual(town.scene()['finder']['hint'], 'Enter opens Test Paint')
        town.blur()
        self.assertEqual((town.scene()['framed'], town.scene()['query']), (None, ''))

    def test_offline_town_opens_nothing(self):
        opened = []
        town, _ = make_town('night', (7, 4, 5, 8), online=False, opener=lambda *args: opened.append(args))
        town.key('2')
        house = houses_of(town.scene())['test-tool-3']['box']
        town.click(*centre(house))
        for key in 'tool3':
            town.key(key)
        town.key('Enter')
        self.assertEqual(opened, [])
        self.assertEqual(town.scene()['finder']['hint'], 'Opening is back in a moment')


def pixel(photo, x, y):
    return photo.getpixel((int(x), int(y)))[:3]


def near(first, second, tolerance):
    return max(abs(a - b) for a, b in zip(first, second)) <= tolerance


def blend(back, front, alpha):
    return tuple(round(b + (f - b) * alpha) for b, f in zip(back, front))


def gold_door(t):
    stops = ((0, (255, 231, 166)), (0.55, (233, 176, 74)), (1, (185, 121, 30)))
    for (a, first), (b, second) in zip(stops, stops[1:]):
        if t <= b:
            return blend(first, second, (t - a) / (b - a))


@unittest.skipUnless(headless_available(), 'headless labwc, bwrap, wlr-randr, Mesa pins, GTK 4, Pango and Cairo')
class MotionTest(unittest.TestCase):
    """The glide, the puff and the caret against a hand-driven clock and timers, as the frame clock would drive them."""

    def motion_town(self, look='day'):
        self.now, self.frames, self.timers = 100.0, [], []
        town, _ = make_town(look, (9, 7, 9, 20), opener=lambda _app_id, _callback: None, timers=self.timers)
        town.motion, town.clock = (lambda: self.frames.append(self.now)), (lambda: self.now)
        return town

    def test_glide_moves_the_street_and_keeps_its_rules_at_rest(self):
        for look in ('day', 'night'):
            with self.subTest(look=look):
                town = self.motion_town(look)
                before = street_of(town.scene(), 'system_tools')
                town.set_query('tool19')
                self.assertEqual(self.frames, [100.0], 'a glide asks for frames once')
                target = street_of(town.scene(), 'system_tools')['offset']
                self.assertNotEqual(target, 0)
                self.assertEqual(street_of(town.scene(), 'system_tools')['shift'], 0, 'drawn at home until a frame')
                self.assertTrue(town.advance(100.15))
                scene = town.scene()
                street, house = street_of(scene, 'system_tools'), houses_of(scene)['test-tool-19']
                shift = target * program.ease_out(0.5)
                self.assertAlmostEqual(street['shift'], shift)
                self.assertTrue(0 < abs(shift) < abs(target))
                # 53c's intermediate frame: the house, its sign, its plots or road move together with the street.
                old = next(h for h in before['houses'] if h['id'] == 'test-tool-19')
                self.assertAlmostEqual(house['left'] - old['left'], shift)
                self.assertAlmostEqual(house['box'][0] - old['box'][0], shift)
                self.assertAlmostEqual(house['sign']['centre'] - old['sign']['centre'], shift)
                self.assertAlmostEqual(street['sign']['centre'] - before['sign']['centre'], shift)
                if look == 'day':
                    self.assertAlmostEqual(street['plots'][0]['left'] - before['plots'][0]['left'], shift)
                    self.assertEqual(street['road'], before['road'], 'the day road stands still')
                else:
                    self.assertAlmostEqual(street['road']['rect'][0] - before['road']['rect'][0], shift)
                # Where it comes to rest decides the ends and the frame, as 53c's layout did.
                self.assertEqual(street['offset'], target)
                self.assertEqual(street['target'], target)
                self.assertFalse(town.advance(100.301))
                self.assertEqual(street_of(town.scene(), 'system_tools')['shift'], target)
                # Clearing the line glides it home from where it is drawn.
                self.now = 100.301
                town.set_query('')
                self.assertTrue(town.advance(100.4))
                self.assertTrue(0 < abs(street_of(town.scene(), 'system_tools')['shift']) < abs(target))
                self.assertFalse(town.advance(100.61))
                self.assertEqual(street_of(town.scene(), 'system_tools')['shift'], 0)

    def test_puff_rises_and_fades_then_stops(self):
        town = self.motion_town()
        town.open('test-web-3')
        house = houses_of(town.scene())['test-web-3']
        self.assertEqual(len(house['puff']), 9)
        self.assertTrue(all(alpha == 1 for _, _, alpha in house['puff']))
        start = [(x, y) for x, y, _ in house['puff']]
        self.assertTrue(town.advance(100.301))
        moved = houses_of(town.scene())['test-web-3']['puff']
        self.assertTrue(all(y1 < y0 for (_, y0), (_, y1, _) in zip(start, moved)), 'the puff rises')
        self.assertTrue(all(0 < alpha < 1 for _, _, alpha in moved))
        self.assertFalse(town.advance(100.601))
        self.assertEqual(houses_of(town.scene())['test-web-3']['puff'], [])
        town.open('test-other-1') if 'test-other-1' in {a['id'] for a in town.programs} else None
        self.assertEqual(town.puffs, {}, 'a program without a house has no puff')

    def test_caret_blinks_five_times_then_stays(self):
        town = self.motion_town()
        town.set_query('t')
        blinks = []
        for _ in range(12):
            pending = [timer for timer in self.timers if timer[0] == 550]
            if not pending:
                break
            self.timers.remove(pending[-1])
            pending[-1][1]()
            blinks.append(town.scene()['finder']['caret'])
        self.assertEqual(blinks, [False, True] * 5)
        self.assertTrue(town.scene()['finder']['caret'])
        town.set_query('')
        self.assertFalse(town.scene()['finder']['caret'], 'no caret on an empty line')

    def test_hover_keys_and_the_end_sign_border(self):
        town = self.motion_town()
        scene = town.scene()
        house = houses_of(scene)['test-web-1']
        self.assertEqual(program.hover_key(program.hit_test(scene, *centre(house['box']))), 'house:test-web-1')
        slot = scene['slots'][0]
        self.assertEqual(program.hover_key(program.hit_test(scene, *centre(slot['rect']))), 'slot:0')
        tools = street_of(scene, 'system_tools')
        side, end = next((side, end) for side, end in tools['ends'].items() if end['cut'])
        key = program.hover_key(program.hit_test(scene, *centre(end['rect'])))
        self.assertEqual(key, f'end:system_tools:{side}')
        self.assertEqual(program.hover_key(program.hit_test(scene, *centre(tools['sign']['rect']))),
                         'sign:system_tools')
        town.set_hover(key)
        self.assertTrue(street_of(town.scene(), 'system_tools')['ends'][side]['hover'])
        self.assertIsNone(program.hover_key(None))


class WindowTest(unittest.TestCase):
    def setUp(self):
        workspace = scratch()
        self.addCleanup(workspace.cleanup)
        self.path = Path(workspace.name)
        self.icon = self.path / 'icon.png'
        self.icon.write_bytes(png())
        self.helper = StandIn(self.path / 'shell.sock', page_size=4)
        self.helper.palette = STUDY_PALETTE
        self.helper.houses, self.helper.programs = generated_town((7, 4, 5, 8), self.icon)
        self.helper.running = list(RUNNING)

    def gui(self, look='day', *, fallback=False, **fields):
        fields.setdefault('broken', os.environ.get('LAPTOP_HOME_TEST_BROKEN') or None)
        return Headless(self.path, self.helper.path, look=look, font_dir=IMAGE_FONTS if fallback else STUDY_FONTS,
                        battery=not fallback, clock=CLOCK, **fields)

    def picture(self, name, **state):
        path = self.view.picture(**state)
        if os.environ.get('LAPTOP_HOME_TEST_PICTURES') and not name.startswith('check-'):
            PICTURES.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, PICTURES / f'{self.look}-{name}.png')
        from PIL import Image
        with Image.open(path) as photo:
            self.assertEqual(photo.size, (1920, 1080))
            return photo.convert('RGB')

    def replace_town(self, streets, *, holes=()):
        houses, programs = generated_town(streets, self.icon, holes=holes)
        self.helper.change_catalogue(str(self.helper.serial), programs, houses)
        return self.view.until(lambda scene: len(houses_of(scene)) == len(houses))

    def cell_sample(self, house):
        """The centre of a solid block of a house's face, away from its door."""
        cells = program.decode_cells(next(row['cells'] for row in self.helper.houses if row['id'] == house['id']),
                                     STUDY_PALETTE)
        cell, size = house['cell'], house['size']
        u, v = next((u, v) for v in range(11, 2, -1) for u in range(4) if cells[v][u] not in (None, 'door'))
        colour = program.rgb(cells[v][u])
        x, y = house['left'] + u * cell + cell // 2, house['base'] - size + (11 - v) * cell + cell // 2
        return x, y, colour

    def check_terraces(self, photo):
        for base in (312, 514, 716, 918):
            samples = [pixel(photo, 20, y) for y in (base - 12, base + 1, base + 17, base + 20)]
            self.assertEqual(samples, [TURF, PAVING, TURF, BANK_EDGE], 'terraces')

    def check_houses(self):
        """An idle house, a lit one with its gold door, a dimmed one and the frame around the best hit."""
        day = self.look == 'day'
        scene = self.view.model()
        idle, lit = houses_of(scene)['test-game-1'], houses_of(scene)['test-web-2']
        photo = self.picture('check-houses')
        x, y, colour = self.cell_sample(idle)
        expected = tuple(round(c * 255) for c in program.idle_colour(colour, self.look))
        self.assertTrue(near(pixel(photo, x, y), expected, 2), ('idle house', pixel(photo, x, y), expected))
        x, y, colour = self.cell_sample(lit)
        expected = tuple(round(c * 255) for c in colour)
        self.assertTrue(near(pixel(photo, x, y), expected, 2), ('lit house', pixel(photo, x, y), expected))
        door = lit['door']
        # The bottom rows take the mat's glow at night, painted after the door as on the page.
        for row in (1, door[3] // 2):
            got, want = pixel(photo, door[0] + door[2] // 2, door[1] + row), gold_door((row + 0.5) / door[3])
            self.assertTrue(near(got, want, 3), ('gold door', row, got, want))
        if day:
            self.assertEqual(pixel(photo, door[0] - 1, door[1] + door[3] // 2), DOOR_FRAME, 'gold door frame')
        self.view.type('tool2')
        scene = self.view.model()
        dimmed, framed = houses_of(scene)['test-game-1'], houses_of(scene)[scene['framed']]
        self.assertEqual(scene['framed'], 'test-tool-2')
        photo = self.picture('check-frame')
        x, y, colour = self.cell_sample(dimmed)
        idle_colour = tuple(c * 255 for c in program.idle_colour(colour, self.look))
        expected = blend(pixel(photo, 5, y), idle_colour, 0.16 if day else 0.13)
        self.assertTrue(near(pixel(photo, x, y), expected, 3), ('dimmed house', pixel(photo, x, y), expected))
        fx, fy, fw, fh = framed['frame']
        if day:
            self.assertTrue(near(pixel(photo, fx + 1, fy + fh // 2), GOLD_HI, 2), 'frame')
            self.assertLessEqual(max(pixel(photo, fx - 1, fy + fh // 2)), 60, 'frame outline')
        else:
            self.assertTrue(near(pixel(photo, fx, fy + fh // 2), GOLD, 2), 'frame')
        self.view.key('Escape')

    def check_empty_plots(self):
        # In the one-house town the entire right side is vacant. Sample inside its first slab and in the next gap.
        photo = self.picture('check-plots')
        for base in (312, 514, 716, 918):
            with self.subTest(road_y=base):
                self.assertEqual(pixel(photo, 1170, base - 3), SLAB, 'empty plot slab')
                self.assertEqual(pixel(photo, 1243, base - 3), TURF, 'turf between plots')

    def check_cut_ends(self, scene):
        street = street_of(scene, 'system_tools')
        base = street['base']
        photo = self.picture('check-ends')
        if self.look == 'day':
            # The view fades out from EDGE to EDGE / 2: at 19 px only the terrace shows, past EDGE the slab.
            self.assertEqual(pixel(photo, 19, base - 3), TURF, 'fade at EDGE / 2')
            self.assertEqual(pixel(photo, 1900, base - 3), TURF, 'fade at EDGE / 2, right')
            left = street['plots'][0]
            covered = next(x for x in range(40, 200) if any(slab + 3 <= x < slab + left['slab'] + 3 and not any(
                house['left'] <= x < house['left'] + house['size'] for house in street['houses'])
                for slab in left['slabs']))
            self.assertEqual(pixel(photo, covered, base - 3), SLAB, 'past EDGE')
        else:
            # At night the cut end fades into the wall over 120 px, solid for the first 18.
            road = street['road']['rect']
            joints = {x for x in range(0, 200) if (x - road[0]) % 14 == 13}
            self.assertEqual(pixel(photo, 5, base + 8), WALL, 'night fade')
            x = next(x for x in range(130, 140) if x not in joints)
            self.assertEqual(pixel(photo, x, base + 8), NIGHT_ROAD, 'past the night fade')
            x = next(x for x in range(60, 70) if x not in joints)
            self.assertTrue(13 < pixel(photo, x, base + 8)[0] < 24, 'inside the night fade')
        end = street['ends']['L']['rect']
        self.assertLessEqual(max(pixel(photo, end[0] + 3, end[1] + 16)), 26, 'end sign plate')
        yellow = [pixel(photo, x, y) for x in range(end[0], end[0] + end[2]) for y in range(end[1], end[1] + end[3])]
        self.assertGreater(sum(near(p, (254, 216, 61), 50) for p in yellow), 10, 'end sign text')

    def check_rest(self):
        before = self.view.request('counters')
        time.sleep(13)
        after = self.view.request('counters')
        reasons = {name: after['reasons'].get(name, 0) - before['reasons'].get(name, 0) for name in after['reasons']}
        clock, star = reasons.pop('clock', 0), reasons.pop('star', 0)
        self.assertEqual({name: count for name, count in reasons.items() if count}, {})
        self.assertLessEqual(clock, 2)
        self.assertIn(star, (0,) if self.look == 'day' else (3, 4))
        self.assertLessEqual(after['draws'] - before['draws'], clock + star)
        self.assertLessEqual(after['frames'] - before['frames'], clock + star)

    def check_reconnect(self):
        self.helper.set_running(['test-tool-3'])
        self.view.until(lambda scene: houses_of(scene)['test-tool-3']['running'])
        self.helper.drop()
        self.view.until(lambda scene: scene['finder']['hint'] == 'Opening is back in a moment')
        launches = list(self.helper.opens)
        self.view.key('2')
        self.view.click(*centre(next(slot for slot in self.view.model()['slots'] if slot['id'] == 'test-web-2')['rect']))
        self.view.click(*centre(houses_of(self.view.model())['test-tool-3']['box']))
        self.view.type('tool3')
        self.view.key('Enter', 'Escape')
        scene = self.view.model()
        self.assertEqual([len(houses_of(scene)), [h['id'] for h in houses_of(scene).values() if h['running']],
                          scene['online']], [44, ['test-tool-3'], False])
        self.assertEqual(self.helper.opens, launches)
        self.picture('helper-away')
        self.helper.revision = None
        self.helper.running = ['test-web-2']
        self.helper.start()
        self.view.until(lambda scene: scene['online'] and houses_of(scene)['test-web-2']['running'])
        self.view.key('2')
        wait_for(lambda: len(self.helper.opens) == len(launches) + 1)
        self.assertEqual(self.helper.opens[-1], 'test-web-2')
        self.helper.publish('empty', [])
        scene = self.view.until(lambda scene: not houses_of(scene))
        self.assertEqual([len(scene['slots']), [slot for slot in scene['slots'] if slot['id']]], [9, []])

    def check_typing(self):
        """53c's typing picture: tool19 typed on the real keyboard, the long street glided to frame it."""
        self.device.type('tool19')
        scene = self.view.until(lambda scene: scene['query'] == 'tool19' and scene['framed'] == 'test-tool-19'
                                and all(street['shift'] == street['offset'] for street in scene['streets']))
        tools = street_of(scene, 'system_tools')
        self.assertNotEqual(tools['offset'], 0)
        self.assertTrue(in_view(houses_of(scene)['test-tool-19']))
        counters = self.view.request('counters')
        self.assertGreater(counters['reasons'].get('motion', 0), 2, 'the glide drew frames')
        photo = self.picture('typing', caret=True)
        house = houses_of(scene)['test-tool-19']
        x, y, colour = self.cell_sample(house)
        expected = tuple(round(c * 255) for c in colour)
        self.assertTrue(near(pixel(photo, x, y), expected, 2), ('the framed house, lit where the glide left it',
                                                                pixel(photo, x, y), expected, house['left']))
        # Escape clears the line, and the street glides home.
        self.device.press('Escape')
        scene = self.view.until(lambda scene: not scene['query'] and street_of(scene, 'system_tools')['shift'] == 0)
        self.assertEqual(street_of(scene, 'system_tools')['offset'], 0)

    def play(self, look):
        self.look = look
        with self.helper, self.gui(look) as self.view, self.view.virtual_input() as self.device:
            scene = self.view.until(lambda scene: scene['online'] and len(houses_of(scene)) == 24)
            parent = self.view.parent()
            first = wait_for(lambda: self.view.request('counters')['first'])
            self.assertEqual(sorted(first['lit']), sorted(RUNNING))
            self.assertEqual(self.view.request('renderer'), 'GskCairoRenderer')
            self.assertEqual(parent['environment'], {'GDK_DISABLE': 'gl,vulkan', 'GSK_RENDERER': 'cairo'})
            self.assertTrue(parent['drm_hidden'])
            self.assertEqual(drivers_mapped(parent['pid']), [])
            self.assertEqual([scene['battery'], scene['clock']['time'], len(scene['stars'])],
                             [{'level': 68, 'charging': True}, '09:41', 0 if look == 'day' else 90])
            photo = self.picture('home')
            if look == 'day':
                self.check_terraces(photo)
            self.check_houses()
            # Real input through labwc: a click on the sky gives the layer surface the keyboard (and opens nothing),
            # a dead key composes through the input method on the German layout, Escape clears it.
            self.device.click(960, 60)
            self.device.press('dead_circumflex', 'a')
            self.view.until(lambda scene: scene['query'] == 'â')
            self.device.press('Escape')
            self.view.until(lambda scene: scene['query'] == '')
            self.device.type('tool')
            self.view.until(lambda scene: scene['query'] == 'tool')
            self.device.press('Return')
            wait_for(lambda: self.helper.opens == ['test-tool-1'])
            self.view.until(lambda scene: not scene['query'])
            self.helper.set_running(['test-tool-1'])
            self.view.until(lambda scene: houses_of(scene)['test-tool-1']['running']
                            and not houses_of(scene)['test-tool-1']['opening'])
            scene = self.view.model()
            self.assertEqual(next(slot for slot in scene['slots'] if slot['running'])['id'], 'test-tool-1')
            self.picture('opened')
            self.helper.set_running([])
            self.view.until(lambda scene: not any(h['running'] for h in houses_of(scene).values()))
            if look == 'day':
                self.replace_town((1, 0, 0, 0))
                self.check_empty_plots()
            scene = self.replace_town((9, 7, 9, 20))
            self.picture('forty-five')
            self.check_cut_ends(scene)
            self.check_typing()
            self.replace_town((9, 7, 9, 20), holes=('test-web-1',))
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
        gui = self.gui('day', fallback=True)
        program.save_home(gui.home_path, program.page_home(STUDY_PALETTE, homes, {p['id']: p['name'] for p in programs}))
        with gui as self.view:
            scene = self.view.until(lambda scene: len(houses_of(scene)) == 3)
            house = houses_of(scene)['test-web-2']
            self.assertEqual([scene['battery'], scene['finder']['hint'], house['side'], house['slot'], house['name'],
                              program.BAR_HEIGHT, len(scene['slots'])],
                             [None, 'Opening is back in a moment', 'R', 1, 'Test Web 2', 78, 9])
            self.view.request('counters')

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
        gui = self.gui('day')
        cached = program.page_home(StandIn.palette, houses, {row['id']: row['name'] for row in programs})
        program.save_home(gui.home_path, cached)
        self.assertGreater(gui.home_path.stat().st_size, 2 * program.MAX_MESSAGE)
        self.assertEqual(program.load_home(gui.home_path), cached)
        with self.helper, gui as self.view:
            try:
                self.assertTrue(last_page_requested.wait(4))
                first = wait_for(lambda: self.view.request('counters')['first'])
                self.assertEqual(first, dict(houses=200, lit=[lit], online=False, hint='Opening is back in a moment'))
                self.assertEqual(self.view.request('bridge-open', id=lit), program.UNAVAILABLE)
                self.view.click(*centre(houses_of(self.view.model())[lit]['box']))
                self.assertEqual(self.helper.opens, [])
            finally:
                release_last_page.set()
            scene = self.view.until(lambda scene: scene['online'])
            self.assertEqual([len(houses_of(scene)), [h['id'] for h in houses_of(scene).values() if h['running']]],
                             [200, [lit]])
            self.assertEqual(program.load_home(gui.home_path), cached)


@unittest.skipUnless(headless_available(), 'headless labwc, bwrap, wlr-randr, Mesa pins, GTK 4, Pango and Cairo')
class SurfaceTest(unittest.TestCase):
    def setUp(self):
        workspace = scratch()
        self.addCleanup(workspace.cleanup)
        self.root = Path(workspace.name)
        icon = self.root / 'icon.png'
        icon.write_bytes(png())
        self.helper = StandIn(self.root / 'shell.sock', icon=icon, count=45,
                             holes=['test-web-2'], unpinned=['test-tool-1'])
        self.chrome = Headless(self.root, self.helper.path)

    def test_reports_real_surface_focus_and_replays_it_after_hello(self):
        def reports():
            with self.helper.lock:
                return [request['focused'] for request in self.helper.requests if request['op'] == 'view_focus']

        with self.helper, self.chrome as gui, gui.virtual_click() as click:
            gui.until(lambda scene: scene['online'])
            self.assertIs(reports()[0], False)
            click()
            wait_for(lambda: reports()[-1] is True)
            gui.request('other-window')
            wait_for(lambda: reports()[-1] is False)
            gui.request('close-other-window')
            click()
            wait_for(lambda: reports()[-1] is True)

            self.helper.drop()
            gui.until(lambda scene: not scene['online'])
            before = len(self.helper.requests)
            self.helper.start()
            gui.until(lambda scene: scene['online'])
            hello, focus = self.helper.requests[before:before + 2]
            self.assertEqual((hello['op'], focus['op'], focus['focused']), ('hello', 'view_focus', True))

    def test_surface_token_pins_renderer_and_opening(self):
        self.helper.running = ['test-web-1']
        with self.helper, self.chrome as gui:
            scene = gui.until(lambda scene: scene['online'])
            parent = gui.parent()
            self.assertEqual(parent['before'], [False, False])
            self.assertEqual(parent['after'], [True, True])
            from laptop_home_headless import VENDORS
            self.assertEqual(parent['pins'], list(VENDORS.values()))
            self.assertEqual(parent['app_id'], 'aresos.laptop-home')
            self.assertEqual(gui.request('renderer'), 'GskCairoRenderer')
            self.assertEqual(drivers_mapped(parent['pid']), [])
            geometry = gui.request('window')
            self.assertTrue(geometry['visible'])
            if gui.expect_layer:
                self.assertEqual(parent.get('layer'),
                                 dict(background=True, on_demand=True, anchored=True, output='HEADLESS-1'))
            else:
                self.assertNotIn('layer', parent)
                self.assertTrue(geometry['fullscreen'])
            self.assertEqual(len(houses_of(scene)), 43)
            self.assertEqual([h['id'] for h in houses_of(scene).values() if h['running']], ['test-web-1'])
            self.assertEqual(gui.request('bridge-open', id='test-web-1'), {'state': 'starting'})
            self.helper.results['test-web-1'] = dict(ok=False, state='failed', error='unavailable',
                                                     message='not_installed')
            self.assertEqual(gui.request('bridge-open', id='test-web-1'),
                             {'state': 'failed', 'message': 'not_installed'})
            self.assertEqual(gui.request('bridge-open', id='Not An Id'), {'state': 'failed', 'message': 'No such app'})
            self.helper.drop()
            gui.until(lambda scene: not scene['online'])
            self.assertEqual(gui.request('bridge-open', id='test-web-1'), program.UNAVAILABLE)
            self.helper.revision = None
            self.helper.running = ['test-work-1']
            self.helper.start()
            scene = gui.until(lambda scene: scene['online'])
            self.assertEqual(len(houses_of(scene)), 43)
            self.assertEqual([h['id'] for h in houses_of(scene).values() if h['running']], ['test-work-1'])
            self.assertEqual(self.helper.opens, ['test-web-1', 'test-web-1'])

    def test_cached_town_comes_up_with_opening_disabled(self):
        cached = program.page_home(StandIn.palette, self.helper.houses,
                                   {row['id']: row['name'] for row in self.helper.programs})
        program.save_home(self.chrome.home_path, cached)
        with self.chrome as gui:
            first = wait_for(lambda: gui.request('counters')['first'])
            self.assertEqual(first, dict(houses=43, lit=[], online=False, hint='Opening is back in a moment'))
            self.assertEqual(gui.request('bridge-open', id='test-web-1'), program.UNAVAILABLE)
            self.assertEqual(self.helper.opens, [])


@unittest.skipUnless(os.environ.get('LAPTOP_HOME_MEMORY_GUARD'), 'opt-in: three fresh measured runs, about 90 s')
class MemoryGuardTest(unittest.TestCase):
    """53f's regression guard in set-up S: a median of at most 64,000 KiB PSS at rest after a redraw.

    The 60 MiB limit itself is judged in set-up I (the real compositor on the Intel chip, one window picture) at the
    laptop trial: the lead's call, 2026-11-19. Set-up S's headless pixman compositor keeps the shown picture until the
    next frame, so from the second frame on it counts two 8,100 KiB pictures; step B measured 62,358 KiB there
    (62,310-62,488) and 53,462 KiB with one picture. This guard pins today's two-picture number with about 1.6 MiB of
    room, so it catches a regression without failing on the test compositor's spare picture.
    """

    LIMIT_KIB = 64000

    def test_median_of_three_after_a_redraw(self):
        import statistics
        from laptop_home_memory import measure

        runs = [measure() for _ in range(3)]
        self.assertTrue(all(run['redrawn'] and run['renderer'] == 'GskCairoRenderer' for run in runs))
        median = statistics.median(run['Pss'] for run in runs)
        self.assertLessEqual(median, self.LIMIT_KIB, dict(runs=[run['Pss'] for run in runs],
                                                          largest=runs[0]['mappings']))
