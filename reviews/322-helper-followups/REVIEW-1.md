## Review of PR #134 at `ac183603`

No blocking findings. The three fixes meet the brief’s functional goals. The legacy replay behavior and the distinction between outstanding checks and live threads are worth documenting.

| Severity | Where | Finding and fix |
|---|---|---|
| nit | [os/config/usr/libexec/aresos-shell:4113](os/config/usr/libexec/aresos-shell#L4113) | Ambiguous desktop launches replay as `background` to 1.0 and 1.1 clients, even in a desktop-only session. The same replay returned `focused` at the base commit. This follows the brief’s attribution rule and preserves the wire format. Clarify that the legacy compatibility statement allows this change in reported state. |
| known limit | [os/config/usr/libexec/aresos-shell:2358](os/config/usr/libexec/aresos-shell#L2358) | A finishing worker releases its slot before signalling completion and exiting. Pausing teardown reproduced five live threads with four outstanding checks at both the base and head. The bound on checks that can stall holds. Document the bound as four outstanding checks. |

- **Restart attribution.** Ambiguity is computed across desktop and view adoptions of the same reviewed app. The focus loop suppresses `focused`, including on replay. Unambiguous adoptions, fresh launches, and discovered apps retain their focus behavior. Final transitions and journal eviction clear the ambiguity marker.
- **Home cursor.** A revision change or any change to the ordered visible IDs invalidates the cursor. I verified reinstallation and deferred filtering at the same home revision. Unchanged snapshots keep their page boundaries, and `list_apps` cursors are unchanged. A socket probe confirmed that laptop home retried from page one and saved all 11 remaining houses.
- **Check reserve and protocol.** Views can start three outstanding checks in total, and the desktop can use all four slots. Joins happen before either cap and count against the starter. Completion and thread-start failure release the slot. The wire vocabulary is unchanged.

## Verification

| Command | Result |
|---|---|
| `python3 -m unittest discover -s os/tests -p 'test_aresos_shell*.py'` | 419 tests in 33.687s, `OK`. The harness emitted socket `ResourceWarning`s. |
| `python3 -m unittest discover -s os/tests -p 'test_aresos_laptop_home*.py'` | 54 tests in 60.402s, `OK (skipped=3)`. |
| `git diff --check 76dd89b5 ac183603` | Passed with no output. |

The targeted probes passed. I left the worktree unchanged and did not run either sudo-dependent suite. A live two-screen session remains unverified.

SAFE