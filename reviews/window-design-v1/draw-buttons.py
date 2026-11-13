#!/usr/bin/python3
"""Draw the title bar buttons of the three AresOS window themes as SVG.

    python3 reviews/window-design-v1/draw-buttons.py os/config/usr/share/themes

writes <themes-dir>/<Theme>/labwc/<button>[_hover]-(active|inactive).svg for
Ares-Crown, Ares-Plain and Ares-Block. The SVG files in the repo are this
script's output: change a colour or a glyph here and run it again, so the 36
images of a theme stay in step.

Every image is exactly as large as the theme's button box (window.button.width x
window.button.height in its themerc), so one SVG unit is one screen pixel.
labwc 0.9 has no pressed state: each button has a normal and a hover image for
the active and the inactive window.
"""
import os
import sys

BUTTONS = ["menu", "iconify", "max", "max_toggled", "close", "shade", "shade_toggled", "desk", "desk_toggled"]


def svg(w, h, body, defs=""):
    d = f"\n  <defs>{defs}\n  </defs>" if defs else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{d}\n'
            f"{body.rstrip()}\n</svg>\n")


def write_set(out, theme, draw):
    d = os.path.join(out, theme, "labwc")
    os.makedirs(d, exist_ok=True)
    for b in BUTTONS:
        for hover in (False, True):
            for active in (True, False):
                name = f"{b}{'_hover' if hover else ''}-{'active' if active else 'inactive'}.svg"
                with open(os.path.join(d, name), "w") as f:
                    f.write(draw(b, hover, active))


# ---------------------------------------------------------------------------------------------
# Ares-Crown: thin rounded glyphs, a glass pill on hover (the hub's .emp-toggle), red only on close
# (the hub's .emp-logout), and the gold dot of the hub's mark as the window-menu button.
# ---------------------------------------------------------------------------------------------
CW, CH = 44, 36


def crown(b, hover, active):
    cx, cy = CW // 2, CH // 2
    ink = "#a6a39a" if active else "#5f5c55"
    body = ""
    defs = ""
    if b == "menu":
        if active or hover:
            defs = ('\n    <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
                    '<stop offset="0" stop-color="#fff4d4"/><stop offset="0.45" stop-color="#edca77"/>'
                    '<stop offset="1" stop-color="#b98a35"/></linearGradient>'
                    '\n    <radialGradient id="h" cx="0.5" cy="0.5" r="0.5">'
                    f'<stop offset="0.3" stop-color="#edca77" stop-opacity="{0.34 if hover else 0.2}"/>'
                    '<stop offset="1" stop-color="#edca77" stop-opacity="0"/></radialGradient>')
            body += f'  <circle cx="{cx}" cy="{cy}" r="{13 if hover else 11}" fill="url(#h)"/>\n'
            body += f'  <circle cx="{cx}" cy="{cy}" r="4.5" fill="url(#g)"/>\n'
        else:
            body += f'  <circle cx="{cx}" cy="{cy}" r="4" fill="none" stroke="#5f5c55" stroke-width="1.4"/>\n'
        return svg(CW, CH, body, defs)
    if hover:
        if b == "close":
            fill, edge, ink = "#ff3c3c", "#ff5a5a", "#ff9a9a"
            fo, eo = 0.16, 0.42
        else:
            fill, edge, ink = "#edca77", "#ecd496", "#fff4d4"
            fo, eo = 0.10, 0.30
        body += (f'  <rect x="6.5" y="5.5" width="31" height="25" rx="8" fill="{fill}" fill-opacity="{fo}" '
                 f'stroke="{edge}" stroke-opacity="{eo}"/>\n')
    s = f'fill="none" stroke="{ink}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"'
    if b == "iconify":
        body += f'  <path d="M17 18h10" {s}/>\n'
    elif b == "max":
        body += f'  <rect x="17.25" y="13.25" width="9.5" height="9.5" rx="2.2" {s}/>\n'
    elif b == "max_toggled":
        body += f'  <rect x="16.25" y="15.25" width="8.5" height="8.5" rx="2" {s}/>\n'
        body += f'  <path d="M19.4 12.75h6.35a2 2 0 0 1 2 2v6.35" {s}/>\n'
    elif b == "close":
        body += f'  <path d="M17.5 13.5l9 9M26.5 13.5l-9 9" {s}/>\n'
    elif b == "shade":
        body += f'  <path d="M17 13.5h10M18 21.5l4-4 4 4" {s}/>\n'
    elif b == "shade_toggled":
        body += f'  <path d="M17 13.5h10M18 18l4 4 4-4" {s}/>\n'
    elif b == "desk":
        body += f'  <circle cx="{cx}" cy="{cy}" r="4.5" {s}/>\n'
    elif b == "desk_toggled":
        body += f'  <circle cx="{cx}" cy="{cy}" r="4.5" {s}/>\n'
        body += f'  <circle cx="{cx}" cy="{cy}" r="1.9" fill="{ink}"/>\n'
    return svg(CW, CH, body)


# ---------------------------------------------------------------------------------------------
# Ares-Plain: the caption buttons Windows users know. Wide, flat, 1px glyphs; hover fills the
# whole box up to the window's corner, close turns red.
# ---------------------------------------------------------------------------------------------
PW, PH = 46, 36


def plain(b, hover, active):
    ink = "#1a1813" if active else "#8f8a7f"
    body = ""
    if hover:
        if b == "close":
            body += f'  <rect width="{PW}" height="{PH}" fill="#c9372c"/>\n'
            ink = "#ffffff"
        else:
            body += f'  <rect width="{PW}" height="{PH}" fill="#1a1813" fill-opacity="0.09"/>\n'
            ink = "#1a1813"
    crisp = f'fill="none" stroke="{ink}" stroke-width="1" shape-rendering="crispEdges"'
    soft = f'fill="none" stroke="{ink}" stroke-width="1.15" stroke-linecap="square"'
    if b == "iconify":
        body += f'  <path d="M18 18.5h10" {crisp}/>\n'
    elif b == "max":
        body += f'  <rect x="18.5" y="13.5" width="9" height="9" {crisp}/>\n'
    elif b == "max_toggled":
        body += f'  <rect x="18.5" y="15.5" width="7" height="7" {crisp}/>\n'
        body += f'  <path d="M20.5 15.5v-2h7v7h-2" {crisp}/>\n'
    elif b == "close":
        body += f'  <path d="M18.5 13.5l9 9M27.5 13.5l-9 9" {soft}/>\n'
    elif b == "menu":
        body += f'  <path d="M18 14.5h10M18 18.5h10M18 22.5h10" {crisp}/>\n'
    elif b == "shade":
        body += f'  <path d="M18 13.5h10" {crisp}/>\n  <path d="M19 21.5l4-4 4 4" {soft}/>\n'
    elif b == "shade_toggled":
        body += f'  <path d="M18 13.5h10" {crisp}/>\n  <path d="M19 17.5l4 4 4-4" {soft}/>\n'
    elif b == "desk":
        body += f'  <circle cx="23" cy="18" r="4.5" fill="none" stroke="{ink}" stroke-width="1"/>\n'
    elif b == "desk_toggled":
        body += f'  <circle cx="23" cy="18" r="4.5" fill="none" stroke="{ink}" stroke-width="1"/>\n'
        body += f'  <circle cx="23" cy="18" r="2" fill="{ink}"/>\n'
    return svg(PW, PH, body)


# ---------------------------------------------------------------------------------------------
# Ares-Block: everything sits on a grid of 2x2 screen pixels ("texels"). A button is a sunken
# slot of 16x16 texels with an 8x8 texel glyph in it, its strokes two texels wide like the stems
# of the title's pixel font. Drawn from rectangles only.
# ---------------------------------------------------------------------------------------------
TX = 2
BN = 16  # slot size in texels: a one-texel edge around 14x14, the 8x8 glyph in the middle

GLYPHS = {
    "close": ["XX....XX", "XXX..XXX", ".XXXXXX.", "..XXXX..", "..XXXX..", ".XXXXXX.", "XXX..XXX", "XX....XX"],
    "max": ["XXXXXXXX", "XXXXXXXX", "XX....XX", "XX....XX", "XX....XX", "XX....XX", "XXXXXXXX", "XXXXXXXX"],
    "max_toggled": ["..XXXXXX", "..XXXXXX", "XXXXXX.X", "XXXXXX.X", "X....X.X", "X....XXX", "X....X..", "XXXXXX.."],
    "iconify": ["........", "........", "........", "........", "........", "........", "XXXXXXXX", "XXXXXXXX"],
    "menu": ["XXXXXXXX", "XXXXXXXX", "........", "XXXXXXXX", "XXXXXXXX", "........", "XXXXXXXX", "XXXXXXXX"],
    "shade": ["XXXXXXXX", "XXXXXXXX", "........", "...XX...", "..XXXX..", ".XXXXXX.", "XXXXXXXX", "........"],
    "shade_toggled": ["XXXXXXXX", "XXXXXXXX", "........", "XXXXXXXX", ".XXXXXX.", "..XXXX..", "...XX...", "........"],
    "desk": ["..XXXX..", ".XXXXXX.", "XXX..XXX", "XX....XX", "XX....XX", "XXX..XXX", ".XXXXXX.", "..XXXX.."],
    "desk_toggled": ["..XXXX..", ".XXXXXX.", "XXXXXXXX", "XXXXXXXX", "XXXXXXXX", "XXXXXXXX", ".XXXXXX.", "..XXXX.."],
}


def texels(rows, ox, oy, colour):
    """Merge each row's runs into one rectangle so the files stay small and exact."""
    out = ""
    for y, row in enumerate(rows):
        x = 0
        while x < len(row):
            if row[x] == "X":
                x0 = x
                while x < len(row) and row[x] == "X":
                    x += 1
                out += (f'  <rect x="{(ox + x0) * TX}" y="{(oy + y) * TX}" width="{(x - x0) * TX}" '
                        f'height="{TX}" fill="{colour}"/>\n')
            else:
                x += 1
    return out


def block(b, hover, active):
    size = BN * TX
    if active:
        face, dark, light, ink = "#8b8b8b", "#373737", "#ffffff", "#262626"
    else:
        face, dark, light, ink = "#7d7d7d", "#4b4b4b", "#b4b4b4", "#4a4a4a"
    if hover:
        ink = "#1c1c1c"
        face = "#e2e2e2"          # the slot lights up under the pointer
        dark, light = "#373737", "#ffffff"
        if b == "close":
            face, ink = "#c0392f", "#ffffff"
    body = f'  <rect width="{size}" height="{size}" fill="{face}"/>\n'
    # sunken edge: dark along the top and left, light along the bottom and right; the two
    # corners where they meet keep the face colour
    body += f'  <rect x="0" y="0" width="{size - TX}" height="{TX}" fill="{dark}"/>\n'
    body += f'  <rect x="0" y="{TX}" width="{TX}" height="{size - 2 * TX}" fill="{dark}"/>\n'
    body += f'  <rect x="{TX}" y="{size - TX}" width="{size - TX}" height="{TX}" fill="{light}"/>\n'
    body += f'  <rect x="{size - TX}" y="{TX}" width="{TX}" height="{size - 2 * TX}" fill="{light}"/>\n'
    body += texels(GLYPHS[b], 4, 4, ink)
    return svg(size, size, body).replace("<svg ", '<svg shape-rendering="crispEdges" ')


if __name__ == "__main__":
    out = sys.argv[1]
    write_set(out, "Ares-Crown", crown)
    write_set(out, "Ares-Plain", plain)
    write_set(out, "Ares-Block", block)
