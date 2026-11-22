# Review 4: final check of the test bench's design note

**Verdict:** READY

| REVIEW-3 finding | Resolved or safely deferred | Evidence |
|---|---|---|
| 1. Laptop and home-network boundary | Yes | Laptop internet stays disabled until Step 4 verifies fail-closed egress against controlled endpoints on every path, including fetch and build. Each `podman exec` uses the verified unprivileged user, with clean credentials, proxy and DNS settings. [§6](docs/design/TEST-BENCH.md#L464) |
| 2. Memory pressure and watcher failure (R1.2, R2.2) | Yes | The shared lock covers all four entry points. The laptop VM stays disabled until Step 6 verifies capped process membership, shutdown on watcher loss, swap growth and game responsiveness with an offline fixture. Timing comes from measurements. [§3](docs/design/TEST-BENCH.md#L213), [Step 6](docs/design/TEST-BENCH.md#L524) |
| 3. Disk cap and cleanup (R1.2) | Yes | Each phase must fit its enforced peak while preserving the SSD reserve. The external lock covers runs and cleanup. Step 2 settles the store location before writes and tests active-store refusal and interrupted cleanup. [§3](docs/design/TEST-BENCH.md#L236), [Step 2](docs/design/TEST-BENCH.md#L518) |
| 4. Native execution and returned evidence (R1.1) | Yes | The native list stays empty and refusal precedes import. The desk validates fixed paths, regular-file types, counts and sizes before writing returned evidence. Step 9 tests malformed returns. [§2](docs/design/TEST-BENCH.md#L43), [Step 9](docs/design/TEST-BENCH.md#L531) |
| 5. Hosted acceptance and release isolation (R1.3, R1.6) | Yes | Step 1 requires a no-NIC boot, active auto-login and authenticated helper health before and after a new boot ID. The negative case preserves import and `--list`. Dispatch exclusivity, a distinct tag, a planted-file raw-layer check and bounded evidence with raw guest output excluded from job logs are explicit. [Step 1](docs/design/TEST-BENCH.md#L511) |
| 6. Local build order and `tree` (R1.7) | Yes | Egress and memory gates precede local builds. Step 7 defines the offline import and bounded scratch before Step 8 uses them. The `tree` assertion moves to Step 6. [Build plan](docs/design/TEST-BENCH.md#L496), [Step 7](docs/design/TEST-BENCH.md#L528) |
| Earlier closed findings (R1.4, R1.5, R2.1) | Yes | The recorder retains only validated fields and uses fixed error reasons. The desk keeps its output override and separate `apps_running` view. The VM home click still waits for 23c and requires its own output override. [§2](docs/design/TEST-BENCH.md#L102), [§3](docs/design/TEST-BENCH.md#L134), [§5](docs/design/TEST-BENCH.md#L361) |

## Notes

- Revision 3 adds no identified real-harm path to the owner’s session, files, disks, credentials, network, memory or a shipped image. Sudden memory spikes, public IP and DNS visibility if laptop internet is enabled, and the limits of hardware readings are recorded as Known limits. [§9](docs/design/TEST-BENCH.md#L590)
- Step 1 can be briefed as written. Its hosted acceptance criteria are independent of the later laptop gates. The supervisor starts the actual helper in `SETUP`, and the helper supports an authenticated `list_apps` request. This was a read-only design review. [Supervisor launch](os/config/usr/libexec/aresos-desktop#L1982), [Helper protocol](os/config/usr/libexec/aresos-shell#L3376)
