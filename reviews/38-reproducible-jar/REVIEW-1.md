Reviewed `5717369c..639fd52e`, excluding `mod/dev`, read-only. No Gradle was run. The jar implementation and hash evidence look sound; the concurrency key needs correction.

1. **Should-fix — unrelated runs can cancel each other.**  
   [`.github/workflows/mod.yml:14`](/var/home/ares/AresOS-38-reproducible-jar/.github/workflows/mod.yml:14) uses only the source branch name. Two fork PRs named `fix` share `mod-fix`; a fork PR from `main` shares `mod-main` with pushes to the repository’s `main`. With `cancel-in-progress: true`, one can cancel another’s validation. GitHub concurrency groups operate across the repository. [GitHub documentation](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)

   **Fix:** use a workflow-specific key containing `github.ref`, such as `mod-${{ github.workflow }}-${{ github.ref }}`. PR refs include their PR number.

2. **Should-fix, pre-existing and separate — startup replay includes newly submitted opens.**  
   [ShellClient.java:327](/var/home/ares/AresOS-38-reproducible-jar/mod/src/main/java/dev/aresos/shell/ShellClient.java:327) publishes `connection`, invokes listeners, and completes readiness before iterating `opens`. An open submitted during that interval gets its ordinary send plus replay. The probe correctly forces this ordering: its listener waits for the first transmission while the reader cannot yet process its reply.

   **Real effect:** duplicate wire requests under the same ID and flaky exact-count tests. The real helper checks its journal before launching, so this does **not** launch a second app or repeat activation.

   **Smallest fix for this startup defect:** move both replay loops before publishing `connection` and announcing readiness, keeping sends on the writer thread. Moving only `firstAttempt.complete()` leaves listener and connection-based callers exposed. **This PR should not wait for that separate runtime fix**; failing tests must continue to fail.

The remaining checks support the implementation:

- **Jar contents and manifest:** independently compared the retained baseline, reordered, fixed, laptop and CI jars. Only the manifest payload changes from baseline to fixed. Manifest attribute membership and ordinary values survive; client-entry membership, including resources, survives sorting. The result retains `Manifest-Version` first, CRLF termination and valid line folding. The reverse-creation experiment demonstrates the reported Loom defect, while the report correctly avoids claiming direct comparison of the unavailable historical binaries.
- **Reproducibility controls:** archive order, timestamps and permissions are fixed; UTF-8, en/US and UTC are configured. Existing Git attributes enforce LF for the packaged text. The checked outputs contain no new path/user/host metadata. CI pins the exact Temurin image digest; the wrapper pins Gradle and its distribution checksum. Laptop reproducibility remains conditional on using the documented JDK build.
- **Other archives:** `sourcesJar` receives both archive and manifest normalization. Loom’s remapped jar task classes also extend `Jar`, so the rules cover them. This configuration produces no remapped jar; the cross-machine proof and CI comparison cover the primary mod jar only.
- **CI:** both clean checkouts actually compiled and packaged their outputs; neither restored mod compilation or jar tasks from a build cache. Shared dependency/Loom caches did not invalidate this comparison. Permissions, pinned actions/image, fork execution, mismatch failure through `cmp`, artifact upload and preservation of test failures are otherwise correct. The path patterns include every `mod/**` path, subject to GitHub’s documented large-diff filtering limit. [GitHub documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#git-diff-comparisons)
- **Evidence:** [final-head run 43481913258](https://github.com/Ares-Empire/AresOS/actions/runs/43481913258) succeeded with both builds executing. Both logged hashes, the retained CI artifact and the laptop jar equal:
  `dacae565e4f837faf5323d6cc8fb1efce1acc03577fcb904a2c0fa1a8f5a63be`.
  Both retained CI unit-result sets contain 56 passes, six skips and zero failures; both server suites passed 38 tests.
- **Committed files:** the package-only changes contain small text files and intentional review evidence. No binary build output, large downloads, secrets or personal data were found.

CHANGES-NEEDED