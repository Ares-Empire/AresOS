# 13f zero-cost sources and host walk

These are upstream source files, not an installed image or VM result.
`sources.json` records exact URLs, bytes and SHA-256. The retained installed
inventory pins xkeyboard-config 2.47-1.fc44 and kbd 2.9.0-4.fc44. The runner
toolchain pins QEMU 1:8.2.2+ds-0ubuntu1.18. QEMU v8.2.2's
`subprojects/keycodemapdb.wrap` pins keycodemapdb
`f5772a62ec52591ff6870b7e8ef32482371f22c6` (not its moving default branch).

| Character | German physical QMP keys | US physical QMP keys | Source |
| --- | --- | --- | --- |
| `.` | `dot` | `dot` | XKB AB09; kbd keycode 52 |
| `;` | `shift` + `comma` | `semicolon` | DE AB08 / kbd 51; US AC10 / kbd 39 |
| `'` | `shift` + `backslash` | `apostrophe` | DE BKSL / kbd 43; US AC11 / kbd 40 |
| `y` | `z` | `y` | DE AB01 / kbd 44; US AD06 / kbd 21 |
| `z` | `y` | `z` | DE AD06 / kbd 21; US AB01 / kbd 44 |
| `-` | `slash` | `minus` | DE AB10 / kbd 53; US AE11 / kbd 12 |
| `/` | `shift` + `7` | `slash` | DE AE07 / kbd 8; US AB10 / kbd 53 |
| `!` | `shift` + `1` | `shift` + `1` | AE01 / kbd 2 |

All other typed lowercase ASCII letters, digits, space and Return use unchanged
positions. German `basic` inherits `latin(type4)`; the two differing letter
positions are explicitly overridden. `kbd-qwertz-layout.inc` and the prior
13e `kbd-us.map` / `kbd-qwerty-layout.inc` show the console positions.
The pinned QEMU CSV maps these XKB/evdev positions to QKeyCode names;
`qemu-ui.json` defines QMP `send-key` and its QKeyCode enum.

`host-walk.json` is a **stand-in host execution**, never VM evidence. It executes
the actual qualification main, tty, foot, physical-input, loaded-map,
transaction and full-list checks through all branches, using the retained 13e
stock snapshots and explicitly source-derived synthetic future deployment states.
The new AresOS checksum is deliberately `b` repeated 64 times. Shell commands
are collected, never executed locally. The real greeter capture/metrics code was
also run with the retained, visually inspected 06c stock PNG. Guest readiness
was a stand-in. Unknown physical characters still raise, including uppercase,
non-ASCII, NUL, empty and multi-character values.

The coverage test observes all actual `type_text` calls, covers the entire
password character domain, and includes both layout-change command strings
even though their unchanged transport is serial root. Generated shell commands
passed `bash -n` with LF bytes. Real QMP input, guest login/sudo, root commands,
signature/network access, kernel maps, bootc finalization, session policy and a
new rendered rollback greeter require the authorized native Actions VM run.
