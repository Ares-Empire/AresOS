Reviewed `d3babf1f…fa35a3a3` against decision 24 in `origin/main`.

**Blocking findings:** none.

**Should-fix findings:** none identified within this diff.

All six public send/delete rules remain generated and required, including Mail unsubscribe and both testapp actions. Generated server names and exposed tool names agree. The relaxed boundary still rejects missing/misnamed rules and retains protected, root-owned, non-writable, non-symlink path checks.

Saved native CI artifacts show 14 required denials against user/project/local allows, `PreToolUse` allows and skip-permissions mode. Six positive controls demonstrate working sends without the managed ask. Independent receiver logs match. The four `PermissionRequest` approvals fall within the explicitly accepted residual.

Service-written questions, exact approval binding, expiry, replay prevention, credential isolation and untrusted-content marking remain intact. No shipped action uses the trusted-send exemption; its new submission guard refuses absent checks and anything other than literal `True`. A real owner-only recipient-list implementation remains future work.

The removed controls concern the superseded containment model; I found no additional tool-level bypass introduced by their removal.

Locally, generated-artifact verification and 18 read-only Python checks passed. Supplemental service checks used mocked storage/policy reads, not filesystem integration. I did not edit files, run containers, or rerun the native/Mail suites.

SAFE