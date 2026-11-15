# Scoped security re-check — c78178dd

Reviewer: gpt-6-astra (xhigh), read-only.

Both FIXes are closed. Saved native queries bypass named-property shadowing;
collection finishes before mutation. Refreshed holds retain outstanding records
and still respect subsequent page changes. **166 exact-source reader/page tests
passed**, no failures/skips. The reviewer independently reran native-query,
retarget and detach removal probes: each baseline passed and each mutation failed.
The retained 281-mutation record was inspected, not fully rerun.

No additional defect found within the fixes or touched safety paths. Browser
replacement, latency and final readiness remain pending. No edits, local
browser/profile/container or GitHub mutation.

SAFE
