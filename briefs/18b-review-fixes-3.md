# 18b review fixes, round 3: compare the whole mount tree, set the weakening sandbox keys explicitly

**Goal:** fix the one blocking finding in `reviews/18b-control-boundary/REVIEW-3.md`, and make the managed draft set
every sandbox key it now leaves to `--setting-sources ''`, on the same branch. Small and exact: nothing else changes.

Read first: `briefs/18b-control-boundary.md` (still the scope), `briefs/18b-review-fixes-2.md`,
`reviews/18b-control-boundary/REVIEW-3.md`, the current `REPORT.md`, `control/boundary/boundary_assertions.py`,
`control/boundary/native.py` and `control/settings/`.

## 1. REVIEW-3 finding 1 (blocking): compare the full mount tree

The comparison drops mount IDs and parent IDs and collapses mounts by destination, so a sandbox whose tree differs
(for example a read-only mount hidden under a covered parent, leaving the visible mount writable) still compares equal.

- Compare the full mount tree from `/proc/<pid>/mountinfo`: mount ID and parent ID (as tree structure), root, mount
  point, mount options, propagation fields, filesystem type, source and super options. Normalize only what is
  session-specific (mount ID numbering, session UUIDs, proxy socket nonces), by mapping IDs through the tree, not by
  dropping them.
- Classify each policy path (hidden / read-only / writable) through the effective mount: the last mount on that path
  that is reachable through its parent chain, not the first or last line that names it.
- Regression tests that must fail: an approved tree that differs from the baseline only in tree shape (the REVIEW-3
  mutation: the read-only work mount re-parented under a covered mount, every line otherwise identical); a policy
  path whose read-only mount is covered by a writable one. Keep the existing seven tests passing.
- Rerun the comparison on the live native runs in CI (approved hostile run against the unapproved baseline, and native
  against standalone for the policy paths). It must still pass, or the report says exactly what differs.

## 2. Set the weakening sandbox keys explicitly

The draft relies on `--setting-sources ''` and on the managed `sandbox.filesystem` lock for keys it doesn't set
(`sandbox.filesystem.disabled`, `sandbox.enableWeakerNetworkIsolation`, and others). Set them in
`control/settings/managed-settings.draft.json` instead, so the managed file alone holds the line.

- Go through every `sandbox.*` key in Anthropic's settings reference and sandboxing page (Claude Code 2.1.319) that the
  draft leaves unset. Where another value would weaken the sandbox (for example `filesystem.disabled`,
  `enableWeakerNetworkIsolation`, `allowNestedUserNamespaces`, proxy ports), set it explicitly to its safe value.
- If a key's safe value differs from its default, or setting it would change what the existing tests show, set it
  only if the tests still pass for the right reason, and otherwise leave it out and say why in the comments file.
  Keys that only apply to macOS stay out, with one line saying so.
- Add a row per key to `managed-settings.draft.comments.md`: purpose, doc URL, version, how it was checked.
- Show in CI that native Claude Code still loads the managed file with these keys (the existing MCP-exclusivity,
  sideload, bypass-clamp and source checks still pass, so an unknown or invalid key hasn't made it drop the file), and
  that the approved native hostile run still blocks all routes in both modes with the same observers.

## Report

Update `REPORT.md` in place: a short "Review fixes, round 3" section mapping REVIEW-3 finding 1 and item 2 to changes
and evidence; update answer line 3 and the settings table as the results require. Keep the PLAN-GAP and
JUDGMENT-CALL list as it is (the design lead takes those forward); add to it only if this round finds something new.
Every claim stays marked **run**, **read** or **assumed**. Name the run IDs of the last implementation commit; the
report commit itself must also pass twice. Don't edit `REVIEW*.md`.

## Rules for this run

- `AGENTS.md` hard rules 1, 4, 5 and 6 apply; its Minecraft, Gradle and Windows parts do not (this runs on the
  owner's MacBook; everything runs on GitHub's Linux runners and in containers).
- Work only in this worktree, on branch `pkg/18b-control-boundary`. Commit in small steps and push; draft PR #5
  already exists, don't open another. Never merge, never push to `main`, never force-push.
- The pre-push privacy check runs on every push. Never use `--no-verify`; fix what it finds.
- No real model, no sign-in, no real account, no network beyond the runner's package downloads: the scripted stub is a
  fixed test double, and the two exact-command test allow rules stand for owner approval, as in round 2.
- Same scope as the brief: `control/boundary/`, `control/settings/`, `.github/workflows/control-boundary.yml`,
  `reviews/18b-control-boundary/` only.
- Keep it to about 6 more workflow runs. The workflow must still finish within its 30-minute cap.
- Add `Codex-Model: gpt-6.1-sol (xhigh)` as a trailer to your commits.

**If unsure:** take the option that keeps Claude inside the sandbox, and say so in the report.

**Model:** `gpt-6.1-sol`, xhigh.
