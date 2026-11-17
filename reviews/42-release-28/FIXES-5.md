# Review 5 fixes: package 42, step 1, round 2

2026-11-17. Starting and final HEAD (no commits made):
`5c9d5f015a29354301b661802579f5e1871c69e9`.

Both remaining should-fixes are addressed. Changes are left in this worktree
for the lead to review and commit. No brief design change was needed.

1. **A consistently wrong alternatives record and links passed.**
   Chose a small repo manifest, `os/ci/release28-alternatives.json:1`, with the
   complete group/name/public-path/target/priority mapping. Its source is the
   pinned RPM's postinstall scriptlet already recorded in
   `reviews/23-minecraft-starts/runs/resolve-43466199049/candidate.txt:112`.
   The corresponding candidate lock has exactly the current RPM's NEVRA and
   SHA-256. This avoids interpreting shell scriptlets or downloading another
   RPM during every release diff, while leaving the expectation small and
   reviewable. It is independent of the image under test.

   `os/ci/release_diff.py:1005` binds the manifest to the source package lock's
   NEVRA and SHA-256 and requires that NEVRA to be installed. A renewed package
   needs a reviewed manifest update. `:1197` compares the complete parsed
   public-name mapping and every choice's associated targets and priority
   against that expectation before accepting any selected chain. The existing
   ownership, coherent-choice and automatic highest-priority checks remain.

   The manifest retains all four legitimate groups (`java`, `jre_openjdk`,
   `jre_25`, `jre_25_openjdk`), twelve chains, priority `25000508`, the JVM
   directory links and the public `.1.gz` names pointing through alternatives
   to the package's uncompressed `.1` pages. The dry run 4 log (43897120279)
   independently lists four explained records and all twelve public names;
   its counts agree with these scriptlet effects and PROGRESS's passed run.

   Negative test:
   `Classifier28Test.test_swapping_the_record_and_links_together_cannot_redefine_java`
   (`os/tests/test_release28.py:989`) swaps java and keytool consistently in
   the record and both alternatives links; the record and all four links must
   remain unexplained. `test_record_names_public_paths_and_priorities_cannot_redefine_the_reviewed_mapping`
   (`:1037`) also rejects changed group/slave names, public paths and priority.
   `AlternativesAdminTest.test_the_manifest_stops_on_a_renewed_nevra_or_hash_or_an_absent_package`
   (`:531`) tests the package binding. The positive manifest test (`:520`)
   independently reconstructs the mapping from the committed scriptlets and
   checks their candidate package pin; the classifier's four-group test
   (`:1050`) accepts all twelve resulting chains.

2. **Missing public command links were invisible.**
   `os/ci/release_diff.py:1197` now validates both links of every selected
   chain: each public path must be a root:root 0777 symlink with no xattrs,
   pointing to its own `/etc/alternatives/<name>`, whose link must select its
   exact reviewed target. `:1239` shares the metadata/type/target check.
   An absent slave target requires both its alternatives link and its public
   path to be absent, including dangling links. `:1443` requires every reviewed
   group to validate, independently of `changed`; even an entirely missing
   record and link chain stops the result.

   Negative tests in `os/tests/test_release28.py`:
   `test_missing_public_links_stop_even_when_absent_from_both_images` (`:1000`)
   removes java, keytool or both; `test_every_public_link_requires_its_type_metadata_and_target_even_when_unchanged`
   (`:1010`) checks type, uid, gid, mode, xattrs and target even when old and new
   entries are identical. `test_a_slave_without_a_target_requires_both_links_absent_and_rejects_an_extra_public_link`
   (`:1022`) accepts the absent-slave case, then rejects extra public symlinks
   (both through alternatives and directly to a package target), regular files
   and directories, plus an extra alternatives link. MainSmokeTest's
   missing-public-link (`:2070`) and missing-whole-group (`:2079`) tests require
   `status: stopped`, including when no alternatives path enters the diff.

## Verification

Each module ran separately, with bytecode disabled, using exactly:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p 'test_release28.py'
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p 'test_release27.py'
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p 'test_checkout_sources.py'
```

| Module | Final output |
| --- | --- |
| `test_release28` | `Ran 85 tests in 22.337s` / `OK` |
| `test_release27` | `Ran 41 tests in 6.845s` / `OK` |
| `test_checkout_sources` | `Ran 8 tests in 1.002s` / `OK` |

Before changing production code, the new consistent-swap and missing-public-link
tests failed against HEAD: `Ran 77 tests in 24.126s`, `FAILED (failures=8)`
(five swapped-chain subtests and three missing-link subtests). This reproduces
both review holes. The first 85-test development run reported 15 failures:
the enlarged smoke image introduced `/usr/bin`, but its old image omitted that
existing base directory. Corrected the fixture to include the base directory;
no assertion was weakened. The subsequent full module run passed as above.

`git diff --check` passed with no output. No `.work/` directory or file over
500 MB was created or left in this worktree.

## Not checked and boundaries

- No real image build, container execution, VM, hosted dispatch or publication
  was run. No replay of the real dry-run file inventories was possible here.
  The GitHub connector could return the existing dry run 4 log and a ZIP
  download reference; materializing that ZIP locally failed with
  `URLError: Temporary failure in name resolution`, without creating a file.
  Compatibility evidence here is the committed pinned-package scriptlet,
  the matching dry-run log counts and the complete synthetic four-group test.
  The lead's next authorized dry run remains the real-image check.
- `PROGRESS.md`, pending bindings and `os/owner-tools/` were not edited.
  `rebind.py` was not run. No commit, push, workflow dispatch, sudo,
  rpm-ostree, bootc or ostree command was run. No owner test module,
  inherited-homebrew, sysusers or whole-suite module was run.
- No unresolved finding, design change or open question remains for this fix
  round. The lead still owns rebinding, committing and the real-image replay.
