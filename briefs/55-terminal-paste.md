# 55: Ctrl+V pastes in AresOS's terminal (rides R28)

Empire board brief 309. Written and built 2026-11-18 by `linux-aresos` (a one-line setting, cheaper to make than
to brief). A fresh reviewer checks it.

## Why

The owner, 2026-11-18, after pasting an API key into a foot window: "why ctrl shift v? isnt it ctrl v usually?
aresos should have standard cmds". Asked whether Ctrl+V should paste, and whether in release 28 or 29, he said
"yes" to the recommendation: Ctrl+V pastes, in release 28.

## What changes

- `os/config/etc/xdg/foot/foot.ini` gains `[key-bindings]` with
  `clipboard-paste=Control+v Control+Shift+v XF86Paste`: Ctrl+V pastes, and foot's default Ctrl+Shift+V and the
  paste key keep working.
- **Ctrl+C is not changed.** It stays with the program ("stop the running command"); foot cannot copy on Ctrl+C
  only while text is selected, so taking it would remove the way to stop a command. Copy stays Ctrl+Shift+C.
- Cost: programs in the terminal no longer receive Ctrl+V (bash's "insert the next key literally", nano's page
  down, vim's block selection). The owner is not expected to use them.
- `os/tests/test_everyday_account.py` pins the section and the binding; `os/ci/image-checks.sh` checks the line
  in the built image and that `foot --check-config` accepts the file.

## Not in the image

foot reads only the first foot.ini it finds. The owner's laptop has its own `~/.config/foot/foot.ini` (an earlier
session's, 2026-11-09: font 16 and an interim PATH), so the image's file doesn't reach him. With his yes the lead
added the same binding to that file on 2026-11-18 (checked with `foot --check-config`).
