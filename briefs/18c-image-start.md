# 18c-image-start: build Part A and B2 now, on main without the Chrome tool

**Goal:** build Part A (the image change) and B2 (the VM test) of `briefs/18c-image-test.md` on today's `main`.
That brief stays the task; this note records what has changed since it was written and what this run covers.
Where the two differ, this note wins.

## The lead's decision (2026-11-14)

The brief's "Order" says to stop if the Chrome tool (PR #27) isn't on `main` and lets the lead decide. Decision:
**build now, without it.** Package 23 is on `main` (`3bff81b6`), B1 is on `main` (PR #43), and PR #27 is planned
for 2026-11-16. On today's `main` the service has no Chrome adapter and starts without Chrome's files, so the image
part can be built and proven as it is. What Chrome adds comes afterwards as a small follow-up on this branch:
its startup files (`build-id.json`, `qualification.json`), the socket modes read from the merged `daemon.py`, and
one more `check_build=control` run. Write Part A so that follow-up adds files and assertions, not structure.

This branch is not merged before PR #27 is on `main` and that follow-up is done, and not before the owner has said
yes to a release carrying Control (agreed change 10). So: push, open a draft PR, never merge.

## What is already on main (don't build it again)

- The unit's network lines and its pin test (`control/tests/test_unit.py`), and B1: `control/boundary/`
  `interactive_driver.py`, `interactive_model.py`, `interactive_suite.py` and the 17 container cases.
- `reviews/18c-image-test/REPORT.md` from that run. Read its section "For the builder of Part A and B2" first: how
  to call the driver and the model double, how the skip-permissions warning is accepted on the pinned Claude Code,
  and what the interactive prompts do (a "No" interrupts the turn; a `PermissionRequest` hook may flash a prompt and
  approve without an answer; normal mode must be selected explicitly).
- Append to that report; don't replace it.

## What package 23 changed under `os/` (from `linux-aresos`, 2026-11-13; check each in the tree)

- `os/Containerfile` has a `source` stage that fetches the build commit and keeps `mod/`. Control comes in through
  that same stage (agreed change 1): keep `control/` there too.
- `os/build.sh` has a build kind (`ARESOS_BUILD_KIND`, `release` by default); only the read-only `check-build` job
  builds a throwaway.
- `os/ci/check-build.sh`, `check-image.sh` and `check-resolve.sh` changed. The resolve now renews a vanished Fedora
  pin by name; the one extra `gh` step of the brief goes into that version.
- The image records what it carries under `/usr/share/aresos/manifest/`; the mod's record `aresos-mod.json` is the
  model for `control.json`.
- **A release image is checked against the reviewed locks exactly** (`check-image.sh`). Everything Control adds must
  be in a lock or in a manifest the release diff can explain: the vendored wheels, `gh`, every installed file.
- Run 43490417132 is the reference for a green `check_build=build` with VM on this `main`.

## Rules added since the brief

- **A vanished pin is not yours to work around.** If a check build stops on a pin that has nothing to do with this
  branch (a Fedora package, Java, Prism metadata), stop that step, write one line for `linux-aresos` into your
  report and your final message, and go on with what doesn't need the build. It renews pins on `main`.
- **`.github/workflows/os-image.yml`:** `linux-aresos` has been told that this run adds the `control` choice to the
  `check-build` job. Keep it purely additive, change that file last, and change it in one commit of its own.
- **Watching runs:** `gh run watch <id> --exit-status --interval 60` or longer, never the default (`AGENTS.md`).
  For a 50-minute image build use `--interval 300`. Check `gh api rate_limit` before a burst of `gh` calls.
- **Reviews:** Codex's shared allowance is used up until 2026-11-17 10:53. The reviews of this part are a fresh
  Claude agent on Opus (package) and on Fable 5.2 (security: a service, a system user and the password store in the
  image), or Codex from Tuesday. That is the lead's job, not yours.
- **The owner chose the folders:** `Downloads` and `Documents` (board #203).

## Done for this run

- Part A as amended by "Agreed with `linux-aresos` on 2026-11-13" in the brief (all sixteen changes), except what
  only exists with Chrome.
- B2: every check of the brief except the Chrome-dependent lines, with its PASS line and evidence;
  `check_build=build` green once and `check_build=control` green twice on the final head.
- The report: Part A and B2 sections in the brief's format, the measured idle footprint of the service, the
  ordinary-session result with the service stopped and failed (the numbers the lead takes to the owner), the
  JUDGMENT-CALLs, what the Chrome follow-up has to add, and where the rehearsal's check actions live.
- A draft PR against `main`. Stop there.

## Rules for this run

You are on AresOS itself (the owner's laptop, user `ares`). No containers, virtual machines or root locally, and no
heavy suites: quick static and unit tests only; images, containers and VMs run on GitHub's runners. `AGENTS.md`'s
hard rules 1, 4, 5, 6 and 7 apply. Commit in small steps with a model trailer (`Claude-Model: opus-5.5`), push your
branch, never merge, never push to `main`, never force-push, never `--no-verify`. The repo is public: no personal
data, no real mail addresses or provider names, no secrets.

**Model:** a Claude agent on Opus 5.5, as the brief says; the lead moves it to Fable 5.2 if the VM work resists.
