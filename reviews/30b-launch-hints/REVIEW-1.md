Reviewed commit `fb6546eba8366f2ec8030ec472d92dbe1e343e8b`; review was read-only. No files changed and no helper, test, build, or application executed.

Scope: package 30b’s `2096b538..a61df109` changes and the added OS-BASE sentence. Package 30’s existing findings were not reopened.

| Point | Status | Reason |
|---|---|---|
| 1. Hint format | OK | New settings enforce the specified types, counts, lengths and ASCII ranges. `\Z` rejects trailing newlines. JSON keys are strings; duplicate decoded keys are rejected at every object depth, including escaped duplicates. Reads stop at 64 KiB plus one byte; oversized files, decoding errors and excessive nesting are refused with a log line. Start-only hints work. |
| 2. Application and disclosure | OK | Settings attach only to the matching discovered desktop ID. Registry apps and replaced entries are excluded. GPU wishes combine without removing the entry’s preference. Each launch gets a fresh filtered environment, then hint values, then NVIDIA values, including terminal wrappers. No expansion or mutation of the session environment. Socket rows/events and normal helper logs do not disclose setting values. |
| 3. Image-only source | OK | Production starts the helper without a registry override; hints come from `/usr/share/aresos/apps/hints`. Home directories, desktop entries, Flatpak exports and socket requests cannot supply hint settings. Image copying and the ownership check preserve the root-owned source. The existing explicit `--registry` development override is not runtime ownership enforcement; production does not use it. |
| 4. Allowed SDL names | OPEN | The pattern matches the brief, but permits library-loading and file-writing variables. It restricts the namespace, not the effects. See SHOULD 1. |
| 5. Revision and compatibility | OK | Catalogue hashing includes `environment` and `gpu`. The 1.0 path retains its separate registry-byte revision and old rows; hint changes do not generate 1.0 `apps_changed` events. The shell-1.1 examples are unchanged. Direct revision regression coverage could improve. |
| 6. Shipped hints and image check | OK | Lunar has exactly the requested additions; Steam is unchanged. The image-check change only updates Lunar’s expected `Hint`. The OS-BASE addition describes the implemented behavior. |
| 7. Tests and laptop safety | OPEN | Static inspection supports the reported regression/control classifications. Unit tests inject executable availability and GPU presence. The real-scope check uses only private stand-ins, temporary HOME/output paths, no display variables, random unit names, `--collect`, and cleanup of that exact unit. It requires a user manager and is intentionally outside hosted `test_*.py` discovery. The report still lacks a completed hosted result. |
| 8. Judgment calls | OK | Agree with all six, individually explained below. |

No FIX findings were identified in the scoped change.

**SHOULD 1 — Document that the SDL namespace permits significant side effects.**  
`os/config/usr/libexec/aresos-shell:353`; `docs/design/OS-BASE.md:267`.

A future image hint containing `"SDL_OPENGL_LIBRARY": "/var/home/ares/libGL-custom.so"` passes validation and can select code outside the image. Similarly, `"SDL_AUDIO_DRIVER": "disk"` with `"SDL_AUDIO_DISK_OUTPUT_FILE": "/var/home/ares/notes.txt"` passes; with the disk backend available and playback opened, SDL opens the destination with `"wb"`, potentially truncating it. These behaviors are documented in [SDL’s hint definitions](https://raw.githubusercontent.com/libsdl-org/SDL/release-3.2.0/include/SDL3/SDL_hints.h) and [disk-audio implementation](https://raw.githubusercontent.com/libsdl-org/SDL/release-3.2.0/src/audio/disk/SDL_diskaudio.c).

Document this beside the pattern and in the hint-review guidance: every new name/value needs semantic review, including any referenced mutable file. Narrowing the pattern to specific variables would require changing the brief’s explicit decision.

This is SHOULD, not FIX: neither shipped hint enables these effects, and an outside input cannot introduce such a hint. The current package does not demonstrate unreviewed settings or owner-file damage.

**SHOULD 2 — Complete the hosted verification record.**  
`reviews/30b-launch-hints/REPORT.md:118`.

The recorded hosted run was still running after the watcher timed out. Consequently, the report cannot establish that hosted checks completed successfully. Record the completed result and tested commit, including whether the subsequent package-30 test-portability fixes were included. Keep the image check and real Lunar trial separately identified as pending.

This is an evidence gap, not a demonstrated runtime failure, so it does not meet the FIX bar.

**NIT 1 — Test revision behavior through the catalogue path.**  
`os/tests/test_aresos_shell_launch_hints.py:230`.

The legacy comparison injects the same `load_registry` revision into both helpers. A regression that excluded environment values from the catalogue digest would therefore pass this test and the row comparison.

Add a focused catalogue test that changes only a hint value and checks: the 1.1 revision changes, rows remain equal, and the 1.0 revision remains equal. The inspected implementation already behaves correctly; this is a coverage improvement.

The six judgment calls:

1. **Duplicate keys rejected — agree.** Prevents review ambiguity, including duplicate keys written using JSON escapes.
2. **Empty environment accepted beside another meaningful field — agree.** Consistent with “at most eight”; an empty object alone supplies no setting.
3. **Space counts as printable ASCII — agree.** Matches the specified range without allowing control characters.
4. **Hint values override session values — agree.** Required for Lunar’s reviewed Wayland choice to take effect.
5. **Start settings contribute to the catalogue revision — agree.** Correct for 1.1; the separate 1.0 revision remains unchanged.
6. **Keep “window hint” in error messages — agree.** Slightly dated wording, but the filename and reason remain useful and values are not unnecessarily logged.

The remaining functional limit is documented accurately: delivering these values to Lunar’s launcher does not itself prove that its game inherits them and opens successfully on NVIDIA under Wayland. That remains the owner’s trial.

VERDICT: SAFE with documented known limits