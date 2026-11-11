# 27: finish the rehearsal (after the Claude reset)

Follow-up to `briefs/27-first-update-release.md`. **Builder: a fresh Claude agent (Opus 5.5).** Don't resume the old one: its context is about 1M tokens. Read the brief, then `reviews/27-first-update-release/REPORT-draft.md` (the previous builder's draft), STATE.md's package 27 lines, and the run evidence below.

## Where it stands (branch `pkg/27-first-update-release`, head `e3a67619`)

- **Release 27 is published privately:** `ghcr.io/ares-empire/aresos@sha256:5fad242fceac7244563913eed96cd72dfcd300fec5e458cdb2ba81bce00d944c`, run 42842793096. It is keyless-signed, and the image diff shows 0 unexplained of 915 changed paths.
- The records, the tools bundle (fingerprint `daa31228a011fb059643d2884199ba95b7dd8a0b9002429f64641e7e89036da5`) and the pins are on the branch.
- **`at update` works** (rehearsal run 4, 42974982988):
  - On R13 it staged the signed exact release, keeping R13 as rollback. `at title` and `at reboot` followed, and R27 booted.
  - Every protected-disk audit through the R27 boot was unchanged.
  - The finalizer unmask is JUDGMENT-CALL 11; the owner accepted it on board #175.
- **Run 4 then failed in the harness**, at the first console login on R27 (`release-27-login-fast-init-0`): "Unverified login/getty version" from `os/ci/owner_login.py:148`.
  - The login observer pins util-linux 2.41.5, but R27 ships 2.41.6 (package 21's JUDGMENT-CALL 4).
  - The observer relies on three behaviours: login.c's 60 s default timeout (`owner_login.py:32`), agetty handling CTRL-U itself (`:60`, `:63`), and agetty's CTRL-D exit without authenticating (`:266`).

## Do

1. **Compare upstream util-linux v2.41.5 with v2.41.6** for `login-utils/login.c` and `term-utils/agetty.c`. Confirm the three behaviours are unchanged; record the comparison (commit range, files, conclusion) in the report. If any behaviour changed, stop and report.
2. **Let the observer accept exactly 2.41.5 and 2.41.6**, nothing wider, with a test that pins both and refuses a third.
3. Search the harness for other pins on package versions that package 21 changed (its 29 RPM changes, listed in the image diff evidence). The aim is a run 5 that doesn't stop on the next one. Add them to the same test.
4. Raise the guard's update cap from 5 to 6 (every dispatch counts). Regenerate the pending list and run the host walk, then the focused WSL set. Push.
5. Dispatch **rehearsal run 5**, with one blocking `gh run watch`.
6. **After it passes:**
   - run `rebind.py record` (source-bindings, the pending list emptied);
   - mark the INSTALL-STATUS update-route gate PASSED with the run links;
   - run the `-B` WSL suite and the checks-only run;
   - write the final `REPORT.md` (from the draft, plus rows for runs 42973044866, 42974982988 and run 5);
   - mark PR #35 ready.
7. If run 5 fails inside the walk on something new, stop and report with the step and its evidence.

## Rules

- WSL: one suite at a time (`pgrep` first, `setsid`, `pkg27-` names, remove clones). C: has plenty of space again, but keep evidence downloads in memory or committed.
- Report as plain messages at push, at dispatch, at the result, and when a decision is needed. Use one blocking wait per CI run.
- `AGENTS.md` applies: never merge, never push to `main`, never `--no-verify`, never force-push. Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- After PR #35 is ready, the integrator runs the Codex review (gpt-6-astra high), merges, and guides the owner through `at update` and `sudo passwd ares` on the laptop.
