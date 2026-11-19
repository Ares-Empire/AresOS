The recommendation is supported by the sampled data, but the rig needs a cleanup fix, and the `/sys` requirement conflicts with the brief.

1. **Blocking — safety-contract conflict:** `reviews/49-memory-cuts/rig/scope.py:41` and `:51` write `memory.reclaim` and `cgroup.freeze` under `/sys/fs/cgroup`. These are deliberate, scope-checked writes required by `briefs/49-memory-cuts.md:26`, not arbitrary host tuning. Nevertheless, criterion (4)’s literal prohibition is not satisfied. **Fix:** explicitly reconcile the requirement with this narrow exception, or disable these actions if the blanket prohibition must stand. Preserve the recorded experiments.

2. **Should-fix — input-reader failure can prevent cleanup:** `reviews/49-memory-cuts/rig/measure.sh:149` opens the input FIFO with a blocking shell redirection. If `vinput.py` dies before a standing, flight, chat or screenshot command, that open can wait indefinitely. The controller then never reaches its cleanup trap and retains the shared client lock. The bounded writer in `wake.py` fixes only the wake path. **Fix:** use a bounded input helper for every command, fail on reader/compositor loss, and exit through the existing owned-process cleanup.

3. **Nit — frame claims cannot be independently reconstructed from committed evidence:** `reviews/49-memory-cuts/rig/analyze.py:166` omits raw frame timestamps. `verification/arena-flight-outlier.json` records the decisive 19.948 ms value, but not its two underlying timestamps. Tables and audit repeat derived summaries. **Fix:** retain privacy-safe timestamp excerpts for decisive outliers and, ideally, the comparison windows; otherwise state this public-reproducibility limit explicitly.

The remaining checks were satisfactory:

- **Scope:** all 2,798 changed files are within `reviews/49-memory-cuts/` plus the supplied brief. The brief matches its initial commit. No product code or settings changed.
- **Numbers:** sampled snapshots and GC logs agree with summaries and `TABLES.md`. Final flat RSS savings are **167.3/295.0/281.0 MiB** settled/flight/covered. FerriteCore’s standing heap minima improve by **9/12 MiB**, while flight RSS increases by **95/12 MiB** and covered RSS by **106/19 MiB**. `cover-r600-1` confirms **804 MiB** covered RSS and an **80.081 ms** GC pause.
- **Recommendation:** keeping current settings, retaining arena cap 2 only for follow-up, and rejecting FerriteCore and forced cover actions are supported. The report plainly acknowledges failed frame comparisons, both failed frozen returns, global zram attribution limits, single-run NMT-off uncertainty, and missing real-session validation.
- **Public exposure:** no credentials, tokens, personal home paths, hostnames, personal files or installed-app inventories found. Host context contains selected executable counts. All 13 images are test-game screenshots; no jars or other binary payloads were committed.
- **Size:** committed package contents total **20.46 MB across 2,797 files**, including **9.16 MB of screenshots**. That is reasonable for 65 retained attempts; wholesale trimming would weaken the evidence. Optional cleanup: consolidate the byte-identical FerriteCore screenshots and drop the interrupted-Nether screenshot, retaining its failure data.
- **Process safety:** inspected stop commands target captured child PIDs or run-specific units. No root requirement or writes under `/proc` or `/etc` found.

Review was read-only at `b670d57b`; no build, Gradle, tests, game or rig scripts were executed.

CHANGES-NEEDED