Reviewed head `9c5e940e` read-only. No blocking or should-fix findings.

- **Nit — `reviews/49b-arena-rerun/REPORT.md:209` and `reviews/49b-arena-rerun/verification/final-local-checks.json:5`:** `bash -n file1 file2…` checks only the first script; remaining filenames become arguments. The recorded command therefore does not establish syntax coverage for every shell script. **Fix:** check each file separately in a loop and update the verification record.

The requested checks otherwise hold:

- **Rig repair:** `94f0e416` precedes the pass-line commit. FIFO writers use nonblocking opens and bounded atomic writes. Reader/compositor monitoring interrupts waits and foreground commands into owned-process cleanup. The three stand-ins exercise reader loss before standing input, mid-flight reader loss, and compositor loss; retained results show nonzero exits, exited processes/scopes and successful lock reacquisition. Final hardening predates the first measurement.
- **Frozen criteria:** `2ddcb93f`, committed at **08:57:09 +01:00**, precedes fixture construction and the first measurement at **09:44:36**. The pass-line/plan prefix is identical in all 14 subsequent commits. All 18 measurements identify `32bcdb55`; the 30 recorded runtime-source hashes match.
- **Independent recomputation:** settled savings are **285, 152, 270, 214, 189, 318 MiB**, median **242 MiB**. Creation counts are control **1+1=2**, candidate **2+3=5**, exceeding the allowance of **3 by 2**. Flat flight >17 ms counts are candidate/control **0/2**, candidate maximum **13.550 ms**. Nether counts are **0/2**, candidate maximum **16.272 ms**, with both routes recording 1200 ticks. Safety counters are clear; maximum post-join GC is **18.698 ms**. Snapshots, frame timestamps and tables agree.
- **Order and conditions:** timestamps confirm **AB, BA, BA, AB, AB, BA**, then creation **AB, BA**, then Nether **AB**. All 18 measurements and two utilities remain recorded. No sampled external build/game interference appears; the scheduler retains and repeats contaminated attempts. Package 47’s card holder and the restriction to within-package comparisons are explicitly documented.
- **Deadlock:** both dumps support the reported mounted-rejoin shutdown stall. The report clearly acknowledges the missing second passing full qualification. No product test or assertion changed.
- **Scope/privacy:** only the permitted brief and review directory changed. Added content totals **9.83 MiB**; the only binaries are three inspected test-game screenshots. I found no credentials, personal paths, hostnames or jars. Measurement settings reject inherited reclaim/freezer actions, and cleanup targets owned processes/scopes.

No build, Gradle, game, client test or rig script was executed during this review. **NOT QUALIFIED** is supported; product settings remain unchanged.

SAFE