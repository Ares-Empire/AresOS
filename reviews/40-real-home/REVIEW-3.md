# Package 40, review 3 (PR #71, `pkg/40-real-home` at `8e5eb1ad`)

Reviewer: a fresh Claude agent on Opus 5.5. I did not build this package or write reviews 1 and 2. I only read, apart
from this file. This review covers review fixes 2 (`f2224715..8e5eb1ad`) and what those fixes touch.

**Verdict: SAFE** (0 blocking, 0 should-fix, 1 nit). REVIEW-2's three findings are answered:
- finding 1 is fixed and has a test that fails without the fix;
- finding 2 is recorded under Known limits;
- finding 3's note now names the two bound files.

I found no order of mouse events that opens an app on a drag except one rare case, and it is older than this round:
a press whose release never reached the screen. That is the nit below. The fix is two lines and one test.

## What I checked, and how

- **Read:** REVIEW-2, item 7 of `briefs/40-review-fixes-1.md`, the REPORT's "Review fixes 2" section,
  `docs/REVIEW.md`, the round's diff (5 files), the whole `AppsScreen.java`, the test's Apps screen part and its
  helpers, `IconReload.java`, `IconRefresh.java` and `AppInventory.keepsOnClick`.
- **Minecraft 26.2, checked with `javap -c`.** I read the mapped jar in `mod/.gradle/loom-cache`. Its
  `AbstractContainerScreen` is byte-identical to the one in `~/.gradle/caches/fabric-loom`.
  - `MouseHandler.onButton`:
    - It hands a press and a release to the screen at once, at the current pointer position.
    - A double click needs the same screen, the same button and less than 250 ms.
    - Any release clears `activeButton`.
    - While `gui.overlay()` is set, neither a press nor a release reaches the screen.
  - `onMove` always updates the pointer position. It adds to the movement only while `isWindowActive()` is true.
  - `handleAccumulatedMovement` sends `mouseDragged` once a frame, and only when all of these hold: the window is
    active, the pointer moved, and `activeButton` is set.
  - So a release always carries the true pointer position, even in a window without focus. The new release-distance
    test therefore sees every drag that no frame saw.
  - `AbstractContainerScreen.skipNextRelease`:
    - The constructor sets it to true.
    - `mouseClicked` sets it to false at offset 85. That happens after `Screen.mouseClicked` has returned false, so
      only for a press that no widget takes, and before any slot is looked at. It is set back to true only after a
      click with nothing on the cursor (offset 310).
    - `mouseReleased` changes it only in its two early returns.
  - With an item on the cursor, a press on a slot starts `isQuickCrafting`. Its release goes on in one of two ways:
    - with no slots dragged over, `PICKUP` on the slot under the pointer;
    - otherwise `quickCraftToSlots`.

    Either way the item is placed. The report's `javap` claims hold.
  - `Minecraft.reloadResourcePacks` sets a `LoadingOverlay`. When the reload ends, `LoadingOverlay` calls
    `screen.init(w, h)`.
- **Fabric's `TestInput.pressMouse`** (client-gametest-api 6.0.2) is `holdKey`, `releaseKey`, then one tick. So the
  test's slot click goes through `MouseHandler.onButton` into `InventoryScreen.mouseClicked` and `mouseReleased`.
- **The cases the brief asked about** (`AppsScreen.java`):

  | Case | What happens | Result |
  |---|---|---|
  | Release with no drag | `movedAway` is false, so it opens. | Right |
  | Drag, then release | A frame that sees more than 3 px picks the item up in `mouseDragged`, and the screen becomes the inventory. The release goes there and places the item. If no frame saw the move, the release is more than 3 px away and picks the item up. | Right |
  | A drag that comes back to the press point | A frame that saw it already picked the item up. If no frame saw it (out and back within one stalled frame, ending within 3 px), it reads as a click and opens. The screen cannot see this without the raw moves. | Accepted (see "Not findings") |
  | Release after the screen changed | `pressed` belongs to an `AppsScreen` that nothing shows again (each "Apps…" makes a new one). Tick's `onClose` and Escape hand the release to the inventory, which has nothing on the cursor. | Right |
  | Release swallowed while the screen stays | `pressed` stays set. | Nit 1 |
  | A second press before the release (right or middle button) | A right press on a row resets `pressed` in `press()`, so the left release does nothing (and one of his is removed, as a right-click should). A press elsewhere, or a middle press, leaves `pressed`. Its release clears `activeButton`, so no more `mouseDragged` arrives, and the left release's distance decides. That case opened on a drag before this round and now picks up. | Right |
  | Double click | The first click opens and the screen closes, so the second press goes to the world (REVIEW-2). The first is a flick, so the screen is the inventory: a different screen, so no double click, and the second press is an inventory click. A double click on a row clears `pressed`. | Right |
  | Search box has the focus | A press on a row still goes to the list. A press in the box leaves `pressed` null. A release over the box after a press on a row is a drag. Enter opens only through `enter()`. | Right |
  | Scrolling the list mid-press | The pointer does not move, so the release opens `pressed`: the program he pressed on, even if another row is under the pointer now. Not a drag. | Right |
- **After a pick-up at the release, the next click places the item.** The screen is `InventoryScreen` and the button is
  up. When the item arrives on the cursor:
  - A press on a slot clears the flag, starts placing, and its release does `PICKUP` on the slot.
  - A press on the recipe-book widget leaves the flag false. Its release sends a click on slot -1, which the server
    ignores, as in vanilla.
  - A click outside the panel is `PICKUP` at -999. `keepsOnClick` refuses it for an app's item.
  - A press on "Apps…" fires on the press, and its release goes to the new Apps screen (as before this round).

  So the accessor's `false` changes nothing on this path, as the code comment and the report say.
- **The test** (`MyAppsClientGameTest.java:330` to `370`):
  - It would fail without the fix. The old `mouseReleased` calls `open`, which calls `closeContainer`, so the screen
    becomes null and the first check fails. `AresOsClient.launch` calls `launchTracked` synchronously, so `opened`
    would already show `okular` in the message.
  - What it checks:
    - the inventory comes back;
    - the item is on the cursor and still there 5 ticks later;
    - a real slot click through the mouse handler places it on the client and on the server, with an empty cursor;
    - `opened` is unchanged.
  - The boundary is pinned too: `dragRow`'s 2-pixel `mouseDragged` must stay a click, and that goes through the
    shared `movedAway`.
- **`pending-rebind.json`:**
  - There is exactly one entry starting with "40:".
  - Its numbers match the package diff: `timeout-minutes` 25 to 40 in `os-image.yml`, and `job_bounds.checks` 35 to
    40 in `rehearsal-packages.json`.
  - `sha256sum` of the four listed files equals their rows.
  - Read-only, `rebind.changed()` equals `files` (4 rows) and `rebind.removed()` equals `removed` (empty).
  - The file is byte-identical to what `rebind.write` would write.
  - `python3 -B -m unittest discover -s os/tests -p test_checkout_sources.py`: 6 tests, OK.
- **Docs:**
  - HUB.md 2.4's new sentence matches the code: a drag seen only at the release opens nothing, and the item waits on
    the cursor.
  - The report's finding 1 text, test description and Known limits entry match the code and REVIEW-2.
- **Privacy:**
  - I matched the round's added lines and its commit message against the names and IDs of every desktop entry the
    laptop has: the user's own, user Flatpak and system Flatpak. The only match is Okular, an allowed test fixture.
  - The round adds no pictures.

## Findings

### 1. nit: a press whose release never reached the screen acts on the next click elsewhere

**Where:** `mod/src/client/java/dev/aresos/client/AppsScreen.java:230` to `240` (`mouseReleased` acts on any left
release while `pressed` is set). `pressed` is set only in `press()` (`:197` to `211`), and only for a press on a row.
It is cleared only there, in `mouseDragged`, in `mouseReleased` and on a double click on a row (`:417`). A press on the
search box, a heading, the empty list or the scroll bar leaves an old value in place. `init()` (`:99`) does not clear
it either.

**How a release gets lost:**
- `MouseHandler.onButton` drops presses and releases while `gui.overlay()` is set.
- `IconReload` (`IconReload.java:28` to `35`) calls `client.reloadResourcePacks()`, which puts up a `LoadingOverlay`,
  whenever a catalogue update from the helper changed a picture. Such an update can arrive while the Apps screen is
  open.
- After the reload, `LoadingOverlay` calls `screen.init(...)`, which keeps `pressed`.

**Scenario:**
1. He has just installed a program and opens Apps… to find it. The helper's new list arrives and the new icon is made.
2. The loading screen comes up just as he presses on Discord's row, and he lets go while it shows. That release is
   dropped.
3. After the loading screen he clicks in the search box to type. That release finds `pressed = "discord"`, well over
   3 px from the old press point, and calls `pickUp`.
4. The Apps screen gives way to the inventory with Discord's item on the cursor. A click never picks one up, yet this
   one did. A click within 3 px of the old point would open Discord instead.

Before this round the same stale press opened the program on any release. So this is not a regression, it is rare
(a reload has to start during a press), and the harm is small. It is the one order of events I found that still
breaks item 7's "never".

**Fix:** a left press starts afresh. A new left press can only follow the previous left release, so a `pressed` still
set at that point belongs to a lost release:

```java
@Override public boolean mouseClicked(MouseButtonEvent event, boolean doubleClick) {
    // A press whose release never reached this screen (a resource reload's loading overlay swallows input) must
    // not act on this press's release.
    if (event.button() == 0) pressed = null;
    return super.mouseClicked(event, doubleClick);
}
```

Optionally also add `pressed = null;` in `init()`, which the loading overlay and a resize call.

**Test:** in the Apps screen part, send `screen.mouseClicked` on a row with no release. Then send `mouseClicked` and
`mouseReleased` at the search box's centre. The screen must still be `AppsScreen`, the cursor empty and `opened`
unchanged. Without the fix the screen becomes the inventory.

## Not findings (checked and fine)

- **A drag that comes back within one stalled frame:** the press, a move of more than 3 px and a return to within
  3 px of the press point, all before a frame handles the movement, reads as a click and opens.
  - `onMove` sees the intermediate positions but hands the screen only the current one.
  - Catching this would need a mixin on the raw moves.
  - At 60 to 144 frames a second it takes a stall plus an exact return.
  - A gesture that ends where it began is as much a click as a drag. Not worth the mixin.
- **A right release after a flick:**
  1. He holds left and right, lets go of left far away (the item is picked up), then lets go of right after the item
     arrived.
  2. The right release lands in the inventory with the flag false and places one item in the slot under the pointer.
  3. Where he lets go, the item stays. Over a slot that is right; outside the panel `keepsOnClick` refuses it.
- **A click right after a flick, before the item arrived:** the inventory's press does `PICKUP` on that slot with an
  empty cursor. The server handles `take` first and then that click, so the item ends in the slot or swaps. This is
  the same as REVIEW-2's "letting go before the item arrived" on the drag path, not new.
- **A GUI-scale change mid-press** (a resize with automatic scale) would compare positions in two scales. This is
  rarer than the nit, and the optional `init()` clear covers it.
- **The test hands the press and the release to the screen directly.** That is what `onButton` does when both come in
  one poll. Going through `holdMouse`, `setCursorPos` and `releaseMouse` would also take the release path only while
  the test window has no focus, so the direct calls are the deterministic choice. The report lists it under "Not
  verified".

SAFE
