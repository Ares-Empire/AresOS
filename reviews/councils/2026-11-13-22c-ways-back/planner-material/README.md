# Planner material

- `shapes.py`: the planner's read-only script. It runs today's `qualified_state` and `preflight_recovery` over every pair and triple ordering, using the repository's own test model.
- The council also read two upstream source files that are not kept here:
  - bootc 1.16.13, `crates/lib/src/status.rs` (the rollback slot and the `rollbackQueued` rule);
  - ostree 2026.4, `src/ostree/ot-admin-builtin-set-default.c`.
  Where a member report cites `planner-material/bootc-1.16.13-status.rs` or `planner-material/ostree-2026.4-ot-admin-builtin-set-default.c`, it means these files at those versions.
