# Package 43, review 11: fix check of review 10 (Codex gpt-6-astra, high, read-only, on a93c07a5)

Both fixes check out. Memory-backed probes confirmed first-value precedence, unchanged environment bytes and no locale coercion. The complete refusal block accepted the correct dispatcher and rejected all 14 caught-attempt mutations. Reverting each fix made its regression assertions fail.

Standard tests encountered environmental temporary-file errors and the expected word-set failure. No image integration ran; `runuser` used a stand-in. Syntax and whitespace checks passed. No files changed.

SAFE