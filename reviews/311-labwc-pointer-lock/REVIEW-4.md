VERDICT: SAFE

Review of step 311e at `2f387a0f1214ce0464d2dc77063596588da995b1`, by a fresh Claude Opus 5.5 reviewer. It covers `os/labwc/loaded_image.py`, its wiring in `os/labwc/stage.py` and its tests.

No blocking or should-fix findings. A file that matches the pin can differ from the reviewed binary only in the two zeroed ranges and in bytes after `end`.

## Findings

**NIT 1:** the program-header-table half of the check at `os/labwc/loaded_image.py:67` has no test of its own. The fixture sets `end` to 32, so the ELF-header half fires first. The real code refuses such a file, and `e_phoff` is in the hash, so a moved table cannot match the pin.

**NIT 2:** two bounds are tested only far from their edge (`os/labwc/loaded_image.py:56` and `:63`). A table end one entry short and a `p_offset + p_filesz` that wraps at 2^64 survive as mutants. The real code refused both when measured.

**NIT 3:** the note name test would not notice a prefix match (`os/labwc/loaded_image.py:86`). The real comparison is exact.

**NIT 4:** the renewal text test is loose (`os/labwc/stage.py:48`). The current text is correct.

**KNOWN LIMIT, confirmed:** the 20-byte build-id descriptor is not real harm. The free range is exactly `0x328..0x33b` in both binaries. The note's header is pinned, so the range cannot grow or move. No direct branch, RIP-relative reference, relocation or dynamic symbol points into it, and the entry point and all code are pinned. The worst realistic effects are a wrong debug-symbol lookup or crash label, and 20 chosen bytes that help only someone already exploiting a memory bug in labwc.

## Answers to the review's questions

1. **Definition and refusals:** `loaded_sha256` matches the brief, including every refusal. 30,000 fuzzed files raised no exception other than `LoadedImageRefused`.
2. **Can a pin-matching file differ?** No, apart from the two zeroed ranges and bytes after `end`. A moved or enlarged descriptor needs a second build-id note header, and the real image holds exactly one. The reviewer edited every byte of `labnag` three ways and 5,843 positions of `labwc`. Only the 8 `e_shoff` bytes and the 20 descriptor bytes kept the pin. Malformed notes, duplicate `PT_NOTE` entries, overlapping notes and 64-bit wraps were each refused or changed the hash.
3. **Descriptor:** a known limit, as above.
4. **Wiring:** the check runs on the same RPM the stage copies to `/out`. A mismatch, a refused file or a missing module each ends in one `LABWC_REFUSED` line and stops the build. Only `build` loads the module. The image's `COPY` layer contains a `__pycache__`, so compiling from source is the right choice.
5. **Renewal:** no build or `check_build=resolve` run can renew a pin. The stricter lock rules break no caller.
6. **Tests:** they load the real function and real stage code, and one runs `stage.py` under `python3 -I`. Of 66 mutants, 61 were caught, including every removal of the stage check. The 5 survivors are the nits above.

## Checked

`os/` is unchanged since `ffacc288`, the commit the recorded build used. `test_labwc_stage`: 126 tests pass. The RPMs from `311d-a`, `311d-b` and `311e` all give the pinned loaded and normalized hashes, and the real `require_pinned_binaries` accepts all three. On real `labwc` copies, it refused a moved `PT_INTERP`, `PT_GNU_RELRO` made `PT_NULL`, a removed `PT_NOTE`, and a wrong loaded pin on the real RPM.

## Could not check

No image was built, so the `--no-cache` build result is the builder's record. The final `aresos` stage and a real `check_build=resolve` run were not exercised. No edited binary was run. That the kernel ignores `e_shoff` and zeroes the bytes after `end` in the last mapped page is reasoning from how it loads ELF files. The search for references to the descriptor is static, so it cannot rule out a computed jump. `test_aresos_desktop` and the Ubuntu test run were not repeated by the reviewer.
