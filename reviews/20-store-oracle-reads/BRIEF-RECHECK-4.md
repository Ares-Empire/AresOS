Codex gpt-6.2-sol, medium, 2026-11-21. Reviewed `brief/317-revise-1` at `8da45b62`.

- **BLOCKER — CLOSED.** The brief allows one shared pre-send guard that preserves reply draining and a separate post-`configure` guard. The `configure` fault test checks that the expired copy remains and no qualification refresh runs, then removes only the post-`configure` guard for the mutation. [Rule 1](briefs/20-store-oracle-reads.md#L84) · [Allowed edits](briefs/20-store-oracle-reads.md#L802)
- **SHOULD-FIX — CLOSED.** The live pending projection may configure before its first probe, behind the existing passive checks. The only new bridge and projection allowances are the pre-send guard and that configuration step. The extension stays outside scope. [Edit limits](briefs/20-store-oracle-reads.md#L802) · [Protected paths](briefs/20-store-oracle-reads.md#L821)
- **NIT — CLOSED.** The fixture specifies one approved file larger than 512 KiB, so the upload needs a second `stage_file`. [Rule 1](briefs/20-store-oracle-reads.md#L84)

READY
