# Scoped security review — de9bf8d8

Reviewer: gpt-6-astra (xhigh), read-only.

FIX: embedded-NUL _sha256 keys lose file pins under SQLite text substr. Exact
production-method and in-memory expiry probes confirm deletion with new pins and
preservation with old Python pins. Use NUL-safe suffix matching and retain an
actual old-file regression.

FIX: daemon_expiry_inside_sample is deliberately sparse (only complete sweeps
inside one marker), but the gate requires20 samples for every provided block.
A valid one-sample diagnostic makes a nominal gate fail. Allow the explicit sparse
diagnostic while keeping required samples strict. Namespace, malformed-state,
pre-unlink enumeration-failure and diagnostic-isolation probes otherwise pass.
Targets remain unapproved. No edits or browser/profile/container access.

CHANGES-NEEDED
