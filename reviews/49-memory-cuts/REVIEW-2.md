No blocking, should-fix or nit findings in `54f4d0df..345d430e`.

1. **Writes:** `reviews/49-memory-cuts/REPORT.md` accurately lists the files, contents and six runs. Its ownership explanation matches `rig/scope.py`, the run-specific unit passed by `rig/measure.sh`, and `systemd-run --user`. Action records confirm the requests. No root use or other direct writes to the prohibited system trees were found.

2. **FIFO hang:** The report correctly describes the blocking open at `reviews/49-memory-cuts/rig/measure.sh:149`, cleanup not being reached, and the inherited lock remaining held. The required bounded helper, reader/compositor failure detection and cleanup exit would address it. Open questions explicitly requires applying and validating that repair before the arena-cap repeat.

3. **Frame evidence:** Independently recomputed from committed timestamps:
   - Flight: `273177150270838 − 273177130322909` = **19.947929 ms**, rounding to **19.948 ms**; paired control maximum **15.072578 ms**.
   - First 30 seconds: control/candidate have **1/3 gaps >33 ms**; town subwindows have **0/2**, with maxima **32.218305/101.973190 ms**.
   
   All six windows match committed summaries, including counts, maxima and p99. `reviews/49-memory-cuts/verification/decisive-frame-timestamps.json` contains only run identifiers, timestamp field names and integers. **431,153 bytes is reasonable; narrower windows are unnecessary** because complete windows allow independent verification of counts and maxima.

4. **Cleanup and scope:** All **52 local Markdown links** across the committed report files resolve. The FerriteCore images were byte-identical; the retained copy is unchanged. All **40 interrupted-control failure files** remain unchanged. Nothing outside `reviews/49-memory-cuts/` changed; existing tables, rig code and measurement data are unchanged.

Read-only Git/file/Python checks only. Both changed JSON files parse; `git diff --check` passes. No build, Gradle, client test, game or rig script ran.

SAFE