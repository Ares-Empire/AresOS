#!/usr/bin/python3
"""Draw the title bar buttons of the Ares-Crown window theme as SVG.

    python3 reviews/window-design-v1/draw-buttons.py os/config/usr/share/themes

writes <themes-dir>/<Theme>/labwc/<button>[_hover]-(active|inactive).svg for
Ares-Crown. The SVG files in the repo are this
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


if __name__ == "__main__":
    write_set(sys.argv[1], "Ares-Crown", crown)
