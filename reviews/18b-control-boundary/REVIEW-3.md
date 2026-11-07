Reviewed `743e6da..a8fa177`. REVIEW-2 findings **1 and 2 are fixed**. L4 now executes the hostile program inside Claude Code’s own sandbox, using only the two exact Bash grants plus the test environment entry. One blocking checker gap remains.

1. **blocking — L4’s mount comparison can accept a changed effective sandbox.**  
   **Where:** [boundary_assertions.py:52](/Users/pab/AresOS-18b-control-boundary/control/boundary/boundary_assertions.py:52), used by [native.py:239](/Users/pab/AresOS-18b-control-boundary/control/boundary/native.py:239).

   The parser discards mount IDs and parent IDs; both comparisons then collapse mounts by destination. Linux determines visibility through the parent graph, including whether an ancestor covers a mount. [Linux mountinfo reference](https://man7.org/linux/man-pages/man5/proc_pid_mountinfo.5.html).

   **Evidence:** using final-head retained mountinfo, I changed the read-only work mount’s parent from visible mount `533` to covered mount `526`. This leaves the visible work mount writable. Both `mount_view` and `policy_mounts` accepted the mutation as identical and still reported the work tree read-only. Consequently, the equality assertions do not establish L4’s required invariant.

   **Fix:** preserve and compare mount topology while normalizing session-specific identifiers. Resolve effective mounts through reachable parent chains before classifying paths; add a regression for a read-only mount hidden beneath a covered ancestor.

I independently confirmed both final-head workflows passed: [push](https://github.com/Ares-Empire/AresOS/actions/runs/42350528274), [PR](https://github.com/Ares-Empire/AresOS/actions/runs/42350532030). Retained evidence shows 127 blocked native routes per mode, unchanged hashes and zero arrivals. Six local regression tests and separate first/second-attempt mutations passed; I did not rerun Linux CI. No live sandbox escape was observed.

CHANGES-NEEDED