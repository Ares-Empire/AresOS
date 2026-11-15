# Scoped security re-check — 6e79f1f5

Reviewer: gpt-6-astra (xhigh), same independent security reviewer.

The credential-label FIX is closed. Root-local ARIA references and combined HTML
labels are checked before filled-state/value access. Exact-source **58 reader
tests passed**. Independent mixed credential/ordinary probes verified watched,
late and approved reads, replay refusal and sticky protection after label
removal. Removing either fix reached the forbidden getter and failed the probe.
The retained 270-mutation record has passing baselines and rejected mutations;
the reviewer inspected it without rerunning the entire audit. Linux fixtures
cover both initial type=text credential-label cases. The inventory fix copies
only test-driver files and introduces no production authority change.

No additional security regression found within the changed scope. Later changes,
Linux acceptance, measurements, targets and final readiness remain unreviewed.
No edits, local browsers/profiles/containers or GitHub mutations.

SAFE
