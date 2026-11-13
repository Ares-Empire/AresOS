1. **Should-fix — new status wording is insufficiently pinned.** In [test_owner_path.py:550](/var/home/ares/AresOS-27b-laptop-update-record/os/tests/test_owner_path.py:550), substring checks leave several new facts unprotected. In-memory mutations still passed the changed status test when:
   - tools version `2` became `20`;
   - the post-restart check became “not confirmed” in both rows;
   - `ares` became “not in `wheel`”;
   - corrected stock became “no longer pinned”;
   - the new “as of” date reverted.

   This violates the brief’s requirement to reject claims beyond or below the record. Compare the complete new evidence clauses and release statements against expected wording, add mutation checks for these cases, and refresh the test’s pending hash.

The actual document additions match the supplied evidence. The 250-path binding audit found exactly the three recorded changes, with matching hashes. I found no binding bypass involving wrong hashes, duplicate or unbound paths, unchanged waiting files, or unrecorded content changes. The pending scanner uses the active tables correctly; the step-limits change removes only the stale assumption. Nothing under `os/manifest/ci/27/` changed.

Verification: step-limits passed 4/4; other targeted modules encountered read-only temporary-file errors. No files were edited.

CHANGES-NEEDED