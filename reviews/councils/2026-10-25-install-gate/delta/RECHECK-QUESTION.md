# Delta re-check: findings A and B only

**What is reviewed:** commit `e2ceeaf` on `pkg/15-owner-path`. It merges package 14's fix commits (`8eab7f6`, `754cf7c`; brief `14n`) into package 15 (brief `15c`).

**Your delta verdict:** [VERDICT.md](VERDICT.md), GAPS-FOUND (2):
- **A** (blocking): the disk helpers read a flat `lsblk` list but walk a device tree.
- **B** (should-fix): the documented layout PASS lines didn't match the CLI.

**The question:** is each one now CLOSED, judged against your own Check line?
- **For A:** the tree request and its validation in `os/owner-tools/media.py` and `owner.py` (and the payload copies); the fixtures and tests; the native loop-image test that runs on GitHub's runner on 1 November. That test and the VM qualification are pending; say what they must prove.
- **For B:** the entry point's output, every documented expected PASS line in INSTALL, INSTALL-PROCEDURES, INSTALL-REFERENCE and EMERGENCY, and the stdout comparison test.

Also say whether these fixes broke anything they touched: the fingerprint everywhere, the payload/source equality, the guarded refusal paths, the step-5 gate. Don't start a fresh hunt elsewhere.

End with one line: **DELTA-CLEAN** or **GAPS-FOUND (n)**.
