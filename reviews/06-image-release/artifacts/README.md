# Original package 06 and 06b archives

Source run: [39796347427](https://github.com/carlsenares/AresOS/actions/runs/39796347427),
commit `01aae1e38ec11356677f526692783c14b89a1d4d`.

- `final-image-evidence.zip`: successful image job, including two fresh VM passes.
- `final-switch-evidence.zip`: failed stock reboot after private verification/pull/staging.
- `final-workflow-logs.zip`: original GitHub workflow log archive, downloaded after completion.

The two evidence ZIP hashes match GitHub's `digest` values in the adjacent
`final-image-metadata.json` and `final-switch-metadata.json`. All three downloaded
archive hashes and byte sizes are recorded in [archive-hashes.json](archive-hashes.json).
GitHub provides no digest in the workflow-log download response; that entry is
our computed download hash. Expanded log text was scanned before retaining the
archives. Display copies outside this directory normalize trailing whitespace
and line endings; these ZIPs preserve the original bytes.

No disk, credential file, raw authentication transcript, builder configuration
or binary journal is present. The switch archive repeats the earlier successful
image evidence; its own switch result is failed. See [REPORT.md](../REPORT.md).

## 06b follow-up

Harness source: `cc341991bb4524dc37154f80f4256d1aff0a3b24`.

- `06b-preflight-evidence.zip`, [39810919917](https://github.com/carlsenares/AresOS/actions/runs/39810919917): successful 52-test checks-only preflight inputs.
- `06b-switch-1-evidence.zip`, [39811047831](https://github.com/carlsenares/AresOS/actions/runs/39811047831): failed switch qualification. Boot into the published image passed, then Homebrew remained executable by `ares`; tty3 recovery and rollback were not reached.
- `06b-switch-1-workflow-logs.zip`: original GitHub log archive for that failed run.

The adjacent `06b-*-metadata.json` files record GitHub's artifact digests, sizes
and expiry dates; both evidence ZIP hashes match. The log ZIP hash is computed
locally because that endpoint provides none. [archive-hashes.json](archive-hashes.json)
includes all three. The expanded contents/logs were scanned before committing.
The switch ZIP repeats the original image-job evidence, not a passing rollback.
See the [06b report](../REPORT.md#06b-switch-qualification-2026-10-22).

## 06c follow-up

Image source: `5578ab21b880091f26bfdc2eda22dd4f304a602b`.
Resumed harness source: `1d4a7dec12430b67ff0a53f38ba280c8ae8f7414`.

- `06c-preflight-failed-1-workflow-logs.zip`, run 39818147832: failed native fixture ancestry checks; original pre-pause archive retained.
- `06c-preflight-failed-2-workflow-logs.zip`, run 39818274310: failed named-ACL fixture checks; original pre-pause archive retained.
- `06c-preflight-preflight-evidence.zip` and `06c-preflight-workflow-logs.zip`, run 39818451208: successful 55-test preflight. Original pre-pause archives retained.
- `06c-full-1-image-evidence.zip`, run 39818554327: successful image build, two fresh VMs, private publication and signature.
- `06c-full-1-switch-evidence.zip` and `06c-full-1-workflow-logs.zip`, same run: successful switched policy and inherited Homebrew restrictions, followed by the failed TTY observer (`tcgetattr` EIO). No recovery authentication or rollback result.
- `06c-tty-preflight-preflight-evidence.zip` and `06c-tty-preflight-workflow-logs.zip`, run 39832900483: successful 61-test preflight including six TTY regressions.
- `06c-full-2-switch-evidence.zip` and `06c-full-2-workflow-logs.zip`, run 39833127717: successful unchanged-image switch, full policy, inherited Homebrew checks, real tty3 administrator password/sudo, partition equality and exact-stock rollback. The rollback PNG is an early black frame; boot/account/display-manager/Homebrew assertions establish stock boot.

Adjacent metadata records GitHub's artifact SHA-256 values, sizes and expiry;
every evidence ZIP matches. Workflow-log archives have locally computed hashes
because that endpoint supplies no digest. All ZIP hashes, including the
pre-pause originals, appear in [archive-hashes.json](archive-hashes.json).
[ci-06c.json](../ci-06c.json) preserves run/job/step metadata. Text was scanned for
unmasked password hashes and GitHub token forms; no disk, credential, builder
configuration, raw authentication transcript or binary journal was retained.
Expanded text display copies normalize whitespace; raw manifest JSON and ZIP
bytes are preserved. See the [06c report](../REPORT.md#06c-inherited-homebrew-qualification-2026-10-22).

06d evidence (acceptance **not met**):

- `06d-preflight-{2,3,4,5,6}-release-inputs.zip`: successful checks-only inputs. Preflight 1 failed before producing an artifact. Preflight 6 is the final 82-test result, including the actual Plasma Login Manager inventory fixture.
- `06d-full-1-os-switch-evidence.zip`: failed stock-greeter observer, before switch; the saved stock framebuffer is rendered, exposing the observer's SDDM assumption.
- `06d-full-2-os-switch-evidence.zip`: partial tooling/disk-preparation evidence from the cancelled second run; no guest rehearsal occurred.

All seven new ZIPs match GitHub's artifact digest and appear in
[archive-hashes.json](archive-hashes.json). Original workflow bytes are retained
in `06d-*-workflow-raw.txt.gz`, with locally computed hashes in the same index;
`../logs/06d-*-workflow.txt` contains whitespace-normalized display copies.
Expanded guest text is also normalized; original bytes remain in the untouched
evidence ZIPs. Screenshots are unchanged. [ci-06d.json](../ci-06d.json) summarizes the eight
run records and budget. Full run 1 failed and full run 2 was cancelled; both
allowances are counted as consumed. There is no successful 06d VM result or
new rendered rollback screenshot. See the
[06d report](../REPORT.md#06d-review-fixes-2026-10-22).
