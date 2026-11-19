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

## What the normalized pins prove (review 3; the header gap is closed by 311e)

**What:** a normalized match means the binary's sections are the same, not that the whole file is. `objcopy` rewrites the file from its sections and recomputes program header fields, so these edits keep the normalized hash: moving the interpreter's offset, turning `PT_GNU_RELRO` into `PT_NULL`, lowering `e_phnum`, changing padding, and appending bytes. Review 3 showed on a small test program that such an edit can make it run under another interpreter. The lead reproduced the hash results on a copy of `labwc`; a changed code byte did change the hash.

**Closed by the loaded pins (311e):** `result.loaded_sha256` pins the bytes the loader maps: the file from offset 0 to `end`, the largest `p_offset+p_filesz`, as they are on disk, with only `e_shoff` and the build-id descriptor set to zero (`os/labwc/loaded_image.py`). The `labwc` stage refuses a binary whose loaded hash differs, or a file the function refuses. On copies of the real `labwc`, the interpreter, `PT_GNU_RELRO`, `e_phnum` and padding edits each keep the normalized hash and change the loaded hash (`PROGRESS.md`, 311e).

**What stays open:**
- Bytes after `end`, which the loader never reads: `.gnu_debuglink`, `.gnu_debugdata`, the section headers and anything appended to the file. A change there keeps both hashes.
- The two zeroed ranges, because they differ between builds of the same code. `e_shoff` is not used by the loader. The 20-byte build-id descriptor is mapped, in the read-and-execute segment of both binaries, and neither pin covers it. The entry point and every other mapped byte are pinned, so changing the descriptor alone gives pinned code nothing new to run (reasoning, not tested).

**Carry into R29's rule:** use `loaded_sha256` from `os/labwc/loaded_image.py` with the two hashes in `PROGRESS.md`'s final section. A normalized match alone is the weaker proof.

## Refusal paths (review 3, nits)

- No test covers the symlink refusal in `require_pinned_binaries`. The behaviour was checked by hand with the real `cpio`.
- A missing `rpm2cpio`, `cpio` or `objcopy` stops the build with a Python error instead of one `LABWC_REFUSED` line. The locked build environment includes all three.
