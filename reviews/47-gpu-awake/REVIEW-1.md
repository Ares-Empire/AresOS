Reviewed head `5d19dd82` using file reads and git only. Three findings:

1. **Blocking — parent death cannot interrupt a stuck CUDA call.**  
   [env.sh:224](/var/home/ares/AresOS-47-gpu-awake/mod/dev/env.sh:224): the holder checks its parent’s pidfd only after initialization and context retention. If the script is killed while a CUDA call hangs, its 30-second watchdog disappears. Likewise, parent death invokes `cuDevicePrimaryCtxRelease_v2` without an independent timeout. `TimeoutStopSec=5` only applies once someone requests a scope stop; parent death does not request one. The holder can therefore remain alive, retaining GPU resources and the inherited lock.  
   **Fix:** supervise the CUDA worker independently of both the calling shell and its CUDA calls, with parent-death detection and bounded termination by owned PID/pidfd. Test parent death during initialization and a hanging release; the existing harness tests neither combination.

2. **Blocking — killing the lock-holding script leaves the game scope running.**  
   [env.sh:244](/var/home/ares/AresOS-47-gpu-awake/mod/dev/env.sh:244) and [client-test.sh:175](/var/home/ares/AresOS-47-gpu-awake/mod/dev/client-test.sh:175): SIGKILL bypasses the shell’s EXIT trap. The holder then releases its context, but nothing stops the separately created game/compositor scope. Those processes can continue using NVIDIA and retain the inherited lock indefinitely if hung. The pidfd protects the holder alone, not the complete aborted run. This is an unmet abort requirement, even though orphaned client scopes predate this patch.  
   **Fix:** make parent death trigger cleanup of all invocation-owned processes, stopping the client before releasing the holder. Verify with a persistent stand-in client and SIGKILL of the script, checking both process exit and lock reacquisition.

3. **Should-fix — holder failure after readiness is silently ignored.**  
   [env.sh:253](/var/home/ares/AresOS-47-gpu-awake/mod/dev/env.sh:253): monitoring ends immediately after `READY`. If the holder crashes or its scope is killed during probing or gameplay, the client continues without the context that enforces the cycle bound. It can resume the baseline’s repeated power cycling and still report success.  
   **Fix:** monitor holder lifetime throughout the run and abort with cleanup if it exits unexpectedly. Add a stand-in test that kills the holder after readiness while the client remains running.

The saved measurements **support one observed wake-up and suspend in each complete changed run**. Both CSVs contain one `suspended → resuming → active → suspending → suspended` sequence, with no suspended-counter increase during the continuous active interval. Their counter deltas match the report; the baseline contains eight cycles.

The report clearly states that historical logs cannot establish cycle counts, causation, HDMI recovery, or long-term stability. However, its unconditional claim that killing the script cannot orphan the context exceeds its lifecycle evidence: the parent-kill harness waits until readiness, uses an immediately returning release, and starts no game.

Static inspection found the lock acquisition, 6 GiB/exit-75 checks, headless isolation, and automatic NVIDIA→Intel→software ordering preserved. Missing NVIDIA/UVM takes the fallback path. The patch adds no privileged operation, protected-system write, or process-name-based kill.

CHANGES-NEEDED