# 42 step 1: fix check of REVIEW-3 (Codex gpt-6-astra high, 2026-11-17)

Checks `699fb9a6` (REVIEW-3 fixes, notes in FIXES-3.md) at merged head `3fad2829`. Read-only sandbox: test errors from temporary-file creation are environmental.

**Five findings are fixed; finding 3 is partly fixed. Two alternatives-validation holes remain.** Reviewed `7ff6df15..699fb9a6`; no files changed.

1. **Fixed — missing RPM files.** The complete inventory is checked against every non-ghost record, including paths absent from both images. Nonzero or unexpected `rpm -V` output now stops the result. PROGRESS records clean verification in dry run 4, supporting compatibility with the four added packages.

2. **Fixed — generated-file exceptions.** The globs became ten exact paths, plus the RPM database. Both sides must have the specified type, ownership, mode and empty xattrs; additions and removals are rejected. The filenames match the recorded generated-path list. I could not independently replay the real inventories to confirm every newly required metadata value and before/after presence.

3. **Partly fixed — alternatives associations.** Swapped links against an unchanged record, malformed records and mixed choices are rejected. However, the record itself remains an unverified source of associations, and public command links are not required to exist. Details below.

4. **Fixed — Prism inventory.** The independently hash-pinned archive now supplies the complete typed inventory, including modes, symlink targets and required presence. Extraction mirrors `build.sh` and its three exclusions. The production archive comparison remains unverified here.

5. **Fixed — schema lookup metadata.** Exact rebuilt-byte comparison covers hashes, buckets and bloom filters, including when the compiled file never enters the diff. The release job’s privileged wrapper can run Podman against the already-built image; Python and the compiler remain installed. `/tmp` is writable, and its `noexec` flag does not prevent executing the compiler under `/usr/bin`.

   Determinism is supported by [GLib’s sorted input processing](https://github.com/GNOME/glib/blob/2.88.4/gio/glib-compile-schemas.c), the same image/compiler/inputs, and PROGRESS’s recorded byte-identical rebuild. I found no execution or determinism defect, but did not run the actual container.

6. **Fixed — jar-pin modes.** Both Git entries must now be regular `100644` blobs before the JSON-only exception applies.

The remaining issues are:

- **Should-fix — a consistently wrong alternatives record and links pass.** [os/ci/release_diff.py:1196](os/ci/release_diff.py:1196)  
  Change the admin record’s master target to `…/bin/keytool`, its keytool target to `…/bin/java`, and swap the corresponding `/etc/alternatives/` links. Both targets still belong to added packages. My in-memory probe accepted the record and all four links, so invoking `java` would invoke keytool. The new tests change links but leave the record unchanged.

  **Fix:** bind the complete group/name/public-path/target mapping to independently reviewed expectations derived from the pinned package scriptlets or a reviewed manifest. Test changing the record and links together.

- **Should-fix — missing public command links remain invisible.** [os/ci/release_diff.py:1206](os/ci/release_diff.py:1206)  
  Keep a correct record and `/etc/alternatives/{java,keytool}`, but omit `/usr/bin/{java,keytool}`. The group still validates; my separate probe accepted every remaining changed path. Missing links absent from both images never reach `alternatives_rule()`, and the new completeness check excludes ghost records. RPM verification also suppresses missing-ghost errors. [RPM verification source](https://github.com/rpm-software-management/rpm/blob/rpm-6.0.0-release/lib/verify.cc)

  **Fix:** validate the presence, metadata and target of every public link required by the selected choice, independently of `changed`. Require absent slaves to have no public link. Add missing-public-link tests.

Verification: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s os/tests -p 'test_release28.py'` reported **75 tests, 55 errors** from read-only temporary-directory creation; those are environmental errors, not code failures. The other 20 passed. In-memory probes reproduced both holes. `git diff --check` passed. I could not replay all 1,585 real paths, so no claim of full dry-run compatibility is made.

CHANGES-NEEDED