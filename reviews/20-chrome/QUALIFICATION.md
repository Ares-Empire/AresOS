# Qualification requirement map

Specification **read** from `origin/main` after fetch (2026-11-09): brief 20, “Qualifying each new Chrome stable”, and CONTROL section 6. Qualification/continuation instructions are local: those paths are absent on `origin/main`. Starting source: `e5e0c8be`. This map is committed before implementation. **Read** means inspected, not executed; **missing** includes incomplete evidence.

Paths below are relative to `control/`. Q = `aresos_control/chrome/qualification.py`; P = `chrome/qualify.py`; W = `.github/workflows/control-chrome.yml`; E = `aresos_control/chrome/adapter.py`. Existing tests are under `chrome_tests/`.

| ID | Requirement / required test | Implementation read | Starting evidence / gap |
|---|---|---|---|
| B1 | Hash complete extension, page script, host, installed service, shared engine/approval, definitions and words | `chrome/build.py:inputs/build_hash` | `test_build.Build.test_complete_installed_runtime_including_shared_approval_changes_identity`; missing independent inventory and install/hash parity checks |
| B2 | Workflow and install compute same build; installed service uses its own build only | W identity check; `ci/setup.sh`; E constructor | **missing** installed-ID validation/parity evidence |
| B3 | Another build's pass never enables this build | Q `switches` | `test_policy.Policy.test_qualification_failure_patch_beta_build_and_conservative_rules`; missing explicit changed-shared-code old/new service case |
| T1 | Daily Google Linux repository lookup for stable AND beta, full version/exact package | P `packages`, W schedule | `test_publisher.Publisher.test_lookup_both_channels_and_newest_three_builds_twice`; malformed/duplicate metadata **missing** |
| T2 | Main plus newest three shipped builds in builds.json | P `plan` | same test; strict registry validation **missing** |
| T3 | Every main push and daily run: each unrecorded build/full-version/channel twice | P `plan`, W plan/pairs | same test; recorded-pair suppression and missing-job accounting **missing** |
| R1 | Per build/full version/channel and run: four core groups, all six adapters, booleans | Q `validate_record`, P `aggregate` | missing-repeat test; malformed records and wrong identity **missing** |
| R2 | A missing/failed repeat or group cannot pass | P `aggregate`; `chrome/ci/verdicts.mjs` | `test_missing_repeat_or_missing_group_never_qualifies`; whole absent pair / failed job with stale result **missing** |
| R3 | Issue names failing groups; publisher refusal opens issue | P `notify` | stub notification test; bounded/new-only failure details and all refusal paths **missing** |
| P1 | Data branch only, never main; main-only publishing/issue/PR mutations | P CLI guard; W publish job | `test_real_remote_mutations_refuse_on_this_branch_and_notifications_are_stubs`; all mutation commands/refs **missing** |
| P2 | Verify current published attestation before append, as service does | P `prepare`, Q `verify` | stub verification-order test; genuine bundle verification **missing** |
| P3 | Current record append-only against shipped main baseline | P `prepare`, Q `append_only` | existing rollback test; altered/reordered/duplicate baseline rows **missing** |
| P4 | Outside-workflow inserted entry: publish nothing, open issue | P `prepare`, `notify` | separate stub tests; integrated local-repository refusal **missing** |
| P5 | Non-append-only published branch: publish nothing, open issue | P `prepare`, `notify` | separate tests; integrated local-repository refusal **missing** |
| P6 | Publisher serialized, not cancelled midway | W publish concurrency | **read** only; exact concurrency contract test **missing** |
| P7 | Attest candidate, verify it, push data branch, open unmerged shipped-copy PR | W attest/publish; P publish/notify | stub notification test; full hermetic local publication **missing** |
| D1 | Fetch HTTPS daily and on extension version not held for own build | Q `refresh`; E `maintenance` | **missing** runtime scheduling/caller tests |
| D2 | Verify repository's qualification workflow on main with supported gh verifier | Q `verify` | `chrome/ci/attestation.py` real subject/wrong branch test; actual altered bundle/wrong workflow/missing bundle **missing** |
| D3 | Use own package workflow attestation + altered copies as fixtures | W delivery-attestation | existing live API subject test; retained bundle fixture **missing** |
| D4 | New valid record is used and retained across restart | Q `accept/record` | **missing** durable-store delivery test |
| D5 | Missing attestation refused; held kept | Q `accept/refresh` | **missing** |
| D6 | Altered attestation refused; held kept | Q `accept/refresh` | **missing** actual altered-bundle test |
| D7 | Other workflow refused; held kept | Q `verify` | **missing** actual verifier test |
| D8 | Other branch refused; held kept | Q `verify` | existing real wrong-branch test; durable held assertion **missing** |
| D9 | Dropped held row refused; held kept | Q `append_only/accept` | `test_qualification_delivery_append_only_and_wrong_build`; delivery-store assertion **missing** |
| D10 | Changed held row refused; held kept | Q `append_only/accept` | same; delivery-store assertion **missing** |
| D11 | Offline keeps held and logs reason | Q `refresh` | **missing** transport/log/rate-limit tests |
| G1 | Failed adapter off; site uses generic rules | Q `switches`; E input recognition | switch test; service generic fallback **missing** |
| G2 | Failed core group refuses dependent actions with reason | E `mode` | password revalidation test; each group/read/act surface **missing** |
| G3 | Failed patch, later unrecorded patch same major: still off | Q `switches` | existing switch test; service path **missing** |
| G4 | Later patch of qualified major runs normally | Q `switches` | existing switch test; service path **missing** |
| G5 | Passing beta enables major's stable, even before beta full-version number | Q `switches` | partial test; explicit pre-beta-version stable **missing** |
| G6 | Failed beta → stable still off, never conservative | Q `switches` | **missing** explicit sequence |
| G7 | Passing beta → failed stable off from stable onward → passing patch back on | Q `switches` | **missing** explicit sequence / channel tie |
| G8 | Recorded failure takes precedence over conservative allowances | Q `switches`; E mode | **missing** major with recorded later failure but no earlier applicable entry |
| C1 | Conservative only for own build's wholly unrecorded major; adapters off | Q `switches` | existing policy/engine tests; recorded-major edge **missing** |
| C2 | Conservative synthetic mail send uses generic binding | E recognition | browser `QUALIFICATION conservative activations ask and core failures gate before reads`; service proof **missing** |
| C3 | Existing don't-ask-again suspended; asks | E `trusted` | same browser matrix; service proof **missing** |
| C4 | Link click asks, zero before approval / once after | E/policy | browser matrix and policy test; service case **missing** |
| C5 | Tick asks, zero before approval / once after | E/policy | same; service case **missing** |
| C6 | List choice asks, zero before approval / once after | E/policy | same; service case **missing** |
| C7 | Enter on control asks, zero before approval / once after | E/policy | same; service case **missing** |
| C8 | Space on control asks, zero before approval / once after | E/policy | same; service case **missing** |
| C9 | Any form submission asks (GET search too) | E/policy/guard | browser search case; explicit stopped form/resume service proof **missing** |
| C10 | Read free | E `read` | browser matrix reads; explicit no-preparation service case **missing** |
| C11 | Scroll free | E/policy | **missing** conservative service/browser case |
| C12 | Typing free | E/policy | browser fill case; service case **missing** |
| C13 | Navigate by address free | E navigate | browser nav helper; explicit service case **missing** |
| C14 | Unknown field safety means no value read; exclusion still runs | extension reader (core ownership) | **missing** explicit conservative unknown-safety browser case; service cannot prove getter behavior |
| C15 | Read-only site filling refused | E/policy owner list | browser matrix; existing engine combined test |
| C16 | Read-only button refused | E/policy owner list | same |
| C17 | Read-only upload refused | E/policy owner list | same |
| C18 | Every result has plain unqualified-version notice, errors included | E reads + engine envelope | `test_conservative_notice_on_every_result_and_independent_bank_restriction`; full public call surface **missing** |

Browser evidence remains the core harness's independent receiver logs, exclusively in runner containers. When a required browser case depends on unfinished injection/reload/task rules, this side build adds strict service coverage and lists the exact browser integration case in QUALIFICATION-REPORT.md; it does not replace core behavior.

Initial registries are empty deliberately: no fabricated passing rows and no invented shipped builds. Workflow runs on this branch so far: **run** `gh run list --branch pkg/20-chrome-qual` returned `[]`.
