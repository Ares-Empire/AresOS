# Package 43, review 15: step 5a, the R28 bridge (Codex gpt-6-astra, high, read-only, on b6625761)

- **Must-fix — [pending-rebind.json:192](/var/home/ares/AresOS-43-aresos-command/os/manifest/ci/16/pending-rebind.json:192):** `unwalked_commands` contains only `newest`. Add `newest-routine`, `reboot-routine`, and `check-routine`, retaining them until step 6 walks them. None is exercised by the current harness, so `test_owner_equality.py:280` will reject them once temporary-file creation works. This is an additional failure beyond the two deliberately red tests. `PROGRESS.md:947` incorrectly claims these entries were committed.

- **Note — [bootstrap.py:173](/var/home/ares/AresOS-43-aresos-command/os/owner-tools/bootstrap.py:173):** All three lines have exactly the required word, quoting, sudo flags, and askpass assignments through unchanged 22d machinery. Labels satisfy its grammar, are distinct, and do not overlap the image’s TABLE labels. Harmless shell stand-ins preserved PASS/STOP output and exit status.

- **Note — [bundle.py:11](/var/home/ares/AresOS-43-aresos-command/os/owner-tools/bundle.py:11):** Independent regeneration in memory matches the payload, commands, guide blocks, and fingerprint pins. `f66fd694` correctly remains unchanged: neither `bootstrap.py` nor `commands.json` belongs to the payload. All 40 pending file hashes match. Byte equality supports the regeneration claim; it cannot prove the historical editing process.

- **Note — [INSTALL.md:341](/var/home/ares/AresOS-43-aresos-command/docs/INSTALL.md:341):** The bridge separately presents its labels and correctly carries announcement, Help, and explicit restart-approval rules. In-memory mutations removing restart approval or Help wording failed the guide test; restoring the parent equality checker caused six failures in the new regression test. Full module runs were limited by read-only temporary-file errors; live windows remain step 6 evidence.

CHANGES-NEEDED