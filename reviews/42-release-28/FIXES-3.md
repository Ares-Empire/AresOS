# Review 3 fixes: package 42, step 1

2026-11-17. Builder: Codex, gpt-6.1-sol (xhigh). Worktree branch: `fix/42-s1`.
Starting HEAD: `7ff6df1585a3ace4a61db71d594d450ac1d0def3`.

All six findings are addressed in `os/ci/release_diff.py` and
`os/tests/test_release28.py`. No brief design change was needed.

1. **Missing RPM files and verification failures.**
   `release_diff.py:1328` and `:1403`: check every non-ghost record of the added
   packages against the complete new inventory, including absent and unchanged
   paths. Check all non-ghost records of a shared path; ghost-only paths may be
   absent. `:1574`: any nonzero `rpm -V` exit, or unexpected output even with exit
   zero, adds a problem before `result.json` is written, so its status is stopped.
   Tests: `MainSmokeTest.test_a_missing_expected_rpm_file_stops_even_when_absent_from_both_images`
   (`test_release28.py:1961`), `test_an_unchanged_rpm_file_must_still_match_its_record`
   (`:1978`) and `test_rpm_verification_failure_is_fatal_even_when_every_path_is_explained`
   (`:1941`). The RPM query stand-in now uses independent literal package records,
   rather than querying the fixture's actual files. Missing keytool is tested
   with both a clean and a failing verification result; neither can pass.

2. **Generated-file exceptions.**
   `release_diff.py:421` and `:1364`: exactly the six observed dnf5 history names,
   the two observed repository countme paths, `var/log/dnf5.log` and
   `var/cache/ldconfig/aux-cache`. Each permits content changes only: no additions,
   removals, type changes or metadata changes. Both sides must be root:root regular
   files, 0644 (0600 for aux-cache), with no xattrs. The RPM database's existing
   exact-path exception now requires root:root 0644 and no xattrs too.
   Test: `Classifier28Test.test_generated_exceptions_reject_neighbours_and_every_unreviewed_operation_or_metadata`
   (`test_release28.py:1001`). Includes all three review probes: the setuid
   `unreviewed.sh`, a repository's `not-countme`, and deletion of aux-cache.
   Tests also reject adjacent filenames, descendants, another repository, log
   rotation, each unreviewed operation and metadata field on either side.

3. **Alternatives target associations and record structure.**
   `release_diff.py:959` and `:1186`: parse complete choices, each with its own
   master target, priority and ordered slave targets (including absent slaves).
   Reject duplicate names/paths, incomplete choices, extra fields and malformed
   paths. Require every selected link to match the corresponding target of one
   complete choice; automatic mode selects a highest-priority choice. The result
   records the selected target per alternative name, rather than a target union.
   Tests: `AlternativesAdminTest.test_the_entire_record_structure_is_required`
   (`test_release28.py:511`),
   `Classifier28Test.test_swapping_alternatives_targets_stops_the_record_and_both_commands`
   (`:926`) and `test_alternatives_cannot_mix_two_choices_or_choose_a_lower_automatic_priority`
   (`:935`). Swapping either link or both stops the record and both command chains.
   The family fixture was corrected to the upstream format: `@family@` prefixes
   the priority, not the target. The former malformed fixture is now a negative
   case. Checked against [chkconfig 1.33's reader and writer](https://github.com/fedora-sysv/chkconfig/blob/1.33/alternatives.c).
   Unexpected init-script suffixes are rejected; the added Java alternatives need none.

4. **Prism's complete typed inventory.**
   `release_diff.py:477`, `:1100` and `:1411`: derive the expected inventory from
   the existing SHA-256/size-pinned tarball, independently of the image. Replay
   `build.sh`'s data-filtered extraction and its three deliberate exclusions in a
   temporary directory. Compare every expected directory, file and symlink,
   including type, mode, root ownership, absence of xattrs, file size/hash and
   exact link target. Compare path sets too, even when a path is absent from both
   images. Reject dangling/escaping links in the expected bundle. Preserve the
   reviewed regular-file-list pin as an additional check.
   Tests: `PrismInventoryTest` (`test_release28.py:436`),
   `Classifier28Test.test_prisms_typed_inventory_rejects_dangling_missing_or_different_links_and_modes`
   (`:894`) and
   `MainSmokeTest.test_a_missing_expected_prism_link_stops_even_when_absent_from_both_images`
   (`:1911`). Archive tests independently bind the full typed result, reject
   bad hashes/sizes, check cache reuse with absolute and relative paths, and
   require temporary extraction and partial-download cleanup.
   The release diff needs one extra read-only download of the pinned archive;
   it reuses one verified cached copy in `.work/release-diff/`. No extracted
   bundle survives. Host filesystem labels are excluded from the expected
   inventory; the image must still carry no xattrs.

5. **Compiled schemas' runtime metadata.**
   Chose deterministic rebuild, not a second GVDB lookup implementation.
   `release_diff.py:453`, `:466` and `:1254`: the release job already has Podman,
   and the image already contains Python and the compiler used by `build.sh`.
   Run that image's `/usr/bin/glib-compile-schemas --strict` against that image's
   schema directory, with output on a small disposable `/tmp` tmpfs. The container
   is read-only, has no network and does not pull. Require exact compiled bytes,
   covering hashes, buckets, bloom filters and every other runtime field, before
   the existing semantic comparison attributes the changed key to package 31.
   Compilation/comparison failure also stops the overall result even if the
   compiled path never entered the diff. Record `schema_rebuild` in the result.
   Tests: `SchemaRebuildTest.test_rebuild_checks_the_actual_bytes_including_hashes_and_buckets`
   (`test_release28.py:217`),
   `Classifier28Test.test_corrupted_schema_hashes_and_buckets_are_not_explained`
   (`:1099`) and `MainSmokeTest.test_corrupted_schema_lookup_metadata_stops_the_result`
   (`:1919`). Both corruptions leave enumerated values intact. The first test
   executes the actual comparison program with an independent deterministic
   compiler stand-in; it also checks compiler failure. The other tests cover the
   classifier and stopped result.

6. **Jar-pin Git mode/type.**
   `release_diff.py:576`: require the old and new entries to be the same regular
   100644 blob before granting the JSON-only jar-pin exception.
   Test: `SourceChangesTest.test_a_jar_pin_renewal_cannot_change_the_git_mode_or_type`
   (`test_release28.py:377`). Both an executable lock and a symlink whose blob
   contains otherwise acceptable JSON are rejected.

## Verification

Each requested module was run separately with this command form:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p '<module>.py'
```

| Module | Final output |
| --- | --- |
| `test_release28` | `Ran 75 tests in 22.095s` / `OK` |
| `test_release27` | `Ran 41 tests in 7.315s` / `OK` |
| `test_checkout_sources` | `Ran 8 tests in 0.991s` / `OK` |
| `test_ci_api_permissions` | `Ran 4 tests in 2.646s` / `OK` |
| `test_ci_step_environment` | `Ran 4 tests in 10.839s` / `OK` |

Earlier development runs of `test_release28` passed at 64 and 67 tests. The first
74-test run exposed inherited SELinux xattrs in the independently extracted
expected inventory; the production fix now explicitly expects no image xattrs.
The first 75-test run exposed overbroad path substitution in the compiler
stand-in; it now substitutes only the exact output arguments. Subsequent runs
passed all 75. Before the final alternatives-format correction, the other four
modules also passed (41, 8, 4 and 4 tests respectively).

`git diff --check` passed with no output. No file over 500 MB remains in `.work/`.

## Not verified and commit blocker

- No image build, container run, hosted dispatch, VM rehearsal or in-game check
  was run. The five local modules use stand-ins for image commands. The complete
  pinned production Prism archive could not be downloaded in this sandbox
  (DNS resolution is unavailable); the new archive path is verified with a
  separately constructed pinned tarball. The actual release image's deterministic
  schema rebuild and the tightened generated-file metadata need the lead's next
  dry run. An unavailable archive or failed rebuild stops that job.
- Local staging failed: `git add os/ci/release_diff.py os/tests/test_release28.py`
  exited 128, reporting `Read-only file system` while creating this worktree's
  `index.lock`. Its Git metadata directory is mounted read-only despite the
  shared Git directory being writable. No commit was created; HEAD remains the
  starting SHA above. No permission escalation or alternate Git metadata was
  attempted. The changes and this notes file are left for the lead to commit.
  The requested commit trailer is `Codex-Model: gpt-6.1-sol (xhigh)`.
- `PROGRESS.md`, the pending bindings and owner-tools code were not edited.
  `rebind.py` was not run. No branch switch, push or system-changing command was
  performed, and no `test_owner_*`, inherited-homebrew, sysusers or whole-suite
  module was run.
