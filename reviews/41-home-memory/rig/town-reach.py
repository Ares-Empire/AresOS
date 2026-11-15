#!/usr/bin/python3
# DEVELOPMENT AID of package 41 (measurement only): which render distance the town needs, from its own rules.
"""usage: town-reach.py

For a town whose groups use rows 0..R (HUB.md 3.1 and 3.2: a logo fills outward a0..a0+2 with a0 = 20 + 14 r, and
sideways 4 + 14 k + u for u 0..11 on either side of the road), prints the farthest logo corner from home and the
least render distance at which every chunk holding a logo block is drawn from home. The game's rule
(ChunkTrackingView.isWithinDistance in 26.2, without the outer ring): a chunk dx, dz chunks from the player's is in
view when max(0, |dx| - 1)^2 + max(0, |dz| - 1)^2 < distance^2. The fog (FogRenderer) then fades the terrain from
16 d - clamp(1.6 d, 4, 64) to 16 d blocks."""
import math

GROUPS = {'north': ((0, -1), (1, 0)), 'east': ((1, 0), (0, 1)), 'south': ((0, 1), (-1, 0)), 'west': ((-1, 0), (0, -1))}


def logo_chunks(group, rows):
    (ox, oz), (rx, rz) = GROUPS[group]
    chunks = set()
    for r in range(rows + 1):
        a0 = 20 + 14 * r
        for k in range(r + 1):
            for side in (1, -1):
                for u in range(12):
                    b = (4 + 14 * k + u) * side
                    for a in (a0, a0 + 1, a0 + 2):
                        chunks.add(((ox * a + rx * b) >> 4, (oz * a + rz * b) >> 4))
    return chunks


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
