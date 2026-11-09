# Stage 1 source review

**Final result: SAFE** for `0caf753626c24e58141a52c5e9ed7d26ed6a5ddc`. Every Control workflow passed twice on that source; all ten Mail jobs finished within 45 minutes (maximum 28m 48s). [REPORT.md](REPORT.md) records the exact run IDs, outputs and limits. The snapshots below preserve the review findings and their resolutions; their pending-test statements describe those earlier review points.

**Read:** fresh `gpt-6.1-sol` high review, as required by the brief. Reviewers were read-only. The preliminary review requested changes; those findings were fixed before this result.

Reviewed source: `d43a583e1cbbe4893c013da95f5d8572090f8a9c`, followed by the small pre-pinning delta (transcript deep copies, exact grouped ledger storage/index, special-role clean-proof guard and Markdown cleanup).

**Result: SAFE for that source scope.** The reviewer explicitly reserved final strict ledger pinning and suite-scoped completeness for another pass.

The review fixes included independent raw evidence instead of production-selected warning outcomes; binding each command to its current attempt; checking every public view and its own continuation; capturing immediate crash bytes before any owner read or orderly close; full metadata and location comparisons; independent proof before a clean result starts a new occurrence epoch; historical-context isolation; wrong mutation kinds under an approval; recursive archive validation; and startup handling of unprepared fences.

**Run:** reviewer ran 31 oracle self-tests on `d43a583e` (`OK`) and a wrong-command probe, then 34 self-tests (`OK`) plus strict-gap probes on the small delta. The probes confirmed unexpected passes, changed failures, omitted views and unlisted cases all fail. The reviewer found the matrix retained every required row, flow and mode.

The final pinned-ledger review is recorded below.

**Read — runtime follow-up:** Linux discovery at `d43a583e` timed out in shards 0/1. The reviewer then reviewed `5cb3ac64`'s exact-gap index and scheduling: all shards discover clean boundaries for every flow, primary fault numbers have unique owners, and each primary retains its persistent, cleanup and crash cases. The ledger uses the same ownership predicate. Result: **SAFE** for that delta.

**Run — follow-up:** 35 oracle self-tests and the scheduler property test passed. The reviewer's direct sweep-module import lacked local `jsonschema`; the isolated Linux CI remains the full execution check.

**Read — worker scheduling and legacy follow-up:** the reviewer found `78085f77` and the worker-scheduling delta **SAFE**. Every primary belongs to one shard/worker pair with all modes and cleanup/crash cases; old review23/24 sweeps stay in the parent. Fresh Python processes isolate global fault hooks. Every child exit affects the job result, and leftover children are terminated.

**Run:** reviewer ran 36 oracle self-tests (`OK`), including a real child exiting 1 to prove failure propagation, and the isolated shard/worker ownership test (`OK`). The legacy new-reservation/cancellation cases add positive coverage and no expected failures.

**Read — local mutation audit:** a focused follow-up found two P1 oracle blind spots: local testapp deletion could remove an extra item or run before context without detection, and folder review could erase historical protected roots. Both were corrected in test code before ledger pinning. Local events are replayed against preceding committed rows and scripted approvals/arguments; separate receiver configuration is recorded before its effect.

**Result: SAFE** for the corrected local-mutation source atop `fd9af47d`. The reviewer confirmed the original probes now fail, exact historical/previous/current protected roots are checked with same-call delimiter evidence, and all earlier local findings are resolved. **Run:** 42 oracle self-tests passed (`OK`). Final strict ledger review remains separate.

**Read — public response schema follow-up:** completed `fd9af47d` job logs exposed persistent-exhaustion testapp status replies that violate their advertised schema (missing evidence, extra evidence_error). The new reader retains the existing validator and records only its exact ValidationError as assertion-specific defects before continuing against the actual reply. It does not catch unrelated validation, transport or assertion failures.

**Result: SAFE** for this reader delta atop `e02a60eb`. **Run:** reviewer ran 44 oracle self-tests (`OK`) and diff checks. The reviewer's direct Mac focused run lacked the installed Linux boundary and exited 139 during teardown; it is not Linux verification. The author's shimmed focused run passed seven tests and reproduced exactly the two schema defects plus a quiet restored response. Authoritative Linux verification remains required.

## Final stage-1 artifact review

**Result: SAFE** at `10accdf120f37db8a8fda2dc22c722b1470999f1`, from the fresh sol high reviewer. All previously reported findings are resolved. This approves the stage-1 harness and ledger, not production gap closure.

**Run:** all 675,775 keys exactly match the harvested data and format-2 grouping round-trips without loss. Row/stage tags and suite ownership are valid; every primary fault has one shard/worker owner and shared clean keys belong to every worker. Strict probes reject unexpected passes, changed failures, omitted views and unlisted failures. Every entry point is strict and enforces its complete scope. The reviewer ran all 44 self-tests (`OK`) and diff checks.

**Read:** final coverage retains M01–M14, C01–C05 and every required flow and mode. Both complete strict Linux repetitions remain required; their results are recorded in REPORT.md after completion.

## Final calendar repeatability correction

**Read:** a final audit found no-argument localtime still used the host calendar despite the fixed epoch clock. This would change audit expectations on another date. The correction uses the effective time.time value, including maintenance's retention advance, preserves explicit conversions and restores hooks on constructor failure/close. Installed CLI audit paging independently checks today's rows and bounds both midnight and page_changed restarts.

**Result: SAFE** for the correction committed as `51041df1`, from the same fresh sol high reviewer. **Run:** 45 self-tests and diff checks passed. The reviewer independently verified the maintenance-only ledger correction (234 removed, 21 added, no changed shared values); all other assertion data remains unchanged. Provenance now records the exact old local/Linux match and corrected replay. No production, boundary, settings or workflow changes were introduced. The complete final strict Linux pair is still required and recorded in REPORT.md after it finishes.

## Exact-gap repeatability correction

**Read:** strict Linux run 42623480745 passed the main suite but failed exact-gap comparisons. Random opaque IDs changed real recovery scan order, moving a fault to a different operation; some occurrence aliases also changed order. The fresh reviewer independently confirmed both mechanisms in the artifacts. Nanosecond notice timestamps were another wall-clock input.

**Result: SAFE** for the repeatability source delta atop `51041df1`. The scenario now uses a hashed per-flow pseudo-random UUIDv4 stream, with unique nonmonotonic identities, continuous through Engine restarts, restored by the existing ExitStack. Nanosecond reads follow the effective clock. Exact comparisons are unchanged. Tests check both parent/repair ID orders, repeated fault output under opposing ambient UUID mocks, uniqueness and exception/constructor cleanup.

**Run:** reviewer ran 47 self-tests and diff checks (`OK`), and separately confirmed the stream is identical across different process hash seeds. All 32 complete fault replays are being recollected; replacement-ledger review and final strict Linux repetitions remain required.

## Final reproducible pin

**Result: SAFE** for `ec2fe8436d94e04ae870b3781bc9a3cbf864e5eb`, from the fresh sol high reviewer. The reviewer independently verified all eight Linux captures, all 32 flows per worker, shard/worker ownership, identical shared clean entries and no unexpected hard failures. The exact pinned list has 675,562 keys and 1,513 groups; all tags are valid, grouping round-trips losslessly, and all 115 non-sweep entries are unchanged. The 9,894 changed deltas match the captured data exactly.

**Run:** strict failure probes, 47 self-tests and diff checks passed. **Read:** the strict sweep entrypoint is restored identically to `51041df1`; provenance separates diagnostic capture from passing verification. The final complete strict Linux repetitions remain required, with their results recorded in REPORT.md.

## Public notice identity and runtime follow-up

**Read:** the `ec2fe843` strict pair exposed a set-order tie in expected notice pages. The reviewer independently reproduced it under hash seeds 1 and 4 with identical fault traces. Recovery and unchecked notices for one operation shared the old source/time ordering key. Source `0caf7536` derives their distinct documented public IDs, groups facts by public identity, uses saved creation times and sorts exactly by creation/ID. No normal process hash seed is pinned.

**Result: SAFE** for the complete seven-file delta committed unchanged as `0caf753626c24e58141a52c5e9ed7d26ed6a5ddc`. The reviewer verified both identical full repair captures, exact replacement data, unchanged onboarding data and all 406,761 retained entries. The ledger preserves 675,562 keys with valid tags, 1,501 groups and lossless round-trip; all 8,486 delta changes match the stated prefixes.

**Read:** a 45-minute timeout also required runtime margin. Three-worker SHA-256 ownership preserves every case, keeps modes and cleanup/crash phases together, retains clean cases on every worker and uses the same predicate for strict completeness. No workflow definition changes were added.

**Run:** 49 self-tests, the isolated ownership property and diff checks passed. The reviewer independently confirmed repair point 186's full delta is identical across hash seeds after the fix. Complete strict Linux repetitions remain the final correctness/runtime evidence in REPORT.md.

## Closing verification

**Run:** final source `0caf7536` passed Control base twice (42644340866, attempts 1/2), complete Mail twice (42644340882 and 42644366804, all four shards and all three workers each), and boundary twice (42644365833 and 42644371566). Every strict worker count matches its complete ledger scope. All test sources and gap data remain unchanged after those runs; the closing commit adds this review record and the report only. Stage 1 stops here. Production stages 2/3 have not been reviewed or built in this run.
