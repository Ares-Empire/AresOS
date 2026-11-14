# App windows: the frame around every program

**Decision: 2026-11-13 (board #206).** The owner chose Ares-Crown: "None look crazy tbh but yes crown.
But chrome shouldn't get the extra bar, other OS don't have that right? It looks weird".

Package 31 ships **Ares-Crown as designed**, Space Grotesk with its OFL licence, thumbnail Alt+Tab, and the
AresOS-scoped GSettings default `appmenu:minimize,maximize,close` for programs with their own bars. The image build
compiles the schemas. **Chrome keeps its own tab bar**, with all three buttons and no second title bar; there is
no Chrome preference, policy or decoration rule. Ares-Plain and Ares-Block were not chosen and their files do not
ship; their pictures and design remain below and their files remain in git history.

Verification and fallback pictures: [package 31 report](../../reviews/31-window-frame/REPORT.md). The look on the
real panel, Discord and the Lunar Client launcher still need the owner's check. Only title-bar size on the real
panel and a possible dark preference for other apps remain open.

The original design exploration follows, updated to distinguish what ships from the two alternatives.

The owner (2026-11-13): "The app windows I dont really have a design for yet. The ares apps have a design style but
its more for apps. I dont know if its copiable onto app windows. [...] you can build custom window designs that fit
ares apps / aresos or just build them like windows as a default."

Short answer: yes, the Ares style carries onto a window frame, with a few things left out that the compositor cannot
draw. All three themes below keep what he knows from Windows: the title at the left of the bar, minimize, maximize and
close at the right in that order, and X closes the window and puts him back in the world.

## Before package 31

![Today's frame: labwc's grey default](../../reviews/window-design-v1/08-today.png)

The previous default was a 26-pixel grey bar with tiny buttons. The active and the inactive window look almost the same.

## The shipped theme

Each picture is a real screenshot at the laptop's 1920x1080: an inactive window (the editor) and the active one (the
terminal) over a bright scene. The scene is a drawing made for these tests, not the game.

### Ares-Crown: the Empire's look on a frame

![Ares-Crown](../../reviews/window-design-v1/01-crown.png)

The crown language (`ares-empire/EMPIRE.md`) says: near-black wall, off-white text, polished gold as the one sparing
accent, glass. On a frame that becomes:

- **The wall:** a near-black title bar (36 px) with a faint sheen on the active window, flat on the others.
- **The one gold accent:** the gold dot at the left of the active window, taken from the hub's own mark
  (`.emp-mark-dot`). Inactive windows show an empty ring. A click on it opens the window menu, like the icon in the
  corner of a Windows title bar.
- **Text:** the title in Space Grotesk Medium, off-white, 17 px; dimmed on inactive windows.
- **Buttons:** thin rounded glyphs. Under the pointer a button lights up as a glass pill with a gold tint, as the hub's
  buttons do; close lights up red, as the hub's logout does.
- **Edge:** a 1 px warm line all round, top corners rounded by 10 px, a deep soft shadow.
- **Alt+Tab:** a dark panel with a preview picture of each window; the chosen one has a gold outline.

Ships with Space Grotesk in the image (see "Image additions"). Without it labwc uses the system's
default sans font and the theme still looks right (tried, including package 31's recovery shortcut).

### More pictures

- [All three over a dark scene](../../reviews/window-design-v1/04-dark-scene.png) (the hub's home is the Nether, so
  the scene behind a window will often be dark red, not daylight).
- [Buttons close up](../../reviews/window-design-v1/05-buttons.png): active, pointer on minimize, pointer on close,
  maximized, inactive.
- [Window menu and Alt+Tab](../../reviews/window-design-v1/06-menus-switcher.png) in each theme.

## Why Ares-Crown was recommended and chosen

1. **It is ours.** AresOS belongs to the Empire, and this is the Empire's look reduced to what a frame needs: wall,
   text, one gold point. Nothing on it is decoration.
2. **It recedes.** A black bar lets the program be the content. With the terminal it forms one dark surface; on a light
   program it is a clear dark band.
3. **It holds on both scenes.** Over daylight the shadow and the black bar carry it; over the dark red of the Nether the
   warm edge line does, and black and gold on dark red is the Ares picture anyway.
4. **The active window is obvious** without colour noise: gold dot and bright title against an empty ring and a dim
   title.
5. **It still behaves like Windows.** Same places, same order, X closes.

Its cost is one font file of 137 KB, which the Empire's websites and iPhone apps already ship.

Ares-Plain is the safe second: no cost at all, and it sits closest to programs that draw their own light title bar
(Chrome, GNOME apps). It remains an unchosen alternative.

Ares-Block is the most playful and the closest to the world behind the windows. I would not make it the default: a
pixel title is harder to read for long file names, and a game panel around Chrome or an editor reads as a costume
after a while. Its finished design remains in git history.

## What every theme covers

| Part | State |
|---|---|
| Title bar, title text, border, shadow | active and inactive window |
| Minimize, maximize, restore (maximized), close | normal and under the pointer, for active and inactive windows |
| Window-menu button, roll-up and all-workspaces buttons | drawn too, so a later change of the button layout never shows a grey default |
| Maximized window | square corners, no border, the restore glyph |
| Menus (window menu, root menu) | background, text, highlighted row, separator, title, border |
| Alt+Tab | both of labwc's styles (pictures and list), the chosen entry, the outline around the window about to be picked |
| On-screen notes | workspace note, move and resize note |
| Snapping | the preview where a dragged window will land |

Every row was looked at in a screenshot, except the root menu, which uses the same settings as the window menu.

The shipped theme is a `themerc` and 36 SVG button images under `os/config/usr/share/themes/Ares-Crown/labwc/`.
The images are the output of `reviews/window-design-v1/draw-buttons.py`, now limited to Crown: change a colour or a
glyph there and run it again, so all 36 stay in step. The original exploration covered all three alternatives.

**How it was tested.** In a separate labwc 0.9.6 that draws to memory only (wlroots' headless backend, 1920x1080), with
its own runtime folder, D-Bus, home folder and font folder, never on the owner's screen. Windows: `foot`, `kwrite`,
Chrome with throwaway profiles, small GTK3, GTK4 and libadwaita sample windows, `glxgears` (X11), and a two-window
Electron 44.9.0 test app. A small script moved a virtual pointer and pressed virtual keys (hover, right-click, Alt+Tab,
workspace switch, dragging), and `grim` took the pictures. labwc's verbose log shows no complaint about any theme.

## What labwc 0.9.6 cannot do

Things I wanted and what stands in their place:

| Wanted | labwc | In the themes |
|---|---|---|
| Glass: a blurred, see-through bar (crown language) | no blur | a solid near-black bar with a faint top-to-bottom sheen |
| Gold gradient text, capitals, wide letter-spacing for the title | one flat colour, no text effects | off-white title; the gold moved into the dot |
| A bright gradient edge | one colour and one width for the whole border | a 1 px warm line |
| All four corners rounded | only the top corners | square bottom corners |
| A pressed look for buttons | normal and hover images only | none |
| A raised edge on the frame for Ares-Block (light top and left, dark bottom and right) | the border is one colour | a plain 2 px outline; the raised and sunken edges live in the buttons |
| A hard pixel shadow for Ares-Block | soft shadows only | a short soft shadow |
| A small app icon next to wide buttons (Ares-Plain) | the icon's size follows the button box | a larger icon than Windows shows |
| Space before the title without a button at the left | the title starts flush at the edge | every layout keeps one button at the left (dot or icon) |
| Any font size | whole points only (`20.25` is read as 20) | Jersey 10 at 21 pt = 28 px, its exact double size. A few letter edges still land on half pixels, because the font's own spacing uses quarter steps |
| The whole look in the theme folder | corner radius, fonts, shadows on or off, button order and Alt+Tab style are `rc.xml` settings | the lines below must change together with the theme's name |

Two notes on labwc's manual: it says font sizes are pixels, but they are points (13 gives 17 px text, 21 gives 28 px).
And a hover image is clipped to the rounded corner by labwc itself, so Ares-Plain's red close button follows the
corner without extra work.

## Programs that draw their own frame

The theme only reaches programs that let the compositor draw their frame. Tried on this machine:

| Program | Wears the AresOS frame? | What can be done |
|---|---|---|
| Terminal (`foot`) | yes | |
| Notepad (`kwrite`) and other Qt/KDE programs | yes | |
| Plain GTK3 and GTK4 windows | yes | |
| X11 programs through Xwayland (`glxgears`) | yes | |
| Chrome 157 | **no**: its own bar with the tabs in it; package 31 gives it all three buttons | keeps its own bar |
| Chrome with "Use system title bar and borders" | yes | one switch in Chrome's settings |
| Chrome app windows (`--app=`) | yes | |
| Electron 44 app with the normal frame | yes | |
| Electron 44 app without a frame (chat apps, game launchers) | **no**: draws its whole window | nothing |
| GNOME apps (libadwaita) and GTK apps with a header bar | **no**: own header bar; package 31 gives it all three buttons | the button setting below |

![Our frame next to programs that draw their own](../../reviews/window-design-v1/07-other-apps.png)

(Ares-Crown, with the button setting below applied. The editor and the lower Chrome wear the AresOS frame; the upper
Chrome, the GNOME sample and the frameless Electron sample draw their own.)

**One setting gives them all three buttons.** Chrome and GNOME apps show only a close button because GNOME's default
for `org.gnome.desktop.wm.preferences button-layout` is `appmenu:close`. Set to `appmenu:minimize,maximize,close`,
Chrome's own bar and every header bar show minimize, maximize and close at the right, in our order. Originally tried with
`gsettings set`; package 31 ships and tests the compiled AresOS-scoped default (see "Image additions").

**Chrome: the choice and the alternative.**

- *Leave Chrome's own bar* (chosen).  With the button setting it looks like Chrome on Windows: tabs on top, three
  buttons at the right. It costs no screen height and is what he knows.
- *Switch on "Use system title bar and borders"* (Chrome's settings, Appearance). Chrome then wears the AresOS frame
  like every other program, at the cost of 36 px of height. I found no Chrome policy for this switch (none among the
  policy names in Chrome's program file). It is the profile preference `browser.custom_chrome_frame` (`false` =
  system title bar); tried by writing it into a fresh throwaway profile.

A labwc window rule (`serverDecoration="yes"`) is **not** a way: labwc then draws its frame, and Chrome keeps its own
close button in the tab bar, so the window has two.

**Frameless Electron apps** (the Lunar Client launcher is Electron 44.9.0; Discord is the same kind) draw their title
bar, corners and shadow themselves. A window rule would only put a second bar on top. Nothing to do, and nothing
needed: they are dark, and next to Ares-Crown they look at home.

**Which theme sits best next to these?** Ares-Plain is closest to Chrome's and GNOME's light bars. Ares-Crown is
closest to dark apps such as the terminal and frameless launchers, and next to it Chrome simply looks like Chrome.
Ares-Block is the furthest from all of them.

## Shipped configuration

Package 31 replaces only `<theme><name>Default</name></theme>` in `rc.xml` with the Crown block below and adds its
`<windowSwitcher>` line. Key bindings and window rules are unchanged. These are the settings used for its pictures.

**Ares-Crown**

```xml
  <theme>
    <name>Ares-Crown</name>
    <icon>breeze</icon>
    <fallbackAppIcon>application-x-executable</fallbackAppIcon>
    <cornerRadius>10</cornerRadius>
    <dropShadows>yes</dropShadows>
    <titlebar><layout>menu:iconify,max,close</layout></titlebar>
    <font place="ActiveWindow"><name>Space Grotesk</name><size>13</size><weight>medium</weight></font>
    <font place="InactiveWindow"><name>Space Grotesk</name><size>13</size><weight>medium</weight></font>
    <font place="MenuHeader"><name>Space Grotesk</name><size>12</size><weight>bold</weight></font>
    <font place="MenuItem"><name>Space Grotesk</name><size>12</size></font>
    <font place="OnScreenDisplay"><name>Space Grotesk</name><size>13</size><weight>medium</weight></font>
  </theme>
  <windowSwitcher><osd style="thumbnail" /></windowSwitcher>
```

What the lines do:

- `<icon>` names the icon set for app icons in the title bar and in Alt+Tab. Without it labwc looks for an icon set
  named like the theme, and there is none.
- `<fallbackAppIcon>`: the terminal opened from the hub has the app id `aresos.terminal`, which has no desktop entry,
  so it has no icon; labwc's own fallback icon is not in the image. With this line such windows get a generic program
  icon instead of an empty space. A desktop entry `aresos.terminal.desktop` with a terminal icon would be the better
  fix; it is left out here because another session is building the program listing in `aresos-shell`, and a new
  desktop entry could show up in it.
- `<cornerRadius>`, `<dropShadows>`, `<font>` and `<windowSwitcher>` belong to the theme's look but are `rc.xml`
  settings in labwc.
- Sizes are whole points: 12 = 16 px, 13 = 17 px, 21 = 28 px.

Dragging the bar, double-click to maximize, dragging to the top edge to maximize and the right-click window menu are
labwc's default mouse settings; they are not changed.

### Image additions

| For | What | Size and licence |
|---|---|---|
| Ares-Crown | `/usr/share/fonts/aresos/SpaceGrotesk-Variable.ttf`, with `OFL-SpaceGrotesk.txt`. Unchanged from `ares-empire/web/fonts/` | 137 KB, SIL Open Font License 1.1, © 2020 The Space Grotesk Project Authors |
| Apps with their own bar | `/usr/share/glib-2.0/schemas/zz-aresos.gschema.override`: `[org.gnome.desktop.wm.preferences:AresOS]`, `button-layout='appmenu:minimize,maximize,close'` | A default only in `XDG_CURRENT_DESKTOP=AresOS`; saved user settings still win |

The configure step runs `glib-compile-schemas --strict /usr/share/glib-2.0/schemas`; errors fail the build.
`gschemas.compiled` changes in the image: the next release's image diff needs a rule for it, which the OS lead writes.
The image checks validate all 36 button images, the theme configuration, the font and licence, and query the compiled
AresOS default as `ares` with a fresh home and memory settings backend.

Space Grotesk SHA-256: `acad6de1fc93436f5c0f1f4137751ef04f1aea3063e7036535970ffcfbd79f72`.
The README lists its copyright and licence. Neither Jersey 10 nor either alternative theme ships.

## Still open

1. **Size on the real panel.** Crown's bar is 36 px high with a 17 px title. The owner needs to judge size and
   legibility on the laptop's screen with the real game behind it.
2. **A dark look for other programs later.** Telling programs to prefer their dark look would change every app's
   appearance and is outside package 31.

## Not chosen

The following designs and pictures are retained as alternatives. Their theme files stay in git history, and
switching either on would first need its files restored. The original Block design also needs Jersey 10 installed.

### Ares-Plain: like Windows, but ours

![Ares-Plain](../../reviews/window-design-v1/02-plain.png)

The frame a Windows user already knows, in the Empire's day colours (the "marble hall" of the iPhone apps' light mode:
ivory wall `#EFEDE6`, near-black ink `#1A1813`, antique gold).

- The app's icon and the title at the left, three wide flat buttons at the right (46x36 px each).
- Under the pointer a button's whole box fills in, up to the window's corner; close turns red with a white X.
- A 1 px antique-gold line marks the active window; the others get a quiet grey line and grey text.
- Title in Adwaita Sans, 16 px. Top corners rounded by 8 px.
- Alt+Tab: a light panel with preview pictures.

Needs: nothing. Every font and icon it uses is already in the image.

### Ares-Block: a frame from the block world

![Ares-Block](../../reviews/window-design-v1/03-block.png)

A flat grey panel with a hard dark outline and square corners. The buttons are sunken slots with pixel glyphs in them;
under the pointer a slot lights up, close turns red. Everything sits on a grid of 2x2 screen pixels: the 2 px outline,
the 40 px bar, the 32 px slots, the glyphs. The title is set in the pixel font Jersey 10 at twice its drawn size.
Alt+Tab is a list like the game's own lists: the chosen row has a white outline.

Drawn from scratch from rectangles and flat greys: no texture, font, sound or image of the game is used or copied, and
Jersey 10 is a sports-lettering pixel font, not a copy of the game's font.

Needs: the font Jersey 10 in the image (details below). Do not switch this theme on before the font
is there: the fallback font at this size is much too large and makes the bar taller.

### Alternative configurations (reference only)

**Ares-Plain**

```xml
  <theme>
    <name>Ares-Plain</name>
    <icon>breeze</icon>
    <fallbackAppIcon>application-x-executable</fallbackAppIcon>
    <cornerRadius>8</cornerRadius>
    <dropShadows>yes</dropShadows>
    <titlebar><layout>icon:iconify,max,close</layout></titlebar>
    <font place="ActiveWindow"><name>Adwaita Sans</name><size>12</size></font>
    <font place="InactiveWindow"><name>Adwaita Sans</name><size>12</size></font>
    <font place="MenuHeader"><name>Adwaita Sans</name><size>10</size><weight>semibold</weight></font>
    <font place="MenuItem"><name>Adwaita Sans</name><size>12</size></font>
    <font place="OnScreenDisplay"><name>Adwaita Sans</name><size>12</size></font>
  </theme>
  <windowSwitcher><osd style="thumbnail" /></windowSwitcher>
```

**Ares-Block**

```xml
  <theme>
    <name>Ares-Block</name>
    <icon>breeze</icon>
    <fallbackAppIcon>application-x-executable</fallbackAppIcon>
    <cornerRadius>0</cornerRadius>
    <dropShadows>yes</dropShadows>
    <titlebar><layout>icon:iconify,max,close</layout></titlebar>
    <font place="ActiveWindow"><name>Jersey 10</name><size>21</size></font>
    <font place="InactiveWindow"><name>Jersey 10</name><size>21</size></font>
    <font place="MenuHeader"><name>Jersey 10</name><size>21</size></font>
    <font place="MenuItem"><name>Jersey 10</name><size>21</size></font>
    <font place="OnScreenDisplay"><name>Jersey 10</name><size>21</size></font>
  </theme>
  <windowSwitcher><osd style="classic" /></windowSwitcher>
```

Jersey 10's tested file was `Jersey10-Regular.ttf`, SHA-256
`db9cbd091617048a145d249daa2b815fe7083be6ab66ac26626e21a4e01c3e82`, from Google Fonts' `ofl/jersey10`;
78 KB, SIL Open Font License 1.1, © 2023 The Soft Type Project Authors. It is not in the image.

## Not verified

- **On the real screen.** Everything was looked at as screenshots; size and legibility on the laptop's panel, and the
  real game behind the windows, need his eyes.
- **Original exploration vs package 31.** The exploration used temporary fonts and a hand-set button layout.
  Package 31 tests the installed font and compiled desktop-scoped override; see its report for image-build results.
  Chrome initial preferences are deliberately absent, following the owner's decision.
- **The Lunar Client launcher and Discord themselves** were not started; the Electron findings come from a test app
  on the same Electron version.
- **Flatpak apps** (KCalc, Flatseal, Firefox): the sandbox did not start inside the isolated test session. KCalc is a
  Qt program and should wear the frame like KWrite; Flatseal is a GNOME app and should behave like the GNOME sample.
