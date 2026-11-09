# Qualification side build

**Read/run:** qualification-owned implementation and tests are complete; this is **not** an acceptance claim for the integrated Chrome package or the installed laptop. [QUALIFICATION.md](QUALIFICATION.md) maps all 53 requirement/test rows. Owned verification covers build identity, planning, complete pair accounting, signed append-only delivery, publishing refusals, major/version gates and conservative service behavior. Shared integration H1–H6 below remains explicit. No fabricated passing qualification or shipped-build row was added.

**Read:** specifications were fetched from origin/main, with brief20, CONTROL section6 and related design files read through `git show`; qualification and continuation briefs exist only locally. Starting source e5e0c8be. The requirement map was committed first as 6a4fed17. Only qualification-owned files, new qualification tests/fixtures and the qualification jobs were changed; the original fixtures job is byte-for-byte unchanged. The core REPORT.md was not edited.

## Done

- **Read/run — build:** `chrome/build.py` now includes the installed command wrappers in `control/packaging/`, alongside all service packages, generated/settings data, complete extension/packaging, native host, launcher and dependency lock. Missing runtime directories refuse hashing. Tests mutate actual shared engine/approval/storage code, confirm the hash changes, and prove the changed build's pass cannot enable the old build. An archived shipped build keeps its own hasher; the driver executes that pinned runtime's build.py at both checks.
- **Read/run — records/gates:** strict schema and boolean validation; immutable ordered history; reconciliation when a newer shipped image contains a longer trusted prefix than persistent fetched data. A recorded major never falls back to conservative mode. Each recorded failure stays active on its patch and later patches until a higher patch passes later in publication history. Earlier advance-beta success cannot hide later stable failure; older stable success cannot hide a newer beta failure. Same-version channel switches cannot erase failure.
- **Read/run — planner/results:** strict stable/beta package identities, exact package checksum/path, full versions, newest three valid shipped builds and exact recorded-pair suppression. Every expected pair has two independent repeats; wholly missing jobs become failures, and unplanned pairs refuse publication. Actual measured runtime and browser identities are checked. The owned Node observer records the real harness's success or its precise final aggregate assertion, with pair identity and result/matrix hashes. It preserves process exit status. Crashes, cleanup errors, interrupted runs and changed/stale result files cannot qualify. A completed failed adapter can retain valid core/other-adapter results.
- **Read/run — publisher:** qualification jobs moved into `control-chrome-qualification.yml`; main-only real mutation guard retained in both CLI and job. Visible plan artifact, serialized publisher, no cancellation midway, supported verification before appending and again before pushing, shipped-baseline check at both stages, candidate attestation, failure issue and shipped-copy PR proposal. Tests publish only to a temporary local bare Git repository; issue/PR calls are stubs. They prove main never moves, unsigned insertion/rollback causes no publication and triggers an issue stub, and repeated identical publication is a no-op.
- **Read/run — delivery:** daily HTTPS and uncovered-extension-version callers tested; valid updates survive service restart and image-baseline advancement. Missing/altered evidence, wrong source, rollback, malformed/oversized responses and offline transport keep trusted history. Logs name the refusal class without copying remote/private transport detail. Public attestation bundles are fetched anonymously by subject digest, bounded both on receipt and after UTF-8 serialization, and verified by supported `gh attestation verify --bundle` with fixed repository/workflow/main and hosted-runner policy. No custom crypto. Cache/config paths are private beside the subject; refresh reserves 4 MiB for bundles plus 8 MiB for verifier cache. Runner cache was 61925 bytes, checked against that reserve.
- **Read/run — conservative behavior:** actual Engine/Chrome with a synthetic extension peer verifies generic mail bindings, suspended owner allow, link/tick/list/Enter/Space/form preparation, both stopped-form resume kinds, free read/scroll/fill/address navigation, independent read-only refusals and a notice on every declared Chrome result, including errors. New Node tests execute the actual reader and prove missing/throwing safety properties cause zero value reads and no value in binding. These are explicitly service/VM tests, not receiver/browser proof.

**Read:** qualification.json and builds.json remain empty intentionally. The registry handoff format and newest-three rule are documented in the map. Register a build only when an image actually ships, using its full commit, its own build.py digest, and a timezone-qualified shipped_at timestamp.

## Verified

**Run — local, browser-free:**

```
PYTHONPATH=control:control/chrome_tests PYTHONDONTWRITEBYTECODE=1 python3 -m unittest test_build test_publisher test_qualification test_qualification_service -v
Ran 47 tests in 1.365s
OK
node --test control/chrome_tests/*.test.mjs
84 tests; 84 pass; 0 fail; 0 cancelled; 0 skipped (6093.910375 ms)
git diff --check
(no output, exit 0)
```

Every exact Python name is in the requirement map or the `qualification-tests-<run>-<attempt>/qualification-tests.txt` artifact. The five new Node names are: `QUALIFICATION completion distinguishes final aggregate assertions from crash or cleanup errors`; `QUALIFICATION observer preserves process failures and distinguishes completed failures from interrupted suites`; `QUALIFICATION completion binds actual result and matrix bytes, and requires both`; and `QUALIFICATION conservative reader excludes unknown safety: missing style property` / `throwing style getter`. No local browser/profile was started, read or touched.

**Run — final runtime c3fc4231, first runner set:** [push42690547697, attempt1](https://github.com/Ares-Empire/AresOS/actions/runs/42690547697/attempts/1) PASS; [PR42690561747](https://github.com/Ares-Empire/AresOS/actions/runs/42690561747) PASS. The downloaded push log has `Ran 47 tests in 1.901s` at line188 and `# tests 84` / `# pass 84` at lines698/700. PR log line223 has `Ran 47 tests in 1.769s`.

**Run — actual attestation, same push:** both this run's new synthetic record and the retained own-package run42687597384 fixture pass the real verifier and all altered-copy/refusal cases. Exact push log lines992–1017 include:

```
QUALIFICATION DELIVERY newer valid attested record used PASS
QUALIFICATION DELIVERY anonymous bundle lookup in launch-equivalent environment PASS; cache 61925 bytes
QUALIFICATION DELIVERY missing attestation refused; held retained PASS
QUALIFICATION DELIVERY altered attestation refused; held retained PASS
QUALIFICATION DELIVERY wrong workflow refused; held retained PASS
QUALIFICATION DELIVERY wrong branch refused; held retained PASS
QUALIFICATION DELIVERY production main rejects branch fixture refused; held retained PASS
QUALIFICATION DELIVERY altered subject refused; held retained PASS
QUALIFICATION DELIVERY dropped held entry refused after real verification PASS
QUALIFICATION DELIVERY changed held entry refused after real verification PASS
QUALIFICATION PUBLISHER real held attestation and baseline verified PASS
QUALIFICATION PUBLISHER unsigned inserted entry refused; no write, issue stubbed PASS
QUALIFICATION PUBLISHER non-append-only shipped baseline refused; no write, issue stubbed PASS
```

The anonymous case clears the environment to the launcher's PATH/LANG only: no HOME, login config or token. The production default is still main; only the fixture explicitly accepts this qualification branch. Public bundle lookup is not trust: every accepted bundle still passes gh's signature/identity policy. [GitHub's verifier documentation](https://cli.github.com/manual/gh_attestation_verify) describes local bundle verification. The retained record/bundle is under `control/chrome_tests/fixtures/qualification/42687597384/`; altered copies are temporary. Artifacts `qualification-attestation-42690547697-1` contain both verification transcripts and the current real bundle.

**Run — failures kept honest:** push42689879277 failed anonymous verification because the temporary bundle lacked gh's required .jsonl extension. The follow-up fixed the producer and added the strict extension/serialized-byte regression; no assertion was removed. Earlier implementation reviews also found and closed the image-baseline deadlock, beta precedence, hidden artifact, archived-hasher mismatch, stale-result acceptance, daily/manual prerequisite and pipefail defects. [BUILD-QUAL-1.md](BUILD-QUAL-1.md) records the independent sol/astra reviews and fixes.

## Shared files / not verified

- **H1 — read, installed network path:** `control/packaging/aresos-toold.service` has `RestrictAddressFamilies=AF_UNIX` and `IPAddressDeny=any`. Direct HTTPS record/bundle lookup and gh trust-root refresh cannot work under that unit. The package lead/image integration must provide the intended network path and test real refresh under the installed unit. This side build did not broaden that policy or build a replacement service.
- **H2 — read, installed verifier:** `control/ci/setup.sh` does not install the required gh >=2.102.0. Install the supported verifier and retain writable private cache/config under the service state path, then test installed-launcher + unit delivery. Minimal-environment verification is run here; actual installed-unit networking is not. No personal GitHub credentials are needed by the owned verifier.
- **H3 — not run, integrated conservative browser cases:** rerun at the integrated core/adapters head with independent receiver logs: generic mail send and existing owner allow; link, tick, list, Enter/Space controls, GET search and ordinary/stopped submissions (both resume kinds), each zero before approval, exactly one after and no replay; free read/scroll/type/address navigation; unsafe-reader properties across every frame/shadow root with zero value traces; read-only fill/button/upload refusal; notices on successful/prepared/refused/error results. New injection/reload/owner-task behavior belongs to core. Service and actual-reader VM tests here do not substitute for those browser assertions. No new screenshots claimed.
- **H4 — read, real managed ask evidence:** core `control/chrome/ci/verdicts.mjs` omits group12; its runner never invokes 18d's normal/skip-permissions precedence harness. Integrate that actual evidence and put its result in groups[12]. Owned pair ingestion currently makes **every result false without it**. Do not set it true synthetically. This deliberately prevents incomplete Now evidence becoming production qualification.
- **H5 — read, adapter verdict precision:** `verdicts.mjs` line25 requires aggregate groups[10] for each adapter. One failed adapter therefore disables all adapters despite other fixtures passing. Preserve the independently failed adapter(s), while retaining genuine shared prerequisite failures. The owned service and completed-pair tests prove generic fallback/healthy-adapter retention; the core verdict producer still needs this change.
- **H6 — not run, real main publication/observer integration:** branch runs skip real planning/pair/publication jobs. Their publisher is exercised against a local runner repository or notification stubs; live signature/history refusal paths are tested. The actual production job and its NODE_OPTIONS observer in a real full browser pair require the integrated head/main run. No real data branch, issue or shipped-copy PR was mutated by these tests. The separate existing Control Chrome fixtures workflow does not load this qualification-only observer.

## PLAN-GAP / JUDGMENT-CALL

**PLAN-GAP — read:** installed HTTPS/verifier integration H1/H2 and real group12/adapter-verdict integration H4/H5 prevent a claim that laptop qualification delivery is complete. None is hidden by a synthetic pass. The integration owner must resolve them in its files. Main-only production publication cannot be tested against real data from this branch under the brief's rails; hermetic tests and genuine signatures cover its components.

**JUDGMENT-CALL — read/run:** failure recovery requires both a higher patch and later immutable publication evidence, including across beta/stable channels. Choosing only the numerically latest beta can erase a later-discovered stable failure; choosing stable unconditionally can erase a newer beta failure. Same-version cross-channel passes never erase failures. Earlier running patches with no applicable evidence use advance beta (or recorded major evidence) conservatively rather than entering the unrecorded-major fallback. Changing this later requires a record-policy migration and all sequence regressions.

**JUDGMENT-CALL — read/run:** runtime inventory now includes installed command wrappers; this is a new build identity. Existing shipped builds keep their own pinned algorithm to avoid relabeling installed code. Missing group12, incomplete execution, wrong identity or unbound result bytes disable qualification rather than inventing evidence. The observer depends on the current core harness's precise final AggregateError contract; if that contract changes, integration must update its strict tests, not treat arbitrary exceptions as completion.

**Read:** no new owner-feel policy was added. Conservative cases and read-only behavior retain the design. The original core report's owner-input limitation remains core-owned; this side build neither claims it fixed nor changes its assertions.

## Delivery / run accounting

**Run:** draft [PR30](https://github.com/Ares-Empire/AresOS/pull/30) targets pkg/20-chrome; no merge or force push. All commits carry the requested model trailer. Closing documentation pushes are included in the budget below. No Gradle/Java daemon was started; no system software was installed. At the first closing inventory `.work/` held589580 bytes and no file over500 MB; final inventory is below.

**Run — second final source/runtime verification:** [42690547697 attempt2](https://github.com/Ares-Empire/AresOS/actions/runs/42690547697/attempts/2) PASS, repeating all47 Python,84 Node and both complete real-attestation fixture sequences on unchanged c3fc4231. This is a real rerun, not the PR job being counted as attestation evidence. Runtime digest printed locally: `9050f08ef3efc833f2241fee8e2716906143c4433f76b8c300551b8770114cea`. The closing commits contain reports only and do not change this digest.

**Run — budget:**12 workflow IDs /13 attempts through source verification (the second attempt of42690547697 counts), plus the closing documentation push's3 workflows: **16 attempts reserved/used of about25**, including cancellations. Chrome fixture runs42687596159,42689234398 and42689879566 were canceled after newer runtime fixes superseded them.42690547740 is the unchanged core fixture suite, not qualification-side browser acceptance; H3/H6 remain not verified here. No further source-workflow start is planned. Main-only planning/publishing jobs stayed skipped on all branch/PR runs.

**Run — source-verification workflow IDs:**42687597384,42687596159,42687724040;42689233574,42689234398,42689255604;42689879277,42689879566,42689887578;42690547697 (attempts1/2),42690547740,42690561747. The one failed attestation iteration is retained above, not counted as green. Closing documentation runs are visible on PR30 and are within the reserved total.

**Run/read — remaining handoff:** the lead integrates H1–H6 in its owned files and reruns the full browser matrices on the combined head. This branch never merges other branches. There are no open preference questions for the side build; no real site/account or image/install acceptance is claimed.

**Run — final storage inventory:** `.work/` contains 776730 bytes; files over500 MB: **none**. No ISO, image layer, extracted browser or browser profile exists there.

**Run — second-set exact log lines:** attempt2 log line481: `Ran 47 tests in 1.536s`; lines991/993: `# tests 84` / `# pass 84`; lines233/246: anonymous minimal-environment verification PASS with61925/61924 cache bytes; lines242–244 and255–257: held verification, unsigned insertion refusal and non-append-only baseline refusal PASS.
