# Switch-only attempt 5

Run: https://github.com/carlsenares/AresOS/actions/runs/39786345222
Source: `12f4a720630e16aa1926411c00f01b366cd1bafb`.
Reused immutable image: run 39774351695 (runtime unchanged at that point).

This attempt failed before any switch. Stock Bazzite's one orderly pre-login
hardware-setup reboot was handled, then the password-protected UID-1000
administrator logged in over serial and authenticated sudo successfully.
`stock-status.txt` contains terminal lock-wait progress and interleaved kernel
records around the JSON; parsing that terminal output raised JSONDecodeError.
The later harness captures stdout to a file, validates JSON there and exports
it with the existing checksum-framed protocol. Tests inject the observed noise
and reject checksum corruption. This folder is failure evidence, not switch
or rollback qualification. The stock screenshot is in the sibling screenshots
folder. No authentication transcript, credential or disk is retained.
