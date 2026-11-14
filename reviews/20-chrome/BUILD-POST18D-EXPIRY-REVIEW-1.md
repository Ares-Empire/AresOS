# Scoped package review — de9bf8d8

Reviewer: gpt-6.1-sol (high), read-only.

FIX: SQLite text substr stops at embedded NUL in a _sha256 key. A retained
reference such as reference\u0000_sha256 is pinned by Python but omitted by the
new SQL enumeration. Exact-source in-memory expiry preserves the old file with
old pins and unlinks it with the new callback. Match suffixes as bytes and add
nested-NUL equivalence and actual old-file retention regressions.

Other namespace cases match original behavior across12 UTF-8 prefixes including
NUL/Unicode boundaries and non-text keys. Enumeration failure precedes unlink.
No further FIX found. No edits or external state changed. Measurements, targets
and final acceptance remain pending.

CHANGES-NEEDED
