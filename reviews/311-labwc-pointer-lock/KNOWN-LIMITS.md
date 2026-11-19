# 311: known limits after review 1

The lead sorted review 1's findings by the safety bar: real harm gets fixed, low-harm edge cases are recorded here. The blocking finding (the build's Fedora digest isn't bound to the lock) is fixed by brief 311c.

## Stale layer focus (review 1, should-fix)

**What:** labwc 0.9.6 keeps `focused_layer` set when focus moves from an on-demand layer surface to a normal window. A layer client that asks for a pointer constraint after losing focus could then still get it, and the pointer would be held over that window.

**Why it stays:** it needs a layer client with on-demand keyboard focus that also asks for a pointer constraint. AresOS has no such client. The sharing backend uses exclusive keyboard focus, and `seat_focus` does not move focus away from an exclusive layer. The same check is in upstream 0.20.3, and brief 311 keeps upstream's logic.

**Carry into the portal backend package:** its capture surface must use exclusive keyboard interactivity.

## Layer surfaces on a display that doesn't start at 0,0 (review 1, known limit)

**What:** the patch uses coordinates relative to the output's scene tree, as upstream does. On a display that starts at x=1920, a cursor hint given on release can put the cursor on the wrong display. The pointer stays usable.

**Why it stays:** it is inherited from upstream and causes no lasting harm. The laptop screen (`eDP-1`) sits at 0,0.

**Carry into the real-laptop test:** check where the cursor lands after coming back from the Mac, with the external monitor connected and without it.

## Test proofs (review 1, nits)

- `install-proof.sh`'s guard 2 proof accepts any exit status 1, so a malformed fixture could look like a fired guard.
- The guard 3 and 4 tests run the real Python body, but would not notice if the shell line that starts it were removed.

Both only weaken a proof of checks that review 1 confirmed are wired into the build.

## The digest check reads physical lines (review 2, known limit)

**What:** 311c's check could be fooled by a locked `FROM` line hidden inside a continued `RUN` comment, together with a real `FROM` that has a different digest and puts `AS labwc` on the next line.

**Why it stays:** it takes two deliberate, unusual edits to a reviewed file. A plain digest change or a continued `FROM` on its own is refused.

## The ignore-file wiring test (review 2, nit)

The wiring test would not notice a `Containerfile` rule padded with spaces in `os/.containerignore`. The build would then stop at the new `COPY` line, so nothing unsafe gets through.
