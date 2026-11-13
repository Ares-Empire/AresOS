# Scoped package review — bc738001

Reviewer: gpt-6.1-sol (high), read-only.

FIX: optional index creation runs before recovery reservations are reconstructed.
Its admission sees empty holds and can spend bytes promised to cancellation,
repair or restore. Move it after recovery and retain low-space fallback.
Exact-source admission probes pass with empty holds and correctly refuse with a
real cancellation reservation present. Indexed and fallback queries otherwise
match the original predicates across 264 mixed operation rows. No further FIX.
Remote measurements and final acceptance remain pending. No edits, browser/profile
or container access, or GitHub mutation.

CHANGES-NEEDED
