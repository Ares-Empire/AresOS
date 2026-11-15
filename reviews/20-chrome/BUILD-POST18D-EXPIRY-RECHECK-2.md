# Scoped package re-check — e0cc9846

Reviewer: gpt-6.1-sol (high), read-only.

Hash-retention FIX closed. Exact-source hash/namespace queries match Python and
old SQL in UTF-8/UTF-16LE/UTF-16BE, including embedded NULs. Removing NUL-safe
suffix matching or legacy-encoding fallback reproduces failures. Eight gate
tests pass; sparse diagnostics retain mandatory20-sample checks. No further FIX.
Measurements/final acceptance pending. No edits or external state changed.

SAFE
