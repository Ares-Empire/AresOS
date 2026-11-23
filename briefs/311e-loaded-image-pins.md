# 311e: pin the bytes the loader maps

**Goal:** a labwc or labnag binary with a different interpreter, different program headers or different mapped bytes can't pass the build's pins. Briefs 311, 311b, 311c and 311d stay in force.

**Why:** review 3 showed that the normalized hash from 311d keeps its value when a program header is edited, for example when `PT_INTERP` is moved to another path. `linux-aresos` decided on 2026-11-19 to pin the loaded image as well, and R29's release rule will use the same function.

## In scope

1. **One function, `loaded_sha256(path)`, in a new file `os/labwc/loaded_image.py`.** Standard library only, and it reads program headers, never section headers. It sits beside `stage.py` because `os/.containerignore` keeps `os/ci/` out of every image stage. Running the file with a path prints the hash, so R29's rule can call it.

   It refuses, with one exception type, unless:
   - the file is ELF64, little-endian and x86-64;
   - `e_phentsize` is 56, `e_phnum` is between 1 and 0xfffe, and the program header table lies inside the file;
   - every program header's `[p_offset, p_offset+p_filesz)` lies inside the file;
   - the ELF header and the program header table lie inside `[0, end)`, where `end` is the largest `p_offset+p_filesz`;
   - the `PT_NOTE` segments hold exactly one `NT_GNU_BUILD_ID` note named `GNU`. Walk the notes with each segment's alignment (4 or 8), and refuse a note that overruns its segment.

   **The loaded image** is the bytes `[0, end)` exactly as they are in the file, with two ranges set to zero: the 8-byte `e_shoff` at offset 0x28, and that note's descriptor bytes. The result is the SHA-256 of that image.

   Bytes between segments stay in the hash. They are mapped with the page they share, and they are identical and zero in the real builds.

2. **The pins:** `result.loaded_sha256` in `os/labwc/labwc.lock.json` holds the hash of `/usr/bin/labwc` and `/usr/bin/labnag`, beside `result.normalized_sha256`, which stays as it is. `validate_lock` requires both.

3. **The stage refuses:** `require_pinned_binaries` also computes both loaded hashes from the RPM's own payload, prints them as `LABWC_LOADED <path> <hash>`, and stops with one `LABWC_REFUSED` line on a mismatch or on a file the function refuses. `stage.py` runs under `python3 -I`, so the script's folder isn't on the import path: load the module from its explicit path next to `stage.py`.

4. **`check_build=resolve`:** the renewal text covers both kinds of pin, and neither is ever renewed by a build.

5. **Tests** in `os/tests/test_labwc_stage.py`, which load the real file:
   - these each change the hash or are refused: a changed code byte, `PT_INTERP`'s offset moved, `PT_GNU_RELRO` turned into `PT_NULL`, a lower `e_phnum`, an interpreter path appended to the file and pointed at, a changed byte between segments;
   - these leave the hash unchanged: another build-id descriptor, another `e_shoff`, other `.gnu_debuglink` or `.gnu_debugdata` contents after `end`;
   - each refusal in item 1 fires: wrong class, byte order or machine, a range outside the file, no build-id note, two build-id notes, a note that overruns its segment;
   - the stage's refusal fires on a wrong loaded pin.

6. **The record:** update "What the normalized pins prove" in `reviews/311-labwc-pointer-lock/KNOWN-LIMITS.md` to say the loaded pins close the header gap, and that what stays open is bytes after `end`, which the loader never reads. Add both loaded hashes and the function's path to `PROGRESS.md`'s final section for `linux-aresos`.

## Out of scope

R29's release rule, which `linux-aresos` writes. Changing the normalized pins. Everything else in `KNOWN-LIMITS.md`.

## Acceptance

1. **Both real builds agree:** on the RPMs in `localhost/aresos-labwc:311d-a` and `311d-b`, the function gives the same hash for each binary. The lead's throwaway prototype gave `92b42d5f5174a91adab883a3f6196500483ac08e37adff7928568284d70422f2` for `/usr/bin/labwc` and `789da84fb23e482434c84e300d1a95c90f5cec5ffc1b9a156d2f6b5cdcff47d2` for `/usr/bin/labnag`. If yours differ, stop and report which bytes differ.
2. One `podman build --no-cache --target labwc` from the real files passes and prints the pinned values. Record the command and output.
3. A wrong loaded pin in a scratch export stops that build with the new line. Record the command and output.
4. `test_labwc_stage` and `test_aresos_desktop` pass, and `test_labwc_stage` also passes in an `ubuntu:24.04` container.
5. `rebind.py pending "<note>"` is run again if a bound file changed.

Brief 311's limits all hold: no hosted workflows, no merge, no push to `main`, nothing on the running laptop.

**Model:** Claude Opus 5.5: a small, exact change with a written definition.
