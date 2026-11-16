# 22d step 0: the password window on the laptop

2026-11-15, about 03:20 (laptop time), R27 with tools v2. Run by the OS lead from its Claude Code shell (stdin
`/dev/null`, no controlling terminal; `WAYLAND_DISPLAY=wayland-0`, `XDG_RUNTIME_DIR=/run/user/1001` inherited from
Konsole), with the owner's OK in the session ("yes you can try it", board #266). The command behind both windows was
`true`. No owner tool ran, nothing on the system changed.

The line, as the design note proposes it, with a test label:

```
SUDO_ASKPASS=/usr/bin/ksshaskpass /usr/bin/sudo -k -A -p 'AresOS owner tools test: password for ares' true
```

Run twice, six seconds apart. Instructions to the owner: Cancel in the first window; a wrong password, then his own,
in the second.

## What happened

| Try | Owner's action | sudo | Journal |
|---|---|---|---|
| 1 | Cancel (answered within about 4 s of the window) | `sudo: no password was provided`, `sudo: a password is required`, exit 1; `true` did not run | `pam_unix(sudo:auth): conversation failed`; audit `op=PAM:authentication … res=failed`; audit `cmd="true" … res=failed` |
| 2 | A wrong password, then his own (about 14 s in all) | `Sorry, try again.`; the window came back; exit 0 | `pam_unix(sudo:auth): authentication failure … tty= ruser=ares`; then audit `res=success`; `sudo: ares : PWD=/var/home/ares ; USER=root ; COMMAND=/usr/sbin/true`; root session opened and closed |

- **Each window logged** `ksshaskpass[…]: Unable to parse phrase "AresOS owner tools test: password for ares"`: the
  label matched none of the helper's remembered-prompt patterns, so no keyring was read and no "keep password" box
  was shown (confirms review 1's reading of ksshaskpass 6.7.5; F18 still asks the VM to assert it).
- **The window** (one screenshot, looked at by the lead, deleted, not committed): a small dialog centred on the left
  display, above the maximised Konsole the owner was working in. Its **title bar reads "Enter SSH Credentials"**
  (ksshaskpass's fixed title; `sudo -p` sets only the line inside). Inside: the label line, a `Password:` field,
  OK and Cancel. No "remember" option.
- **Keyboard:** the owner answered each window within seconds, so it took his typing without a detour; his own words
  on focus are still to be added.
- **sudo's journal names the command that the prompt approved** (`COMMAND=/usr/sbin/true`), as the note expected
  (section 3, point 1).
- No ticket: try 2 asked again although try 1 had just run (Cancel leaves nothing behind either way); `-k` was given.

## Consequences for the brief

- The label rule stands (no keyring). **The title "Enter SSH Credentials" cannot be changed with ksshaskpass**, so the
  guide describes the window as it looks: that title, and the AresOS line inside. A root-owned AresOS helper with its
  own title (`kdialog` 26.08.1 and `zenity` are in R27) belongs to the next image, not 22d, which cannot change the
  image.
- The window opens on the left display over whatever has focus, not specifically over the hub; with the hub in front
  it is expected to stack above it the same way (labwc places new dialogs on top). Not yet seen with the game in
  full screen.
- Cancel and a wrong password behave as the note says, and the journal tells all three outcomes apart.
