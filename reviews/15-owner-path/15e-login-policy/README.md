# Pinned login-policy source inspection

These eight files are byte-for-byte reads from the public Bazzite base named
in `os/manifest/release.json`, not a live laptop's configuration. `index.json`
binds their SHA-256, OCI layer, original path and OSTree object to the retained
base manifest. The registry manifest and every downloaded layer were verified
against their literal digests before reading. OSTree hardlinks were resolved
to their archived objects; no image code, mount, container or VM was run.
The compressed archives and read-only inspection scripts remain in ignored
`.work/15e/sources/` and `.work/15e/`.

The baseline selects authselect's `local` profile. Login includes system-auth;
sudo-i includes sudo, which includes system-auth. The generated stack contains
no `pam_faillock` call. The shipped, unmodified `faillock.conf` documents module
defaults of deny=3, fail_interval=900 seconds and unlock_time=600 seconds, with
no active overrides. The recovery budget of two failed login submissions is
conservatively below that shipped default; **this does not claim an active
three-failure account lock in the baseline stack**.

The AresOS package lock adds no PAM/authselect package, its configuration tree
has no replacement for these files, and its build script does not change this
policy. The keyboard image retains that release and changes only its two
declared session/keyboard files. Those source bindings are listed in the index.
Installer or owner changes to an installed `/etc` are not covered by this
source inspection. Earlier failures, a lockout warning or policy uncertainty
therefore require Help before using the bounded login route; nothing here
authorizes changing PAM, clearing counters or retrying in a loop.
