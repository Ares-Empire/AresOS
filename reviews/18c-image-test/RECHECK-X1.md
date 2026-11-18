Codex gpt-6-astra, 2026-11-17.

Read `AGENTS.md`, both X1 reviews, `896f45e6..48570285`, the relevant implementation and tests, the design, the brief’s evidence/protected-path/acceptance sections, and PROGRESS’s fix-round record.

Ran `git diff --stat`, `git diff --check`, seven Python syntax compilations in memory, and memory-only old/new behavioral probes. Attempted `test_control_image`: **15 tests, 13 setup errors**, because the read-only sandbox provides no writable temporary directory. I did not run the other full modules or repeat CI/VM runs. Hosted results are supplied evidence. No files changed or prohibited commands ran.

The stat confirms **all code changes are CI-only**; the other changes are review-link corrections. Production image configuration, `control/`, and `.github/workflows/os-image.yml` are unchanged. `48570285..HEAD` changes only PROGRESS, including its later change inventory.

| X1 finding | Closed? | Regression evidence and baseline behavior |
|---|---|---|
| **1. Vendor bytes independently bound to wheels** | **Not fully.** Files inside `vendor/` are bound; siblings remain self-certified. | `test_the_record_must_be_what_the_locked_wheels_install` — [os/tests/test_control_image.py:402](../../os/tests/test_control_image.py#L402) — covers altered source, bytecode, extra files and generated metadata **inside `vendor/`**. It cannot run unchanged on `896f45e6`, which lacks the new helper; the old checks accept these self-recorded mutations. No regression covers the sibling-file escape below. |
| **2. Password scan requires complete coverage** | **Not fully.** Read/traversal/journal failures now fail, but unknown vanished runtime content remains exempt. | `test_one_unreadable_file_fails` [612](../../os/tests/test_control_vm.py#L612), `test_a_folder_that_cannot_be_listed_fails` [620](../../os/tests/test_control_vm.py#L620), and `test_a_journal_export_that_fails_fails` [630](../../os/tests/test_control_vm.py#L630). These depend on helpers absent from the baseline. Separately, executing the actual old/new `passwords()` functions with mocked I/O reproduced **old returncode 0 / new rejection** for unreadable content and failed journal export. |
| **3. Unsearchable archives fail closed** | **Not fully.** The reported examples are fixed, but archive recognition has another silent-pass path. | `test_archives_nested_past_the_depth_limit_are_unreadable` [756](../../os/tests/test_control_vm.py#L756), `test_a_damaged_tar_holding_a_compressed_password_is_unreadable` [775](../../os/tests/test_control_vm.py#L775), and `test_formats_the_scan_does_not_unpack_are_unreadable_and_ordinary_logs_are_not` [801](../../os/tests/test_control_vm.py#L801). Memory-only probes confirmed their negative cases escape the old scanner and are rejected now. |
| **4. Interactive PASS requires transcripts** | **Yes.** | `test_a_missing_evidence_folder_fails_and_is_named` [218](../../os/tests/test_control_vm.py#L218) and `test_check_9_fails_without_its_transcripts` [229](../../os/tests/test_control_vm.py#L229). The latter’s existing test method, run with an in-memory filesystem and stubbed archive transport, passed against current code and failed against the baseline: **`0 != 1 : none`**. Missing folders also produced errors only in current code. |

1. **SHOULD-FIX — the independent vendor tree retains untrusted siblings.**  
   [os/ci/control/vendor_check.py:210](../../os/ci/control/vendor_check.py#L210)

   `check()` inventories all of `/usr/lib/aresos-control`, but removes and reconstructs only its `vendor/` child. An extra `/usr/lib/aresos-control/extra.py` or `extra.pyc`, included in the build-generated manifest, survives reconstruction unchanged. Both comparisons therefore accept it.

   Executing the real comparison logic with filesystem mutations modeled in memory accepted both sibling examples; the same extra file **inside** `vendor/` was rejected. Existing image checks also accept a root-owned, correctly recorded sibling.

   Derive the entire expected dependency tree independently, or explicitly require the dependency directory to contain only `vendor/`. Add sibling-file and sibling-bytecode regressions.

   The remaining mechanism looks sound: `fetch()` checks the recorded SHA-256 against both index metadata and downloaded bytes; the preceding shell check binds the record to `control/requirements.lock`. The comparison starts against the built image in a `--network=none` container, then reconstructs the expectation there. Within `vendor/`, generated scripts, `INSTALLER`, empty `REQUESTED`, `RECORD`, injected `direct_url.json`, and compiled bytecode participate in exact content comparisons. Existing image checks enforce actual modes.

2. **SHOULD-FIX — any disappearing runtime file can become successful, incomplete coverage.**  
   [os/ci/control/tree_scan.py:99](../../os/ci/control/tree_scan.py#L99), [os/ci/control/actions.py:1586](../../os/ci/control/actions.py#L1586)

   A process writes the synthetic password to `/tmp/control-debug.log`. The scanner lists it, but the process removes it before opening; the subsequent `lstat` also returns ENOENT. The scanner records `vanished`, leaves `errors` empty, and check 8 can return success with the legitimate stored password as its only hit.

   I reproduced that successful `passwords()` result. The policy covers **every** descendant of `/run`, `/tmp` and `/var/tmp`, including disappearing directories. A pathname and two ENOENT results do not establish that its unread content was harmless. The existing [runtime-disappearance test](../../os/tests/test_control_vm.py#L637) uses a clean file and explicitly permits this result.

   Fail on unknown vanished content; restrict any exemption to specifically justified transient paths. The currently configured missing roots, ordinary read failures, unlistable directories and unsuccessful journal exports otherwise fail correctly.

   Walking the current document-portal FUSE mount as its owner is reasonable: it replaces root’s denied traversal, and owner-side errors propagate. I found no demonstrated loss of root-visible content for that mount. The assertion that *every* FUSE mount refuses root is broader than the implementation can assume, particularly with `allow_other`.

3. **SHOULD-FIX — exact tar magic matching can classify readable archives as ordinary bytes.**  
   [os/ci/control/evidence_scan.py:64](../../os/ci/control/evidence_scan.py#L64)

   A valid V7 tar containing `secret.gz` has no POSIX/GNU magic. `tarfile` reads it, but `kind()` returns `None`; the compressed password produces neither a hit nor `Unreadable`.

   There is also a **new regression**: a tar retaining `ustar` but carrying version bytes `01`, with its checksum recomputed, is accepted by Python’s tar reader. The old scanner found its compressed password; the new exact eight-byte comparison returned **zero members, zero hits, no error**. I reproduced both cases in memory.

   Preserve recognition of parseable tar archives and classify recognizable malformed/unsupported variants as unreadable. Add both regressions.

   The depth-limit and damaged-header fixes themselves work. Ordinary text and normal `.tar.gz` evidence passed the probes; the supplied runs also report no unreadable evidence. Nested `.tar.gz` within `.tar.gz` now exceeds the configured depth deliberately.

The change to `test_a_tar_that_does_not_fit_...` is honest: it removes the obsolete expectation that a missing folder succeeds. Its oversized-archive assertions remain, and the missing-folder case now has a dedicated failure test at line 218.

I found no further failure-to-summary or empty-list success path in the changed transcript handling. Copy exceptions now populate `errors`, empty transcript sets fail, and required missing folders fail packing.

The fixes do not change the production behavior judged SAFE by SECURITY-REVIEW-X1. Its limits remain: one deliberate Stop JSON diagnostic on hook errors; UID/GID 250 depends on release-rehearsal deployment checks; auto mode remains unexercised, K1. The findings above concern CI verification and synthetic-password evidence. `.work/` contains no files over 500 MB.

CHANGES-NEEDED