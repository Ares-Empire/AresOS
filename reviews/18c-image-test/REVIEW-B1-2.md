Re-checked `4121ea7a` against `6edaf6a6`. No files modified.

1. **Fixed — each DAA send is judged independently.** The [suite](/var/home/ares/AresOS-18c-build/control/boundary/interactive_suite.py:89) checks arrival deltas `[1, 0, 0]`, success/refusal content, tool-use IDs and approval inputs. The verifier invokes the same checks. The swapped-evidence regression passes; in-memory mutations of both modes’ saved evidence are rejected.

2. **Fixed — persistence and evidence checks gate PASS.** [Before each case’s PASS](/var/home/ares/AresOS-18c-build/control/boundary/interactive_suite.py:333), the suite checks the evidence, including the DAA grant after sends 1 and 2, before restart, at the restarted process’s rendered prompt, and after send 3. The remaining verifier checks are enforced by the suite’s live checks or final PASS gate. I found no PASS claim dependent solely on the separate verifier.

3. **Fixed — VSOCK wording matches the evidence.** The [comment](/var/home/ares/AresOS-18c-build/control/boundary/hostile.py:27) says timeout/reset means no established connection and explicitly excludes receiver-backed VSOCK isolation evidence. The classification code is unchanged.

The fix diff changes no forbidden path, `os/` file, unit or pin test, pinned PermissionRequest outcome, other case’s expected behavior, or workflow permission.

No new findings caused by the fixes.

Verification: six read-only interactive tests and the service pin test passed; twelve in-memory malformed-evidence checks were rejected. Both final-head boundary artifacts pass the verifier with 17 cases. Saved logs confirm both boundary attempts passed and Control base passed 305 tests.

SAFE