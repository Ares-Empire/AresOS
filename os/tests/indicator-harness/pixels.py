"""Compare real screencopy pixels with the public Look A study."""
import sys

from PIL import Image, ImageChops

sys.path.insert(0, '/harness')
import look as study

LOOK = study.LookA('/usr/share/fonts/aresos/Jersey10-Regular.ttf')
ICONS = dict(speaker='speaker', sun='sun', microphone='microphone',
             **{'speaker-muted': 'speaker-muted', 'microphone-off': 'microphone-off'})
PALETTE = {colour[:3] for colour in study.P.values()}


def level(value, label='Volume', **kwargs):
    return dict(kind='level', what='speaker', label=label, level=value, **kwargs)


def message(what, label, status, tone='quiet', **kwargs):
    return dict(kind='message', what=what, label=label, status=status, tone=tone, **kwargs)


def reference(state, scale, look=LOOK):
    return study.up(study.indicator(look, state, ICONS), scale)


def mask_pixels(mask):
    return [(x, y) for y in range(mask.height) for x in range(mask.width) if mask.getpixel((x, y))]


class PositionedLook(study.LookA):
    """Use the study's glyph masks and recover integer pen shifts from the capture."""
    def __init__(self, capture, scale):
        self.__dict__.update(LOOK.__dict__)
        self.capture = capture
        self.scale = scale
        self.shifts = []

    def text(self, image, x, y, text, colour, shadow=True):
        s = self.scale
        placed, _ = self._layout(text)
        letters = (letter for letter in text if self.glyph_mask(letter) is not None)
        positions = []
        left = 0
        for letter, (mask, dx, dy) in zip(letters, placed, strict=True):
            top = y + self.cap + dy
            want = x + dx
            offsets = sorted(range(-8, 9), key=lambda shift: (abs(shift), shift))
            points = mask_pixels(mask)
            # Only integer-unit pen movement is allowed. The full-frame comparison below
            # then checks every pixel including the rest of each glyph and its shadow.
            matches = [want + shift for shift in offsets if want + shift >= left
                       and want + shift + mask.width <= image.width
                       and all(self.capture.getpixel(((want + shift + px) * s, (top + py) * s)) == colour[:3]
                               for px, py in points)]
            if not matches:
                raise AssertionError(f'{s}x {text!r}: {letter!r} at ({want}, {top}) differs from the study glyph')
            actual = matches[0]
            if actual != want:
                self.shifts.append(f'{text!r} {letter!r} at x={want}: {actual - want:+d} units')
            left = actual + 1
            positions.append((mask, actual, top))
        passes = ((1, study.P['outline']), (0, colour)) if shadow else ((0, colour),)
        for offset, ink in passes:
            for mask, gx, gy in positions:
                image.paste(ink, (gx + offset, gy + offset), mask)


def equal(capture, expected):
    assert capture.size == expected.size, f'capture size {capture.size}, study size {expected.size}'
    diff = ImageChops.difference(capture, expected.convert('RGB'))
    changed = ImageChops.multiply(diff.getchannel('R'), expected.getchannel('A'))
    for channel in 'GB':
        changed = ImageChops.lighter(changed, ImageChops.multiply(diff.getchannel(channel), expected.getchannel('A')))
    if box := changed.getbbox():
        count = sum(value for value in changed.histogram()[1:])
        raise AssertionError(f'{count} opaque pixels differ from the study, bounds {box}')


def exact(capture, state, scale, *, fit_message=False):
    positioned = PositionedLook(capture, scale)
    if fit_message:
        # The short plate's measured text width includes Pango's advances.
        assert state['kind'] == 'message' and capture.width % scale == 0
        width = capture.width // scale - (LOOK.pad * 2 + LOOK.icon_box + LOOK.gap + 1)
        assert abs(width - max(LOOK.text_width(state['label']), LOOK.text_width(state['status']))) <= 8
        positioned.text_width = lambda _text: width
    expected = reference(state, scale, positioned)
    equal(capture, expected)
    assert all(pixel in PALETTE for pixel, alpha in zip(capture.getdata(), expected.getchannel('A').getdata(),
                                                       strict=True) if alpha)
    return positioned.shifts


def fallback(capture, scale):
    state = level(62, label='')
    expected = reference(state, scale)
    # Only the label and its shadow may differ. The fallback face is taller than
    # Jersey 10, so inspect from the top of the plate to the start of the bar.
    box = (28 * scale, 0, 48 * scale, 18 * scale)
    paint = capture.crop(box)
    want = expected.crop(box).convert('RGB')
    differences = [actual for actual, base in zip(paint.getdata(), want.getdata(), strict=True) if actual != base]
    ink, shadow = (study.P[colour][:3] for colour in ('ink', 'outline'))
    assert ink in differences and set(differences) <= {ink, shadow}, 'fallback glyph has unexpected colours'
    clean = capture.copy()
    clean.paste(want, box)
    equal(clean, expected)
    return differences.count(ink)
