VERDICT: SAFE

Review of step 311d at `b38ad4682883ba513e80b0ea3b2f54015527eb3f`, by a fresh Claude Opus 5.5 reviewer. A Codex recheck was started first and produced no verdict: OpenAI's content filter stopped the run with a "possible cybersecurity risk" error.

The pins stop any ordinary rebuild whose code differs from the reviewed build, and they are checked on the exact RPM the stage hands over. They prove less than the record claimed, so the record was corrected. No code change is needed to merge.

## Findings

**SHOULD-FIX (record only, does not block):** the pins do not cover all of the ELF program headers, so "the pins still prove the code that runs" was false.
- Where: `reviews/311-labwc-pointer-lock/PROGRESS.md`, the 311d PLAN-GAP and the final section, and the docstring of `normalized_sha256` in `os/labwc/stage.py`.
- Cause: when `objcopy` removes the sections it recomputes many header fields from the section table, so their original values never reach the hash.
- Measured on copies of the real `/usr/bin/labwc`, none of them run. Each still matched the lock's pin: the interpreter's `p_offset` pointed at padding holding another path, `PT_DYNAMIC` pointed at padding, `PT_GNU_RELRO` turned into `PT_NULL`, `e_phnum` lowered from 13 to 12, changed bytes in executable padding, and bytes appended to the file.
- Run-time proof on a small harmless test program: the same interpreter edit left its normalized hash unchanged, and the program ran under the other interpreter.
- Why this is not real harm in the stage: an accidental build difference cannot change only these fields, because they follow from section addresses that are pinned (the reviewer's reasoning, not tested). A crafted binary needs code running in the `labwc` stage. `rpmbuild` runs there before the check, in the same container, so that code could replace `objcopy` anyway. Every input to that stage is locked by hash.
- Optional hardening if R29 compares binaries outside the build: also hash the ELF header (with `e_shoff` zeroed) and the program header table, and refuse non-zero bytes outside sections.

**KNOWN LIMIT:** padding and appended bytes. On their own these are not real harm. In builds A and B all of these bytes are zero (`labwc` 3202, `labnag` 3734).

**NIT:** the symlink refusal has no test. Removing `binary.is_symlink()` leaves all 109 tests passing. With the real `cpio`, a symlink to `labnag` and a symlink to an outside path were both refused.

**NIT:** a missing `rpm2cpio` raises an uncaught `FileNotFoundError` instead of one `LABWC_REFUSED` line. `cpio` and `objcopy` are launched the same way. The build still stops, and the locked environment includes these tools.

## Answers to the review's questions

1. **Same RPM, real build path:** yes. The file that is checked is the file that is copied out. A refusal fails the `RUN` in `os/Containerfile`, and the final image can only take the RPM from that stage. The check build and the release job both go through `os/ci/check-build.sh`.
2. **Sections:** exactly the three named sections disappear on the real `labwc`. Neither binary imports `dl_iterate_phdr`, `backtrace`, `dladdr` or `dlopen`. Nothing found uses their contents at run time.
3. **Padding:** see the known limit above.
4. **Silent renewal:** not possible. `build` only reads the lock, `resolve` copies `result` unchanged into a candidate file that is only uploaded as evidence, and no workflow commits or pushes.
5. **Unpacking and lock rules:** a truncated RPM, a non-RPM, a missing RPM, a failing `rpm2cpio`, a failing `cpio`, a symlink, a directory, a missing member, non-ELF content and wrong code were all refused. Both real RPMs were accepted. The lock's new rules break no caller.
6. **Tests:** they load the real `os/labwc/stage.py` and use the real `objcopy`. `rpm2cpio` and `cpio` are stand-ins. Of 11 mutants, 9 were caught. The survivors are the symlink check and the `--no-absolute-filenames` flag.

## Checked

The commit, the brief, the known limits, the 311d progress section and the full diff. `test_labwc_stage`: 109 tests pass. The RPMs from `localhost/aresos-labwc:311d-a` and `311d-b` match both pins.

## Could not check

No full image build or hosted workflow was run. The measurements used this machine's `objcopy`, not the locked `binutils-2.46.1` inside the stage, though it reproduced both pins. No crafted `labwc` was executed, by design. `test_aresos_desktop` was not run by the reviewer.
