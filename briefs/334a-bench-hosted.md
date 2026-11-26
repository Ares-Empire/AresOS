# 334a: the bench's hosted pass (test bench, step 1)

**Goal:** the first value from the test bench (`docs/design/TEST-BENCH.md`). A new hosted check mode,
`check_build=bench`, builds the image from the dispatched ref and adds a bench-only layer with a minimal guest agent.
It makes a disposable disk, boots it with no network card, plays one bench script and uploads bounded evidence. After
this, Claude can check a change that needs a new image or a restart on GitHub's runners, one round per dispatch.

Nothing runs on the laptop. Nothing in the shipped image changes.

Model: Codex `gpt-6.2-sol`, effort `xhigh` (the repo's build default; workflow and VM work where a wrong guard costs
a release).

## Read first

- `AGENTS.md` (all of it: the laptop rules, `os/tests` on the laptop, hosted runs, the GitHub API allowance).
- `docs/design/TEST-BENCH.md`:
  - section 3: the hosted route, "Reuse", "Missing", "How the limits are kept", "Release protection", the worked
    example, "Where the VM image comes from", "How a test reaches the desktop without his password";
  - section 6: the `bench` interface, steps, output, evidence and exit codes;
  - section 7: step 1's row, and **"Carried into the step briefs", Step 1**. Those bullets are part of this brief;
  - section 9: Known limits.
- `reviews/334-test-bench/REVIEW-1.md` (blocking 3 and 6), `REVIEW-3.md` (blocking 5), `REVIEW-4.md`, for why step 1
  looks the way it does.
- The code the note cites for this route: `os/ci/check-build.sh`, `os/ci/vm.py`, `os/ci/qmp.py`,
  `os/ci/serial_console.py`, `os/ci/serial_transport.py`, `os/ci/prepare-disk.py`, `os/ci/overlay/checks.py`,
  `os/ci/control/` (the Control pass is the closest model: `control_vm.py`, its `Containerfile`, `CHROME_STEPS`),
  `os/ci/image-checks.sh`, `os/ci/publish.sh`, `os/Containerfile`, `os/.containerignore`, `os/build.sh`,
  `.github/workflows/os-image.yml`.

## In scope

1. **Bench sources under `os/ci/bench/`.** Check that `os/.containerignore`'s `ci/` rule keeps them out of the
   release build context, and that the release `Containerfile`'s assertion still holds.
2. **A bench layer** built on top of the CI-built image in its own build context, with a distinct tag. It is never
   pushed to a registry or pinned.
3. **A minimal guest agent:** a root unit in the guest that uses the existing virtio handshake and acts as `ares` through
   `runuser`. It offers only the verbs this step needs (section 6: `exec`, `shot`, `journal`, `status`, `reboot` and
   `wait`/`expect` as the script runner needs them).
4. **A bench disk config** with no account password; auto-login comes from greetd's `initial_session`. **Boot
   explicitly with no NIC.**
5. **The script runner and the `bench_script` input.** The input must match `reviews/<package>/bench/<name>.json` and
   exist in the dispatched commit. Ship one script for the acceptance below, under `reviews/334a-bench-hosted/bench/`.
6. **`check_build=bench` in `os/ci/check-build.sh` and `os-image.yml`**, as a new option next to the existing
   `check_build` modes.
7. **Evidence:** a bounded set of regular files with a size cap, refused if they hold token-shaped strings. Upload is
   gated on that check, not `always()`. Raw guest output stays out of retained job logs. `run.json` names the
   dispatched head SHA and the script.
8. **Release protection:**
   - a bench dispatch is exclusive with the release, rehearsal and published-image switch inputs;
   - the package 13 publish job refuses `check_build=bench` (its condition near `os-image.yml` line 263 lacks the
     `check_build` exclusion used near line 421);
   - a raw-layer scan of the plain image, with a planted-file case that must fail;
   - the "no bench file" rule covers image and build inputs only, not the scripts under `reviews/`.
9. **Tests** in `os/tests/test_bench_*.py` for the script parser, the evidence checker (oversize, token strings,
   links, unexpected paths), the dispatch-exclusivity logic and the release-layer scan. The hosted checks run them.

## Out of scope

- Anything on the laptop: no VM, container, QEMU or sudo there. The bench's laptop pieces are steps 2 to 10.
- Network levels, stand-ins, `tree`, clicks and typing, the desk and the recorder (steps 2 to 10).
- **B331, the R29 release package** (PR144, `pkg/331-release-29`, `linux-aresos`), rewrites `os-image.yml`: three
  guarded R29 modes, authorization jobs, caps, and a 95-minute checks reservation in `os/ci/rehearsal_guard.py`. Don't
  touch the R29 jobs or `rehearsal_guard.py`. Keep your workflow diff small and local, so a rebase onto B331 stays
  easy. B321's `check_build=deskflow` edits the same two files too. Whichever lands second merges `main` first and
  keeps both modes.

## Acceptance

All on hosted runners, from this branch:

1. A dispatch with the acceptance script passes:
   - it boots with no NIC and the auto-login session is active;
   - an authenticated, read-only request to the real session helper answers (health), with launch credentials kept
     inside the guest;
   - it takes a QMP screenshot;
   - it reboots, then requires a new boot ID and a fresh health check.
2. A dispatch from a commit with a deliberately broken helper **fails at the VM health check**. The broken helper still
   imports and answers `--list`, because `os/ci/image-checks.sh` runs those before the VM boots. Revert that commit
   afterwards.
3. Oversize evidence and a planted token-shaped string are refused before upload (unit tests, plus one negative case
   in the hosted run if cheap).
4. Release protection: the planted bench file in the plain image's raw layers fails the scan. The publish job refuses
   `check_build=bench`. Dispatch exclusivity has tests.
5. `run.json` matches the dispatched head.
6. The repo's normal hosted checks pass: `gh workflow run "OS image" --ref <branch> -f checks_only=true`.

## Rules

- `AGENTS.md` holds. On the laptop, run only the test modules you touch, one at a time
  (`python3 -m unittest discover -s os/tests -p 'test_bench_<name>.py'`). Never run the module `test_owner_update`,
  never use sudo, and never run `rpm-ostree`, `bootc`, `ostree` or the owner tools.
- The VM pass runs only on hosted runners. Wait for a run with `gh run watch <id> --exit-status --interval 60`. Use
  **at most 8 bench dispatches** for this step. If `gh` answers HTTP 403, wait for the reset and try once.
- Write "the owner", never a person's name. Repo-relative paths in everything committed.
- Commit and push on `pkg/334a-bench-hosted`, open a pull request into `main`, and never merge. Name the model in
  commit trailers.
- Keep `reviews/334a-bench-hosted/PROGRESS.md` up to date while you work (done, left, what the code doesn't show).
- At the end, write `reviews/334a-bench-hosted/REPORT.md` and delete `PROGRESS.md`. The report covers what was
  built, the run IDs (passing and failing), evidence size, time per dispatch, and Known limits.
