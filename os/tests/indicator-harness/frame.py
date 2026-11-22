"""Package 329's real inputs, protocol observations and pixel checks."""
from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
import re
import sys
import time
import traceback
from xml.etree import ElementTree as ET

from PIL import Image, ImageChops, ImageColor, ImageDraw

# Isolated mode removes the script directory from sys.path.
sys.path.insert(0, '/harness')
from driver import CONFIG, EV, LEFT, RIGHT, WLH, WORLD, Session, check_bus, run, settings, until

WIDTH, HEIGHT = 1920, 1080
BRANCH = Path('/harness/rc.xml')
BASELINE = Path('/harness/baseline/rc.xml')
PACK = Path('/usr/share/aresos/look')
ROLES = json.loads((PACK / 'look.json').read_text())['frame_colours']
THEME = Path('/usr/share/themes/AresOS/labwc')
LEFT_BUTTON, RIGHT_BUTTON, MIDDLE_BUTTON = 272, 273, 274
ESC, TAB, ALT, SHIFT, SUPER, F4 = 1, 15, 56, 42, 125, 62
UNBOUND_KEY = 30  # A, with no modifiers
THEME_ERROR = re.compile(
    r'^.*\[ERROR\] \[(?:[^\]\s]*/)?(?:theme\.c|(?:img|ssd|decorations)/[^/\]\s]+\.c):\d+\].*$',
    re.MULTILINE,
)
SHIPPED = ('menu', 'iconify', 'max', 'close')
ALL_BUTTONS = ('menu', 'shade', 'desk', 'iconify', 'max', 'close')
COLOURS = ('#725238', '#385869', '#4f673a', '#705776')
MENU_ROWS = ('Minimize', 'Maximize', 'Fullscreen', 'Roll Up/Down', 'Decorations',
             'Always on Top', 'Workspace', 'Close')


def rgb(value):
    return ImageColor.getrgb(value)


def role(group, field):
    return rgb(ROLES[group][field])


def colour_box(image, colour):
    diff = ImageChops.difference(image, Image.new('RGB', image.size, colour))
    red, green, blue = diff.split()
    return ImageChops.invert(ImageChops.lighter(ImageChops.lighter(red, green), blue)
                             .point([0] + [255] * 255)).getbbox()


def filled(image, box, colour):
    assert box[2] > box[0] and box[3] > box[1], box
    return image.crop(box).getcolors(1) == [((box[2] - box[0]) * (box[3] - box[1]), colour)]


def capture(name, image):
    image.save(EV / f'{name}.png')


class BarHeightError(AssertionError):
    """The brief reserves a different title-bar height for the lead."""


@dataclass
class Client:
    app_id: str
    colour: tuple
    proc: object
    log: Path

    def lines(self):
        return self.log.read_text().splitlines()


class FrameSession(Session):
    def __init__(self, number, label, source=BRANCH, *, toggles=False):
        super().__init__(number, width=WIDTH, height=HEIGHT)
        self.label = label
        self.log_path = EV / f'{number:02}-{label}-labwc.log'
        self.source = source
        self.bar, self.edge, self.cell = (36, 1, 44) if source == BASELINE else (40, 2, 48)
        self.buttons = ALL_BUTTONS if toggles else SHIPPED
        self.last_press = {}
        self.config = CONFIG / f'labwc-{label}'
        self.config.mkdir()
        if toggles:
            tree = ET.parse(source)
            tree.find('theme/titlebar/layout').text = 'menu:shade,desk,iconify,max,close'
            ET.SubElement(ET.SubElement(tree.getroot(), 'desktops'), 'number').text = '2'
            tree.write(self.config / 'rc.xml', encoding='utf-8')
        else:
            (self.config / 'rc.xml').write_bytes(source.read_bytes())

    def start(self):
        self.start_compositor(config=self.config, verbose=True)
        expected = 'Ares-Crown' if self.source == BASELINE else 'AresOS'
        assert f'read theme /usr/share/themes/{expected}/labwc/themerc' in self.log()
        self.observe_toplevels()
        for name in self.outputs:
            assert self.grab(name).size == (WIDTH, HEIGHT)
        return self

    def __exit__(self, *error):
        super().__exit__(*error)
        if error[0] is None:
            bad = THEME_ERROR.findall(self.log())
            assert not bad, bad

    def windows(self):
        self.observer.roundtrip()
        return {view.app_id: view for view in self.toplevels.toplevels.values() if view.ready}

    def focused(self):
        return sorted(view.app_id for view in self.windows().values() if view.activated)

    def expect_focus(self, client):
        until(lambda: self.focused() == [client.app_id], f'{client.app_id} focus')

    def open(self, name, *, title=None, size=(580, 260), colour=COLOURS[0], output=LEFT, lock=False):
        self.goto(output, WIDTH // 2, HEIGHT // 2)
        path = EV / f'{self.number:02}-{self.label}-{name}.log'
        argv = [WLH, 'window', '--app-id', name, '--title', title or name, '--size', f'{size[0]}x{size[1]}']
        if colour is not None:
            argv += ['--colour', colour]
        if lock:
            argv += ['--lock']
        proc = self.spawn(argv, env=self.env, log=path, stdin=lock)
        client = Client(name, rgb(colour) if colour else WORLD, proc, path)
        self.expect_focus(client)
        until(lambda: any(line.startswith('CONFIGURED ') for line in client.lines()), f'{name} configure')
        return client

    def gtk(self):
        self.goto(RIGHT, WIDTH // 2, HEIGHT // 2)
        self.spawn([sys.executable, '-IB', '/harness/frame_gtk.py'], env=self.env,
                   log=EV / '01-gtk.log')
        until(lambda: self.focused() == ['org.aresos.FrameHarness'], 'GTK 4 window focus')

    def button(self, code, down, *, double=False):
        if down:
            # Labwc uses a 500ms double-click interval even across different SSD buttons.
            remaining = self.last_press.get(code, 0) + 0.52 - time.monotonic()
            if remaining > 0 and not double:
                time.sleep(remaining)
            self.last_press[code] = time.monotonic()
        self.input(self.pointer, f'btn {code} {int(down)}')

    def click(self, point, code=LEFT_BUTTON, output=LEFT, *, double=False):
        self.goto(output, *point)
        self.button(code, True, double=double)
        self.button(code, False)

    def drag(self, start, end, *, code=LEFT_BUTTON, super_key=False, output=LEFT, preview=None):
        self.goto(output, *start)
        if super_key:
            self.key(SUPER, True)
        self.button(code, True)
        # Cross labwc's drag threshold before the final motion so it has a grab.
        x, y = start
        a, b = end
        self.goto(output, x + (a - x) // 4, y + (b - y) // 4)
        self.goto(output, a, b)
        if preview:
            until(lambda: preview(self.grab(output)), 'edge snapping overlay')
        self.button(code, False)
        if super_key:
            self.key(SUPER, False)

    def client_box(self, client, output=LEFT):
        return colour_box(self.grab(output), client.colour)

    def box(self, client, output=LEFT):
        return until(lambda: self.client_box(client, output), f'{client.app_id} on {output}')

    def place(self, client, x, y, output=LEFT):
        l, t, r, _ = self.box(client, output)
        self.drag(((l + r) // 2, t - self.bar // 2),
                  ((l + r) // 2 + x - l, t - self.bar // 2 + y - t), output=output)
        return until(lambda: (box := self.client_box(client, output)) and box[:2] == (x, y) and box,
                     f'{client.app_id} placed at {(x, y)} on {output}')

    def cell_box(self, client_box, button):
        l, y, r, _ = client_box
        index = self.buttons.index(button)
        x = l if not index else r - (len(self.buttons) - index) * self.cell
        return x, y - self.bar, x + self.cell, y

    def button_at(self, box, button):
        l, t, r, b = self.cell_box(box, button)
        return (l + r) // 2, (t + b) // 2

    def click_client(self, client):
        x, y, _, _ = self.box(client)
        self.click((x + 10, y + 10))
        self.expect_focus(client)

    def gone(self, client):
        assert client.proc.wait(timeout=4) == 0
        assert client.lines().count('CLOSE') == 1
        until(lambda: client.app_id not in self.windows(), f'{client.app_id} removed')
        assert not self.client_box(client)


@lru_cache(maxsize=36)
def sprite(filename, state):
    png = Image.open(THEME / filename).convert('RGBA')
    assert png.size == (48, 40)
    return Image.alpha_composite(Image.new('RGBA', png.size, role(state, 'bar') + (255,)), png).convert('RGB')


def pixels_for_button(app, image, box, button, state, compared, *, hover=False, toggled=False):
    filename = f'{button}{"_toggled" if toggled else ""}{"_hover" if hover else ""}-{state}.png'
    area = app.cell_box(box, button)
    actual = image.crop(area)
    expected = sprite(filename, state)
    diff = ImageChops.difference(actual, expected)
    if diff.getbbox():
        capture(f'debug-{app.number:02}-{filename[:-4]}', actual)
    assert not diff.getbbox(), (filename, area, diff.getbbox())
    compared[filename] = actual


def frame_geometry(image, box, colour, state, *, solid=True):
    l, t, r, b = box
    edge = role(state, 'border')
    run_height = 0
    while t - run_height > 0 and image.getpixel((l - 1, t - run_height - 1)) == edge:
        run_height += 1
    # The side edge extends up past the title to include the 2 px top edge.
    if run_height - 2 != 40:
        raise BarHeightError(f'{state}: measured {run_height - 2}px title bar at {box}')
    for area in ((l - 2, t - 42, r + 2, t - 40), (l - 2, t - 40, l, b),
                 (r, t - 40, r + 2, b), (l - 2, b, r + 2, b + 2)):
        assert filled(image, area, edge), (state, 'border', area)
    assert image.getpixel((l - 3, t + 10)) != edge
    assert image.getpixel((r + 2, t + 10)) != edge
    for area in ((l, t, r, t+1), (l, t, l+1, b)):
        assert filled(image, area, colour), (state, 'first client row or column', area)
    if solid:
        assert filled(image, box, colour), (state, 'client pixels or size', box)
    assert image.getpixel((l + 49, t - 39)) == role(state, 'bar')


def title_pixels(app, image, box, state):
    l, t, r, _ = box
    area = (l + 48, t - 40, r - 3 * 48, t)
    title = image.crop(area)
    colours = {colour: count for count, colour in title.getcolors(title.width * title.height)}
    text, background = role(state, 'title'), role(state, 'bar')
    assert colours[text] and colours[background], (state, colours)
    extra = sum(count for value, count in colours.items() if value not in (text, background))
    capture(f'01-title-{state}-4x', title.resize((title.width * 4, title.height * 4), Image.Resampling.NEAREST))
    app.check(True, f'{state} title 40px crop: {colours[text]} text pixels, {extra} intermediate pixels')


def check_frames(compared):
    with FrameSession(1, 'frame') as app:
        app.start()
        editor = app.open('editor', title='Editor ÄÖÜß with a deliberately long title that runs past the controls')
        app.place(editor, 140, 300)
        terminal = app.open('terminal', title='Terminal ÄÖÜß', size=(620, 300), colour=COLOURS[1])
        app.place(terminal, 1050, 380)
        app.gtk()
        app.click_client(terminal)
        app.goto(LEFT, 950, 900)
        image = app.grab(LEFT)
        capture('01-active-inactive', image)
        gtk = app.grab(RIGHT)
        capture('01-gtk4', gtk)
        gtk_colour = rgb('#d7d3c9')
        gtk_box = colour_box(gtk, gtk_colour)
        assert (gtk_box[2] - gtk_box[0], gtk_box[3] - gtk_box[1]) == (620, 300), gtk_box
        frame_geometry(gtk, gtk_box, gtk_colour, 'inactive', solid=False)
        app.check(True, 'GTK 4 also negotiated a 40px server bar and kept its 620x300 client area')
        for client, size, state in ((editor, (580, 260), 'inactive'), (terminal, (620, 300), 'active')):
            box = colour_box(image, client.colour)
            assert (box[2] - box[0], box[3] - box[1]) == size, (client.app_id, box)
            frame_geometry(image, box, client.colour, state)
            for button in SHIPPED:
                pixels_for_button(app, image, box, button, state, compared)
            title_pixels(app, image, box, state)
        app.check(True, 'two 40px bars, four buttons each at 1:1, exact 2px edges and complete client areas')
        app.click_client(editor)
        capture('01-long-title-active', app.grab(LEFT))
        frame_count = app.count

        app.number, app.count = 2, 0
        for client, state in ((terminal, 'inactive'), (editor, 'active')):
            box = app.box(client)
            for button in SHIPPED:
                app.goto(LEFT, *app.button_at(box, button))
                image = app.grab(LEFT)
                pixels_for_button(app, image, box, button, state, compared, hover=True)
                capture(f'02-{state}-{button}', image)
        close = app.button_at(app.box(editor), 'close')
        app.goto(LEFT, *close)
        app.button(LEFT_BUTTON, True)
        x, y, _, _ = app.box(editor)
        app.goto(LEFT, x + 30, y + 35)
        app.button(LEFT_BUTTON, False)
        assert editor.proc.poll() is None and 'CLOSE' not in editor.lines()
        assert app.box(editor)
        capture('02-slide-off', app.grab(LEFT))
        app.click(close)
        app.gone(editor)
        capture('02-closed', app.grab(LEFT))
        app.check(True, 'all eight hover cells, slide-off cancelled close, and click closed with exit 0')
        locked = app.open('locked-close', size=(650, 400), colour=COLOURS[2], lock=True)
        until(lambda: 'LOCKED' in locked.lines(), 'close test pointer lock')
        app.key(ALT, True)
        app.tap(F4)
        app.key(ALT, False)
        app.gone(locked)
        app.check(True, 'a floating --lock client also logged CLOSE and exited zero')
        return frame_count, app.count


def max_button(app, client):
    app.click(app.button_at(app.box(client), 'max'))


def check_toggles(compared):
    with FrameSession(3, 'maximized') as app:
        app.start()
        client = app.open('terminal', title='Terminal ÄÖÜß')
        old = app.box(client)
        for method in ('button', 'double-click'):
            if method == 'button':
                max_button(app, client)
            else:
                l, t, _, _ = old
                app.click((l + 110, t - 20))
                app.click((l + 110, t - 20), double=True)
            until(lambda: app.windows()[client.app_id].maximized, 'maximized')
            assert_box(app, client, lambda box: box == (0, 40, WIDTH, HEIGHT), 'maximized client below bar')
            app.goto(LEFT, 600, 480)
            shot = app.grab(LEFT)
            assert filled(shot, (900, 0, 1000, 40), role('active', 'bar'))
            assert not colour_box(shot.crop((300, 0, 1500, 40)), role('active', 'border'))
            capture(f'03-maximize-{method}', shot)
            max_button(app, client)
            until(lambda: not app.windows()[client.app_id].maximized and app.client_box(client) == old,
                  'restored client position and size')
        app.check(True, 'both maximize gestures put the borderless 40px bar at y=0 and restore the exact client rectangle')
        count = app.count

    with FrameSession(3, 'all-buttons', toggles=True) as app:
        app.start()
        client = app.open('editor', title='Editor ÄÖÜß', size=(560, 270))
        old = app.place(client, 170, 310)
        other = app.open('terminal', output=RIGHT, colour=COLOURS[1])
        app.click_client(client)
        for button in ('shade', 'desk', 'max'):
            box = old
            for toggled in (False, True):
                if toggled:
                    app.click(app.button_at(old, button))
                    if button == 'max':
                        box = assert_box(app, client, lambda box: box == (0, 40, WIDTH, HEIGHT), 'toggled maximize')
                        assert app.windows()[client.app_id].maximized
                    if button == 'shade':
                        until(lambda: not app.client_box(client), 'rolled-up client')
                    if button == 'desk':
                        assert app.box(client) == old
                        app.goto(RIGHT, 1800, 950)
                        app.input(app.pointer, 'axis 1')
                        until(lambda: not app.client_box(other, RIGHT), 'other window left on the first workspace')
                        assert app.client_box(client) == old
                        app.input(app.pointer, 'axis -1')
                        app.box(other, RIGHT)
                        app.click_client(client)
                for state in ('active', 'inactive'):
                    if state == 'inactive':
                        x, y, _, _ = app.box(other, RIGHT)
                        app.click((x + 10, y + 10), output=RIGHT)
                        app.expect_focus(other)
                    app.goto(LEFT, 950, 10)
                    shot = app.grab(LEFT)
                    pixels_for_button(app, shot, box, button, state, compared, toggled=toggled)
                    app.goto(LEFT, *app.button_at(box, button))
                    hover = app.grab(LEFT)
                    pixels_for_button(app, hover, box, button, state, compared, hover=True, toggled=toggled)
                    capture(f'03-{button}-{state}-{"on" if toggled else "off"}', hover)
                app.click((box[0] + 110, box[1] - 15))
                app.expect_focus(client)
            app.click(app.button_at(box, button))
            until(lambda: app.client_box(client) == old, f'{button} restored rectangle')
            if button == 'desk':
                # Root scroll changes workspaces. The client must disappear with the toggle off.
                app.goto(RIGHT, 1800, 950)
                app.input(app.pointer, 'axis 1')
                until(lambda: not app.client_box(client), 'second workspace without the unpinned client')
                app.input(app.pointer, 'axis -1')
                assert_box(app, client, lambda rect: rect == old, 'client back on the first workspace')
                app.click_client(client)
        assert set(compared) == {path.name for path in THEME.glob('*.png')}, sorted(compared)
        (EV / '01-03-pngs.txt').write_text(''.join(f'PASS 48x40 1:1 {name}\n' for name in sorted(compared)))
        app.count = count
        app.check(True, f'{len(compared)}/36 normal, hover and toggled theme PNGs at 1:1 across two workspaces')
        return app.count


def menu(app, point, button, output=LEFT):
    app.goto(output, 1700, 950)
    before = app.grab(output)
    app.click(point, button, output)
    app.goto(output, 1700, 950)
    def shown():
        shot = app.grab(output)
        box = ImageChops.difference(shot, before).getbbox()
        return (shot, box) if box else None
    return before, *until(shown, 'built-in menu')


def menu_pixels(image, box, rows):
    l, t, r, b = box
    bg, border = role('menu', 'bg'), role('menu', 'border')
    assert 200 <= r - l <= 400 and b - t == 4 + len(rows) * 40, (rows, box)
    for area in ((l, t, r, t+2), (l, b-2, r, b), (l, t, l+2, b), (r-2, t, r, b)):
        assert filled(image, area, border), (rows, area)
    measurements = {}
    for index, label in enumerate(rows):
        y = t + 2 + index * 40
        assert filled(image, (r-8, y, r-2, y+40), bg), label
        row = image.crop((l+2, y, r-2, y+40))
        ink = colour_box(row, role('menu', 'text'))
        assert ink and ink[0] >= 8 and ink[2] <= row.width - 8 and 0 < ink[1] < ink[3] < 40, (label, ink)
        measurements[label] = ink
    return measurements


def check_menus():
    with FrameSession(4, 'menus') as app:
        app.start()
        client = app.open('editor', title='Editor ÄÖÜß')
        box = app.box(client)
        data = {}
        for method, point, button in (
            ('gold', app.button_at(box, 'menu'), LEFT_BUTTON),
            ('title', (box[0] + 110, box[1] - 20), RIGHT_BUTTON),
        ):
            before, image, rect = menu(app, point, button)
            capture(f'04-{method}-menu', image)
            data[method] = {'rect': rect, 'rows': menu_pixels(image, rect, MENU_ROWS)}
            l, t, r, _ = rect
            y = t + 2 + MENU_ROWS.index('Always on Top') * 40
            app.goto(LEFT, r - 12, y + 20)
            hover = app.grab(LEFT)
            capture(f'04-{method}-hover', hover)
            assert filled(hover, (r-8, y, r-2, y+40), role('menu', 'chosen_bg'))
            ink = colour_box(hover.crop((l+2, y, r-2, y+40)), role('menu', 'chosen_text'))
            assert ink == data[method]['rows']['Always on Top'], ink
            app.tap(ESC)
            app.goto(LEFT, 1700, 950)
            until(lambda: not ImageChops.difference(app.grab(LEFT), before).getbbox(), 'menu dismissed')
            app.expect_focus(client)
            app.check(True, f'{method} window menu has 8 complete 40px rows, 2px border, hover colours and Escape focus')
        app.goto(RIGHT, 600, 220)
        bare = app.grab(RIGHT)
        assert bare.getcolors(1), 'the second output must be empty'
        data['root'] = {}
        for name, code in (('Left', LEFT_BUTTON), ('Right', RIGHT_BUTTON), ('Middle', MIDDLE_BUTTON)):
            for down in (True, False):
                app.button(code, down)
                assert not ImageChops.difference(app.grab(RIGHT), bare).getbbox(), (name, down)
            app.expect_focus(client)
            data['root'][name] = {'menu_on_press': False, 'menu_on_release': False}
            app.check(True, f'{name} click on empty output leaves the root menu closed')
        capture('04-root-menu', app.grab(RIGHT))
        (EV / '04-menu-rows.json').write_text(json.dumps(data, indent=2) + '\n')
        return app.count


def assert_box(app, client, predicate, name):
    return until(lambda: (box := app.client_box(client)) and predicate(box) and box, name)


def roll_up(app, client):
    box = app.box(client)
    _, _, rect = menu(app, (box[0] + 110, box[1] - app.bar // 2), RIGHT_BUTTON)
    l, t, r, b = rect
    line = (b - t - 2 * app.edge) // len(MENU_ROWS)
    app.goto(LEFT, (l + r) // 2, t + app.edge + 3 * line + line // 2)
    app.button(LEFT_BUTTON, True)
    app.button(LEFT_BUTTON, False)
    until(lambda: not app.client_box(client), 'window menu Roll Up/Down')


def state_record(app, client, direction, when, branch):
    image = app.grab(LEFT)
    box = colour_box(image, client.colour)
    if branch:
        capture(f'05-scroll-{direction}-{when}', image)
    return image, {'focus': app.focused(), 'client': box, 'shaded': box is None, 'visible_bounds': image.getbbox(),
                   'configure': [line for line in client.lines() if line.startswith('CONFIGURED ')][-1]}


def binding_run(source):
    branch = source == BRANCH
    label = 'branch' if branch else 'baseline'
    data = {}
    with FrameSession(5, label, source) as app:
        app.start()
        other = app.open('other', output=RIGHT, colour=COLOURS[1])
        client = app.open('editor', title='Editor ÄÖÜß')
        original = app.box(client)
        l, t, r, b = original
        point = (l + 110, t - app.bar // 2)
        # Labwc 0.9.6 maps negative virtual wheel deltas to Up (shade) and positive to Down (unshade).
        for direction, delta, shaded in (('down-unshaded', 1, False), ('up-unshaded', -1, False),
                                         ('up-shaded', -1, True), ('down-shaded', 1, True)):
            if shaded:
                if branch and direction == 'up-shaded':
                    roll_up(app, client)
                if app.focused() != [other.app_id]:
                    x, y, _, _ = app.box(other, RIGHT)
                    app.click((x+10, y+10), output=RIGHT)
                    app.expect_focus(other)
            app.goto(LEFT, *point)
            before, state = state_record(app, client, direction, 'before', branch)
            assert state['shaded'] == shaded, state
            assert state['focus'] == [other.app_id if shaded else client.app_id], state
            app.input(app.pointer, f'axis {delta}')
            if not branch:
                if direction == 'up-unshaded':
                    until(lambda: not app.client_box(client) and client.app_id not in app.focused(), 'baseline shaded/unfocused')
                elif direction == 'down-shaded':
                    assert_box(app, client, lambda box: box == original, 'baseline unshaded original rectangle')
                    app.expect_focus(client)
                elif direction == 'up-shaded':
                    until(lambda: not app.focused(), 'baseline unfocused the other window')
            after, updated = state_record(app, client, direction, 'after', branch)
            same = not ImageChops.difference(before, after).getbbox()
            if branch:
                assert same and state == updated, (direction, state, updated)
            else:
                assert same == (direction in ('down-unshaded', 'up-shaded')), (direction, state, updated)
            data[f'scroll {direction} ({delta:+})'] = dict(before=state, after=updated, same_pixels=same)
        if branch:
            roll_point = (original[0] + 110, original[1] - app.bar // 2)
            app.click(roll_point)
            app.expect_focus(client)
            _, _, rect = menu(app, roll_point, RIGHT_BUTTON)
            l, t, r, b = rect
            app.goto(LEFT, (l+r)//2, t + 2 + 3*40 + 20)
            app.button(LEFT_BUTTON, True)
            app.button(LEFT_BUTTON, False)
            assert_box(app, client, lambda box: box == original, 'unshade for remaining bindings')
        app.click_client(client)

        def note(name, before, after, result):
            data[name] = dict(before=before, after=after, result=result)
            if name in ('title drag', 'Super+left move', 'border resize', 'Super+right resize'):
                data[name]['delta'] = [end-start for start, end in zip(before, after, strict=True)]
            if branch and name in ('left snap', 'right snap', 'border resize', 'middle maximize'):
                capture('05-' + name.replace(' ', '-'), app.grab(LEFT))

        def title(box):
            return box[0] + 110, box[1] - app.bar // 2

        def move(name, super_key=False):
            old = app.box(client)
            x, y = (old[0] + 150, old[1] + 110) if super_key else title(old)
            app.drag((x, y), (x + 160, y + 90), super_key=super_key)
            new = assert_box(app, client, lambda box: box[0] > old[0] and box[1] > old[1], name)
            assert (new[2]-new[0], new[3]-new[1]) == (old[2]-old[0], old[3]-old[1]), new
            note(name, old, new, 'moved with unchanged size')

        move('title drag')
        for name, edge in (('top-edge maximize', (900, 0)), ('left snap', (0, 500)), ('right snap', (WIDTH-1, 500))):
            old = app.box(client)
            def snap_preview(image):
                # The preview has a 2px black/gold/black outline and #cfa24f40 tint.
                x = 1100 if name == 'right snap' else 100
                stripes = [image.getpixel((x, y)) for y in range(6)]
                if stripes != [rgb(c) for c in ROLES['snap']['lines'] for _ in range(2)]:
                    return False
                capture('05-preview-' + name.replace(' ', '-'), image)
                red, green, blue, alpha = rgb(ROLES['snap']['fill'])
                # Pixman quantizes a premultiplied 16-bit colour to its high byte.
                tint = tuple((channel * alpha * 257 // 255) >> 8 for channel in (red, green, blue))
                assert image.getpixel((x, 200)) == tint, (name, image.getpixel((x, 200)), tint)
                return True
            app.drag(title(old), edge, preview=snap_preview if branch and name.endswith('snap') else None)
            if branch and name == 'top-edge maximize':
                assert_box(app, client, lambda box: box == (0, app.bar, WIDTH, HEIGHT), name)
                capture('05-top-edge-maximize', app.grab(LEFT))
            if name == 'top-edge maximize':
                new = assert_box(app, client, lambda box: box == (0, app.bar, WIDTH, HEIGHT), name)
                assert app.windows()[client.app_id].maximized
                max_button(app, client)
                assert_box(app, client, lambda box: box == old, 'restore after top-edge maximize')
            else:
                left = 0 if name == 'left snap' else WIDTH // 2
                new = assert_box(app, client, lambda box: box == (left + app.edge, app.bar + app.edge,
                                                                  left + WIDTH//2 - app.edge, HEIGHT - app.edge),
                                 name)
                assert not app.windows()[client.app_id].maximized
            note(name, old, new, name)
        # Drag out of the right snap before checking floating resize grasps.
        app.drag(title(new), (780, 320))
        box = assert_box(app, client, lambda rect: rect[0] < 1000 and rect[1] > 100, 'floating after drag from snap')
        for name, start, code, super_key in (
            ('border resize', (box[2], box[3]), LEFT_BUTTON, False),
            ('Super+right resize', None, RIGHT_BUTTON, True),
        ):
            old = app.box(client)
            x, y = start or (old[2] - 40, old[3] - 40)
            app.drag((x, y), (x + 130, y + 75), code=code, super_key=super_key)
            new = assert_box(app, client, lambda rect: rect[:2] == old[:2] and rect[2] > old[2] and rect[3] > old[3], name)
            note(name, old, new, 'bottom-right grew with stable top-left')
        move('Super+left move')
        old = app.box(client)
        app.click(app.button_at(old, 'max'), MIDDLE_BUTTON)
        new = assert_box(app, client, lambda box: box[0] == old[0] and box[2] == old[2] and
                         box[1] == app.bar + app.edge and box[3] == HEIGHT - app.edge, 'middle-click vertical maximize')
        note('middle maximize', old, new, 'vertical maximize only')
        app.click(app.button_at(new, 'max'), MIDDLE_BUTTON)
        old = assert_box(app, client, lambda box: box == old, 'restore after vertical maximize')
        app.click(app.button_at(old, 'iconify'))
        until(lambda: app.windows()[client.app_id].minimized and not app.client_box(client), 'minimized')
        note('minimize', old, None, 'hidden and minimized')
        app.key(ALT, True)
        app.tap(TAB)
        app.key(ALT, False)
        app.expect_focus(client)
        box = app.box(client)
        app.key(ALT, True)
        app.tap(F4)
        app.key(ALT, False)
        app.gone(client)
        note('Alt+F4', box, None, 'close event and exit 0')
    return data


def check_bindings():
    baseline = binding_run(BASELINE)
    branch = binding_run(BRANCH)
    for name, row in baseline.items():
        if 'result' in row:
            assert row['result'] == branch[name]['result'], name
            assert row.get('delta') == branch[name].get('delta'), (name, row, branch[name])
    (EV / '05-bindings.json').write_text(json.dumps({
        'merge_base': Path('/harness/merge-base.txt').read_text().strip(),
        'baseline': baseline, 'branch': branch,
    }, indent=2) + '\n')
    return len(branch)


def alt_tab(app, *, held=False, reverse=False):
    app.key(ALT, True)
    if reverse:
        app.key(SHIFT, True)
    app.tap(TAB)
    if reverse:
        app.key(SHIFT, False)
    if not held:
        app.key(ALT, False)


def cancel(app):
    app.tap(ESC)
    app.key(ALT, False)


def lock_events(lines):
    return [line for line in lines if line in ('LOCKED', 'UNLOCKED', 'LEAVE', 'KBD_ENTER', 'KBD_LEAVE')
            or line.startswith(('REL ', 'MOTION '))]


def motion_sample(app, world):
    start = len(world.lines())
    app.input(app.pointer, 'rel 10 5')
    until(lambda: 'REL 10.00 5.00' in world.lines()[start:], 'relative delta received by world')
    # The client may log the same event's absolute motion just past the relative delta.
    time.sleep(0.04)
    return lock_events(world.lines()[start:])


def keyboard_sample(app, world):
    start = len(world.lines())
    app.tap(UNBOUND_KEY)
    # The later pointer event confirms the world has processed events queued before it.
    motion = motion_sample(app, world)
    keys = [line for line in world.lines()[start:] if line.startswith(f'KEY {UNBOUND_KEY} ')]
    return {'key_events': keys, 'motion_events': motion}


def panel_metrics(image, count):
    l = (WIDTH - count * 280) // 2
    top = (HEIGHT - 208) // 2
    box = colour_box(image.crop((l, top, l+count*280, top+208)), role('switcher', 'chosen_border'))
    assert box, 'no gold selection frame'
    x, y, r, b = selected = (box[0]+l, box[1]+top, box[2]+l, box[3]+top)
    assert (r-x, b-y) == (280, 208), selected
    assert y == top and (x-l) % 280 == 0 and 0 <= (x-l)//280 < count, selected
    edge = role('switcher', 'chosen_border')
    for box in ((x, y, r, y+4), (x, b-4, r, b), (x, y, x+4, b), (r-4, y, r, b)):
        assert filled(image, box, edge), box
    assert image.getpixel((x+4, y+4)) == role('switcher', 'chosen_bg')
    assert filled(image, (l-10, top-10, l+count*280+10, top-8), role('switcher', 'border'))
    assert filled(image, (l, top-8, l+count*280, top), role('switcher', 'bg'))
    tile = image.crop(selected)
    label = colour_box(tile.crop((8, 144, 272, 200)), role('switcher', 'text'))
    assert label, 'no label in tile'
    return selected, tile, label


def switch_run(source):
    branch = source == BRANCH
    data = {}
    with FrameSession(6, 'branch-switch' if branch else 'baseline-switch', source) as app:
        app.start()
        minimized = app.open('minimized', title='Minimized ÄÖÜß', colour=COLOURS[3], size=(520, 230))
        app.place(minimized, 1250, 670)
        app.click(app.button_at(app.box(minimized), 'iconify'))
        until(lambda: app.windows()[minimized.app_id].minimized, 'initial minimized state')
        remote = app.open('on-right', output=RIGHT, title='Right output', colour=COLOURS[2])
        spare = app.open('spare', output=RIGHT, title='Spare window', colour='#59715e')
        app.place(spare, 1300, 650, output=RIGHT)
        overlap = app.open('overlap', title='Above Home', colour=COLOURS[0])
        placed = app.place(overlap, 140, 260)
        world = app.open('aresos-desktop', title='Home', size=(720, 500), lock=True, colour=None)
        state = app.windows()[world.app_id]
        assert state.maximized and not state.fullscreen
        until(lambda: 'LOCKED' in world.lines(), 'world pointer locked')
        configures = [line for line in world.lines() if line.startswith('CONFIGURED ')]
        assert any(line.startswith('CONFIGURED 1920 1080 states=') and 'maximized' in line
                   and 'fullscreen' not in line for line in configures), configures
        original = app.grab(LEFT)
        assert filled(original, placed, overlap.colour), 'a focused world covered the overlapping app'
        # Everything away from the overlap and its shadow is the borderless world, including all four edges.
        for box in ((0, 0, WIDTH, 1), (0, HEIGHT-1, WIDTH, HEIGHT), (0, 0, 1, HEIGHT),
                    (WIDTH-1, 0, WIDTH, HEIGHT), (1050, 20, WIDTH, HEIGHT)):
            assert filled(original, box, WORLD), box
        data['world_configures'] = configures
        if branch:
            capture('06-world-below-app', original)
        data['before'] = keyboard_sample(app, world)
        assert data['before'] == {'key_events': [f'KEY {UNBOUND_KEY} 1', f'KEY {UNBOUND_KEY} 0'],
                                  'motion_events': ['REL 10.00 5.00']}, data
        mark = len(world.lines())
        right_before = app.grab(RIGHT)
        alt_tab(app, held=True)
        if branch:
            shot = app.grab(LEFT)
            capture('06-panel-focused-left', shot)
            capture('06-other-output', app.grab(RIGHT))
            selected, _, label = panel_metrics(shot, 5)
            assert not ImageChops.difference(right_before, app.grab(RIGHT)).getbbox()
            x, y, r, _ = placed
            # The preview outline is three 2px bands around the selected floating app.
            colours = [shot.getpixel(((x+r)//2, y-app.bar-app.edge+i)) for i in range(6)]
            assert colours == [rgb(c) for c in ROLES['switcher']['outline'] for _ in range(2)], colours
            data['panel'] = {'selected': selected, 'label_ink': label, 'outline_top': colours}
        cancel(app)
        app.expect_focus(world)
        if branch:
            assert not ImageChops.difference(original, app.grab(LEFT)).getbbox()
        data['cancel_events'] = lock_events(world.lines()[mark:])
        data['after_cancel'] = keyboard_sample(app, world)

        mark = len(world.lines())
        alt_tab(app)
        app.expect_focus(overlap)
        until(lambda: 'UNLOCKED' in world.lines()[mark:], 'world unlock after focus moves away')
        data['away_events'] = lock_events(world.lines()[mark:])
        data['while_away'] = motion_sample(app, world)
        mark = len(world.lines())
        alt_tab(app)
        app.expect_focus(world)
        until(lambda: 'LOCKED' in world.lines()[mark:], 'world relock on returned focus')
        data['back_events'] = lock_events(world.lines()[mark:])
        data['after_back'] = keyboard_sample(app, world)
        assert data['after_back'] == data['before'], data

        if branch:
            alt_tab(app, held=True, reverse=True)
            shot = app.grab(LEFT)
            rect, tile, label = panel_metrics(shot, 5)
            # The previous MRU entry wraps to the initially minimized window. Its colour identifies the thumbnail.
            thumb = colour_box(tile.crop((8, 8, 272, 144)), minimized.colour)
            capture('06-minimized-tile', shot)
            assert thumb, 'minimized tile is missing its client thumbnail'
            assert app.windows()[minimized.app_id].minimized
            app.key(ALT, False)
            app.expect_focus(minimized)
            assert not app.windows()[minimized.app_id].minimized and app.box(minimized)
            data['minimized_tile'] = {'box': rect, 'thumbnail_client_colour_box': thumb, 'label_ink': label}
            capture('06-minimized-restored', app.grab(LEFT))

            # Keep focus on the right while the pointer is on the left, then select a tile by click.
            bx = app.box(remote, RIGHT)
            app.click((bx[0]+15, bx[1]+15), output=RIGHT)
            mark = len(world.lines())
            app.goto(LEFT, 1600, 220)
            until(lambda: any(line in ('ENTER 1600.0 220.0', 'MOTION 1600.0 220.0')
                              for line in world.lines()[mark:]), 'pointer on left output')
            app.expect_focus(remote)
            l = (WIDTH - 5 * 280) // 2
            top = (HEIGHT - 208) // 2
            panel_band = (l, top-8, l+5*280, top)
            left_before = app.grab(LEFT).crop(panel_band)
            alt_tab(app, held=True)
            shot = app.grab(RIGHT)
            panel_metrics(shot, 5)
            assert not ImageChops.difference(left_before, app.grab(LEFT).crop(panel_band)).getbbox(), (
                'switcher panel changed the output under the pointer')
            capture('06-panel-focused-right', shot)
            tiles = [shot.crop((l+i*280, 436, l+(i+1)*280, 580)) for i in range(5)]
            index, = [i for i, tile in enumerate(tiles) if colour_box(tile, overlap.colour)]
            app.click((l+index*280+140, 520), output=RIGHT)
            app.expect_focus(overlap)
            app.key(ALT, False)
            data['panel_click'] = {'pointer_output_at_open': LEFT, 'focused_output_at_open': RIGHT,
                                   'panel_on_pointer_output': False, 'tile': index,
                                   'focus_before_releasing_alt': app.focused()}
    return data


def check_switcher():
    baseline = switch_run(BASELINE)
    branch = switch_run(BRANCH)
    (EV / '06-switcher.json').write_text(json.dumps({
        'merge_base': Path('/harness/merge-base.txt').read_text().strip(),
        'baseline': baseline, 'branch': branch,
    }, indent=2) + '\n')
    for key in ('before', 'cancel_events', 'after_cancel', 'away_events', 'while_away', 'back_events', 'after_back'):
        assert baseline[key] == branch[key], (key, baseline[key], branch[key])
    return 8


def check_look():
    reference = None
    for value in ('A', 'B', 'C'):
        settings(look=value)
        with FrameSession(7, f'look-{value}') as app:
            app.start()
            actual = json.loads(run('/usr/libexec/aresos-settings', 'get', env=app.env).stdout)
            assert actual['look'] == value
            client = app.open('editor', title='Editor ÄÖÜß')
            app.goto(LEFT, 1700, 950)
            box = app.box(client)
            image = app.grab(LEFT)
            frame_geometry(image, box, client.colour, 'active')
            capture(f'07-look-{value}', image)
            if reference is None:
                reference = image
            assert not ImageChops.difference(reference, image).getbbox(), value
    return 3


SHEETS = {
    1: ('A-10', ('01-active-inactive', '01-gtk4', '01-title-active-4x', '01-title-inactive-4x')),
    2: ('A-09', ('02-active-close', '02-inactive-close', '02-slide-off', '02-closed')),
    3: ('A-11', ('03-maximize-button', '03-shade-active-on', '03-desk-inactive-on', '03-max-active-on')),
    4: ('A-11', ('04-gold-hover', '04-title-menu', '04-root-menu')),
    5: ('A-11', ('05-scroll-up-unshaded-after', '05-scroll-down-shaded-after',
                 '05-preview-left-snap', '05-right-snap')),
    6: ('A-14', ('06-panel-focused-left', '06-minimized-tile', '06-panel-focused-right', '06-world-below-app')),
    7: ('A-10', ('07-look-A', '07-look-B', '07-look-C')),
    8: ('A-09', ('08-sprites',)),
}


def make_sheet(number, reference, shots):
    entries = [(f'Look A study {reference}', next(Path('/harness').glob(f'{reference}-*.png')))]
    entries += [(name, EV / f'{name}.png') for name in shots]
    panels = []
    for label, path in entries:
        with Image.open(path) as opened:
            panel = opened.convert('RGB')
        if panel.size == (WIDTH, HEIGHT) and (ink := panel.getbbox()):
            panel = panel.crop(ink)
        # Full-size source captures sit beside these previews in evidence/.
        panel.thumbnail((940, 490), Image.Resampling.NEAREST)
        panels.append((label, panel))
    margin, row_header = 16, 26
    sheet = Image.new('RGB', (2 * (940 + margin) + margin,
                              ((len(panels) + 1) // 2) * (490 + row_header) + margin), '#1a181f')
    draw = ImageDraw.Draw(sheet)
    for index, (label, panel) in enumerate(panels):
        x = margin + index % 2 * (940 + margin)
        y = margin + index // 2 * (490 + row_header)
        draw.text((x, y), label, fill='#f3f1ea', font_size=15)
        sheet.paste(panel, (x, y + row_header))
    capture(f'sheet-{number:02}', sheet)


def check_sheets(compared):
    names = sorted(compared)
    assert len(names) == 36
    atlas = Image.new('RGB', (6 * 136, 6 * 70), '#1a181f')
    draw = ImageDraw.Draw(atlas)
    for i, filename in enumerate(names):
        x, y = i % 6 * 136, i // 6 * 70
        atlas.paste(compared[filename], (x + 44, y + 4))
        draw.text((x + 6, y + 49), filename.removesuffix('.png'), fill='#f3f1ea', font_size=10)
    capture('08-sprites', atlas)
    for number, (reference, shots) in SHEETS.items():
        make_sheet(number, reference, shots)
    return len(SHEETS)


def main():
    check_bus()
    compared = {}
    failed = False
    for number, check in ((1, lambda: check_frames(compared)), (3, lambda: check_toggles(compared)),
                          (4, check_menus), (5, check_bindings), (6, check_switcher), (7, check_look)):
        try:
            count = check()
        except BarHeightError as error:
            print(f'STOP {number} {error}', flush=True)
            return 2
        except Exception:
            print(f'FAIL group {number}\n{traceback.format_exc()}', flush=True)
            failed = True
        else:
            if number == 1:
                print(f'PASS group 1: {count[0]} checks\nPASS group 2: {count[1]} checks', flush=True)
            else:
                print(f'PASS group {number}: {count} checks', flush=True)
    if not failed:
        print(f'PASS group 8: {check_sheets(compared)} review sheets', flush=True)
    return int(failed)


if __name__ == '__main__':
    with (EV / 'results.txt').open('w') as results:
        sys.stdout = results
        sys.exit(main())
