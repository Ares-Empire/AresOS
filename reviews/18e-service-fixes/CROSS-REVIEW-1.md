**No new blocking, should-fix, or security fix findings.** Reviewed `689c0778..bc1d7918`, excluding main-only differences by checking merge commit `9324224a`. No files modified.

The package checks out:

- **Connect retry:** only failed `connect()` calls with `ENOENT` or `ECONNREFUSED` retry. Sending happens afterward. A lost response cannot enter that retry loop; changing requests retain `unknown`. `service_busy` and `setup_error` neither retry nor trigger the fallback catalogue.
- **Deadlines:** future reservations use their remaining time plus 5 ms; the 0.1 s floor applies only to overdue deadlines. Deferred notices retain earlier future reservation deadlines. Submission independently rejects expired approvals.
- **Start limit:** five immediately failing starts, separated by two-second restart delays, exhaust the 30-second window at roughly ten seconds. This supports the reported immediate-start-failure case; it is not a universal 15-second bound for failures preceded by lengthy startup work.
- **Sockets:** final names appear after chmod and listen. Normal failures remove the temporary socket; a kill can leave it behind, but the next successful start replaces it. Directory ownership prevents the owner’s processes from swapping these paths.
- **Catalogue/admin:** fallback tools retain the owner-only filter, and service authorization remains authoritative. Before the non-root admin refusal, only launcher checks, configuration/help reads and argument parsing run—not socket access or password prompting.

Security **known limits**, rather than fix findings:

- Another process running as the owner can read, plant or remove usage marks and `.told` files. These are informational state, not session authentication. Directory ownership/mode checks, descriptor-relative access, `O_NOFOLLOW` and `O_NONBLOCK` protect against other users and link/FIFO hazards; existing regular marker files are not individually checked for owner/mode.
- Parent identity capture and the nearest-non-shell rule prevent the supported nested-session and reparenting mistakes. Changed launch chains, resumed processes and CLI work can still miss reminders, as documented.
- Marked sessions can see other sessions’ pending work. The reminder and MCP sentence explicitly prohibit autonomous completion, cancellation, resending and acknowledgement; the outage notice contains no untrusted text. Prompt-injection risk remains the documented model-level limit, with no new authorization bypass here.

**The already-found Stop bug is closed on main.** Commit `91487807` (#91) checks usage before parsing input, replaces exit-2 failure handling with guarded JSON decisions, and wraps the managed Stop command. It also deliberately changes unreadable usage state to quiet. This fix is absent from `bc1d7918`; my verdict accounts for its presence on main.

Verification: four existing file-free unit tests passed; `control/generate.py --check` reported matching artifacts. In-memory probes passed for retry/send separation, the three connection codes and deadline calculations. Five actual #91 hook tests, loaded from Git into memory, passed; six shell-wrapper cases passed. I did not rerun filesystem-writing suites, systemd/VM tests, Chrome latency tests or hosted CI.

**Where I differ from Claude’s reviews**

I agree that their earlier findings are addressed at the reviewed final head. I found no additional unresolved defect they missed.

They caught one remaining **nit** I did not flag independently: [test_service_fixes.py:1079](/control/tests/test_service_fixes.py#L1079) imports `SOCKET_MODES` as its expected value. Changing admin’s mode to `0666` changes both implementation and oracle, so this test still passes. Fix: assert the literal expected modes independently. I agree this is a test gap, not an existing authorization bypass: the service still checks peer UID.

I disagree with the earlier recheck’s assurance that invalid Stop input cannot come from Claude Code itself. That assurance was insufficient; #91 now handles the known failure explicitly.

SAFE