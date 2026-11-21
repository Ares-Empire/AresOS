# 332: inputs for revision 1

From `linux-desktop` (its OS part for section 12) and the owner's answers to section 11, both from Sat 2026-11-21 evening.

### `linux-desktop`'s part (Sat 2026-11-21 21:58)

**Layers** (wlr-layer-shell on labwc 0.9.6). Each has its own namespace, never `aresos-input-barrier`, which B321's labwc patch treats as the capture surface.

- **Picture, `aresos-picture`:** background layer, anchored on all four edges, exclusive zone -1, keyboard none. Its input region is the whole output, so a click on the picture never reaches labwc's Root context (see the `rc.xml` point below).
- **Bar, `aresos-bar`:**
  - Top layer while `shown`: above windows, below a true full-screen window.
  - When revealed at `edge`, it moves to overlay with `set_layer` (layer-shell v2+), and back to top when it hides.
  - Anchored bottom, left and right; exclusive zone 0 (reserves nothing); keyboard none.
  - Its menus are xdg_popups on it, pointer only.
- **Strip, `aresos-bar-edge`:** overlay layer. It exists only while that output's bar is `edge`. It is 1 logical px high and full width, with exclusive zone -1, keyboard none, and a transparent buffer with an input region.
- **Search, `aresos-search`:** overlay layer, keyboard exclusive while open. Esc, a click outside, or the recovery key ends it.
- **Toast, `aresos-toast`:** top layer, so not over a full-screen video. Keyboard none, and an empty input region, so clicks pass through, as with package 320's indicator.
- **The indicator** stays on overlay, above all of these.
- **To verify in a private labwc:**
  - the stacking: background < bottom < always-below views (the world) < views < top < full-screen < overlay;
  - `set_layer` support;
  - that a full-screen view hides the top layer.

**Strip and reveal:**
- **Timing:** rest 300 ms, slide 150 ms.
- **Drawing:** the surface keeps a fixed size and draws an offset, with the input region on the visible part only. No per-frame resize.
- **No reveal** while a button is held, during a Deskflow capture, or while the pointer is locked.
- **Deskflow:** the barrier edge wins. If the Mac is configured below the laptop, that output gets no strip on its bottom edge, and the bar is reachable by Super and search only (a known limit).

**Covering (T372/T373) feeding `screens`:**
- wlr-foreign-toplevel gives states and outputs but no window geometry. So until the layouts and covering packages ship (COMPONENTS 4.3's labwc patch that reports geometry), an output is covered when a window on it is maximized or full-screen and not minimized. That is today's rule, applied per output.
- A "full layout" counts only once covering ships.
- `aresos.cover` and `aresos.black` never cover; they make the bar `none`.

**Scaling:**
- The town and every look sprite scale by whole numbers, nearest-neighbour. Any leftover is centred on the picture's own edge colour.
- A picture file scales smoothly to cover the output, cropped centred.
- Each output uses its own scale factor.

**Look:**
- The bar is a new COMPONENTS.md piece, with the status icons (try-out item 9). `linux-desktop` writes its A/B/C, marks and look-B map rows there before package 4's brief.
- The frame package (B329, building now) sets A's colours and button cells, which the bar reuses.

**`rc.xml`** (to `linux-aresos` first):
- The image has no `<mouse>` section and no `menu.xml`. So labwc's defaults show its built-in root menu on a click on a bare desktop; it may hold Exit, still to verify.
- The picture covers that from package 3 on. Package 3 also makes the Root context's clicks do nothing, for when no picture is up.
- Nothing else in `rc.xml` for packages 3 to 5. The bar takes no keys, and Super stays 23c's.

**Packages 3, 4 and 5** are agreed as `linux-desktop`'s in section 10. Each gets its own brief from `linux-desktop` once the note is reviewed. Package 5 also needs the 1 px strip tested against B321's barrier in its harness.

### The owner's answers
- **T482 (Sat 2026-11-21), the default picture:** "A plain picture". The default behind apps and with the world off is a plain picture that `linux-desktop` draws in the look (A until B's files exist). Black and his own picture stay settings. The town from the side stops being the default; it stays an available kind only if it costs nothing extra.
- **T483 (Sat 2026-11-21), one bar instead of the hotbar:** "Ohhh good question. So the Mc hotbar wouldn't exist then? But isn't the taskbar design the Minecraft hotbar ? So I think keeping both makes sense". **Keep both.** In the world, the game's own hotbar (with the open/active marks of package 2); wherever the awake world isn't in view, the bar outside, which also looks like the Minecraft hotbar in look B. Package 10 ("One bar") is dropped from the migration; question 2 is answered. Told him that both look alike, so one bar stays possible later as a setting if he changes his mind.
- **T484 (Sat 2026-11-21), bars per screen:** "Yea both makes sense but only when going down right?". **A bar on every screen**, brought up by moving the pointer down. Follow-up asked (whether it also stays visible on a screen nothing fills).
- **T485 (Sat 2026-11-21), the follow-up:** "Visible there (recommended)". The bar stays visible on a screen nothing fills, and hides at the bottom edge while a window fills it, as the note's section 8 already has it. Question 3 is answered: a bar on every screen, each by its own screen's state.
