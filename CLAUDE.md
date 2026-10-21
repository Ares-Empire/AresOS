# AresOS: notes for Claude / Codex

Read `README.md` first. It holds the design and phases.

- The Minecraft theme is a **Fabric mod for the real game**, not a recreation. Don't build a voxel engine.
- Develop and test on Windows (phase 1) before any Linux/USB work.
- Codex runs headless via `codex exec` with `-m gpt-5.5` (or newer) and high/xhigh reasoning, never the Spark default. Claude reviews the diffs.
- Never commit Mojang or Supercell assets to this repo. Textures are loaded from the user's own install at runtime.
- Never write to the laptop's internal disk or change boot settings without asking first.
