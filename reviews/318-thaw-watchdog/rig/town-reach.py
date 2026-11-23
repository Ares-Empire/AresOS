#!/usr/bin/python3
# DEVELOPMENT AID of package 318 (copied from packages 49b and 41) (measurement only): which render distance the town needs, from its own rules.
"""usage: town-reach.py

For a town whose groups use rows 0..R (HUB.md 3.1 and 3.2: a logo fills outward a0..a0+2 with a0 = 20 + 14 r, and
sideways 4 + 14 k + u for u 0..11 on either side of the road), prints the farthest logo corner from home and the
least render distance at which every chunk holding a logo block is drawn from home. Then, filling a group's places
in HUB.md 3.3's order (by row, then by k, then L before R), the most apps a group can hold at each render distance
with every logo drawn from home, per road. The game's rule
(ChunkTrackingView.isWithinDistance in 26.2, without the outer ring): a chunk dx, dz chunks from the player's is in
view when max(0, |dx| - 1)^2 + max(0, |dz| - 1)^2 < distance^2. The fog (FogRenderer) then fades the terrain from
16 d - clamp(1.6 d, 4, 64) to 16 d blocks."""
import math

GROUPS = {'north': ((0, -1), (1, 0)), 'east': ((1, 0), (0, 1)), 'south': ((0, 1), (-1, 0)), 'west': ((-1, 0), (0, -1))}


def place_chunks(group, r, k, side):
    """The chunks holding the logo of one place (side 1 = R, -1 = L): outward a0..a0+2, sideways 4 + 14 k + u."""
    (ox, oz), (rx, rz) = GROUPS[group]
    a0 = 20 + 14 * r
    chunks = set()
    for u in range(12):
        b = (4 + 14 * k + u) * side
        for a in (a0, a0 + 1, a0 + 2):
            chunks.add(((ox * a + rx * b) >> 4, (oz * a + rz * b) >> 4))
    return chunks


def logo_chunks(group, rows):
    return set().union(*(place_chunks(group, r, k, side)
                         for r in range(rows + 1) for k in range(r + 1) for side in (1, -1)))


# HUB.md 3.3: a group's places, nearest first: by row, then by k, then L before R.
FILL_ORDER = [(r, k, side) for r in range(8) for k in range(r + 1) for side in (-1, 1)]


def needed(chunks):
    worst = max(max(0, abs(x) - 1) ** 2 + max(0, abs(z) - 1) ** 2 for x, z in chunks)
    distance = 2
    while not worst < distance * distance:
        distance += 1
    return distance


print('| Rows a group uses | Logos per group | Farthest logo corner from home | Render distance needed (per road) |')
print('|---|---|---|---|')
for rows in range(6):
    per_group = sum(2 * (r + 1) for r in range(rows + 1))
    corner = math.hypot(20 + 14 * rows + 2, 4 + 14 * rows + 11)
    each = {g: needed(logo_chunks(g, rows)) for g in GROUPS}
    print(f"| 0 to {rows} | {per_group} | {corner:.0f} blocks | {max(each.values())} "
          f"({', '.join(f'{g} {d}' for g, d in each.items())}) |")
for d in (4, 5, 6, 7, 8):
    end = 16 * d
    print(f'render distance {d}: terrain fades from {end - min(max(end / 10, 4), 64):.0f} to {end} blocks')

# Apps fill a group's places in HUB.md 3.3's order, so the distance a town needs follows from its biggest group's count.
print()
print('| Render distance | Most apps a group holds with every logo drawn from home: north, east, south, west |')
print('|---|---|')
need = {g: [needed(place_chunks(g, *place)) for place in FILL_ORDER] for g in GROUPS}
for d in range(2, 9):
    most = {g: next((i for i, n in enumerate(need[g]) if n > d), len(FILL_ORDER)) for g in GROUPS}
    print(f"| {d} | {', '.join(f'{g} {most[g]}' for g in GROUPS)} |")
for g in GROUPS:
    places = [f"{g[0].upper()}{r}{'L' if side < 0 else 'R'}{k}" for r, k, side in FILL_ORDER]
    steps = [f'{places[i]} (app {i + 1}) {need[g][i]}' for i in range(len(FILL_ORDER))
             if need[g][i] > max(need[g][:i], default=0)]
    print(f"{g}: the place that first needs more: {', '.join(steps)}")
