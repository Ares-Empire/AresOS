# 14u: The two console findings are the public Fedora kernel signing-key fingerprint; run qualification 2

Follow-up on branch `pkg/14-owner-tools`. Briefs 14 to 14t still apply, with the change below.

## Integrator classification (I looked at both lines privately; no value is reproduced here)

`evidence/two-disk/live-ui-probe-boot-console.txt` lines 497 and 530 are the kernel's standard boot messages `Loaded X.509 cert 'Fedora kernel signing key: <fingerprint>'`. They're printed twice, for the compiled-in certificates and the module certificates.

That is the public fingerprint of Fedora's kernel signing certificate, which every Fedora kernel prints at boot. It isn't a credential. It's the same class the repo's `.gitleaks.toml` already allowlists for committed captured boot consoles: "kernel-certificate fingerprints … look like API keys".

**Rule from now on, for artifact scans only:**
- A finding counts as this class only if the whole matched line is exactly a kernel `Loaded X.509 cert '…signing key: <hex>'` message in a captured boot console. Record each one in the REPORT.
- Any other finding outside the 14s ISO listing is a STOP.
- Don't add ignore entries and don't change the privacy workflow. Don't commit the raw consoles beyond what the existing allowlisted paths already permit.

## Then

- **The owner's $1 Actions budget is still on**, with prevent true. Probe 10 passed on the pushed head `bbf228c`.
- Recheck the ledger, billing and the budget. Then dispatch the **second qualification on that same head**. No push is needed, so don't push.
- Any stop: report it, no rerun.
- When acceptance is met, put the closing reservation back to 12 and the reserve back to 150 in a final commit, push once, and mark PR #13 ready for review. Then say the run is over, so the owner sets the budget back to $0. Don't merge.

**Model:** gpt-6.1-sol, xhigh (resuming the package 14 Codex session).
