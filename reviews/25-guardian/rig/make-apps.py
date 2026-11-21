#!/usr/bin/python3
# DEVELOPMENT AID of package 25 (the real-game check; copied from package 49b's rig): writes the rig's town of test apps, none of them a real program.
"""usage: make-apps.py <folder>

Writes <folder>/applications/pkg41.*.desktop (40 entries), <folder>/icons/*.png (a generated 128 x 128 picture each),
<folder>/bin/pkg41-app (the program every entry starts: a foot window with the entry's app ID) and an empty
<folder>/registry/. The mix follows the laptop's own proportions (HUB.md 5: 9 Internet, 5 Games, 5 Work & Media,
42 System & Tools of 61) scaled to 40: 6 Internet, 3 Games, 3 Work & Media, 28 System & Tools. System & Tools then
fills rows 0 to 4 of the south road, so its farthest logos stand about 100 blocks from home (the brief's town)."""
import colorsys, os, struct, sys, zlib

GROUPS = [('Web', 'Network;', 6), ('Game', 'Game;', 3), ('Media', 'Graphics;', 3), ('Tool', 'Utility;', 28)]


def png(path, rgb_back, rgb_front, shape):
    side = 128
    rows = []
    for y in range(side):
        row = bytearray([0])
        for x in range(side):
            dx, dy = x - 63.5, y - 63.5
            inside = {0: dx * dx + dy * dy < 40 ** 2, 1: abs(dx) + abs(dy) < 48, 2: abs(dx) < 36 and abs(dy) < 36,
                      3: (int(y) // 16) % 2 == 0 and abs(dx) < 48 and abs(dy) < 48}[shape]
            row += bytes(rgb_front if inside else rgb_back) + b'\xff'
        rows.append(bytes(row))
    raw = zlib.compress(b''.join(rows), 9)

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    with open(path, 'wb') as out:
        out.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', side, side, 8, 6, 0, 0, 0))
                  + chunk(b'IDAT', raw) + chunk(b'IEND', b''))


def main(folder):
    folder = os.path.abspath(folder)
    for sub in ('applications', 'icons', 'bin', 'registry'):
        os.makedirs(os.path.join(folder, sub), exist_ok=True)
    program = os.path.join(folder, 'bin', 'pkg41-app')
    with open(program, 'w') as out:
        out.write('#!/usr/bin/bash\n# DEVELOPMENT AID of package 49b (copied from package 41): every test app is this foot window.\n'
                  'exec /usr/bin/foot --app-id="pkg41.$1" --title="Test app $1" -e /usr/bin/sleep 900\n')
    os.chmod(program, 0o755)
    n = 0
    for word, categories, count in GROUPS:
        for i in range(1, count + 1):
            n += 1
            app = f'{word.lower()}{i:02d}'
            hue = (n * 0.618034) % 1.0
            back = tuple(int(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.75, 0.9))
            front = tuple(int(c * 255) for c in colorsys.hsv_to_rgb((hue + 0.5) % 1.0, 0.3, 0.98))
            icon = os.path.join(folder, 'icons', f'pkg41-{app}.png')
            png(icon, back, front, n % 4)
            with open(os.path.join(folder, 'applications', f'pkg41.{app}.desktop'), 'w') as out:
                out.write(f'[Desktop Entry]\nType=Application\nName=Test {word} {i}\nExec={program} {app}\n'
                          f'Icon={icon}\nCategories={categories}\nTerminal=false\nStartupWMClass=pkg41.{app}\n')
    print(f'{n} test apps in {folder}')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
