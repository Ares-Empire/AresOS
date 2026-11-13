1. **Fixed — Chrome startup and sockets.** The brief now gates A/B2 on Chrome’s merge, installs `build-id.json` and `qualification.json`, and uses the merged daemon’s socket modes. These match the supplied Chrome worktree: `Chrome.__init__` loads those files, and `daemon.py` sets act/chrome to 0666 and admin to 0600.

2. **Fixed — Ordinary Claude Code use.** [B2 check 6](/var/home/ares/AresOS-18c-image-test/briefs/18c-image-test.md:267) now calls the owner’s fixture MCP tool alongside his hooks, with the service healthy and stopped. It requires a deadline, reminder/request counts, and a clean turn after restarting. This covers the failure behavior in `hooks.py`.

3. **Partly — Folder policy.** The revision adds image-created folders and an installed-entry-point attachment import/save check. However, its new two-folder policy conflicts with the existing install-map requirement for three folders; see the finding below.

4. **Fixed — `gh` resolution.** [Part A item 3](/var/home/ares/AresOS-18c-image-test/briefs/18c-image-test.md:118) explicitly authorizes extending `os/ci/check-resolve.sh` to report and resolve Fedora’s `gh`, preserving unrelated locked packages. That supplies the missing authorized work; the current script indeed never resolves `gh`.

5. **Fixed — Pending-operation cleanup.** [“A clean baseline”](/var/home/ares/AresOS-18c-image-test/briefs/18c-image-test.md:320) now requires preserving evidence, cancelling reserved work, acknowledging its notice, and asserting nothing pending. Check 4 explicitly invokes that cleanup. This matches `engine.py` and `test_cancel_expire_only_reserved_and_notices`.

6. **Fixed — Model script and bypass warning.** [B1](/var/home/ares/AresOS-18c-image-test/briefs/18c-image-test.md:198) now specifies scripts per case, distinguishing Stop continuations from subsequent owner prompts so the second send can execute. It also correctly limits what `precedence.py` seeds and requires discovering the pinned binary’s bypass-warning setup first.

**Revision-caused finding — should-fix:** The configured folder list is contradictory. [Part A item 2](/var/home/ares/AresOS-18c-image-test/briefs/18c-image-test.md:106) still requires Documents, Downloads **and Desktop**, while new [item 8](/var/home/ares/AresOS-18c-image-test/briefs/18c-image-test.md:137) and the builder details specify only Downloads and Documents. Following the install map would leave Desktop allowed but unprovisioned—the same missing-directory problem identified originally. `FilePolicy` uses the configured roots literally and creates none. **Fix:** update item 2 to name only Downloads and Documents, consistent with the revision’s default policy and folder-creation requirements.

No other revision-caused findings. No files modified.

CHANGES-NEEDED