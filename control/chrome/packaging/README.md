These are the image-side files of Chrome's browser side. The image build installs
them (package 18c-b); nothing here changes an image by itself.

`python3 control/chrome/packaging/pack.py EXTENSION_FOLDER OUTPUT_FOLDER` builds, in
one call, everything that depends on the extension's identity: `extension.crx`, a
signed CRX3 package of the folder, and `update.xml`, `policy.json` and
`native-host.json`, rendered from the templates here with the package's ID. Every
call makes a new RSA key inside its own process, signs once and forgets the key.
The ID is the hash of the public key, so each image build has its own ID, and no
signing key is kept anywhere: the key is never written, printed or exported, and
the packer takes no key as input. Two builds of one commit therefore differ in the
package, the ID and the generated files, on purpose. What stays comparable is the
public record the packer prints: `id`, `version`, `public_key_sha256`,
`crx_sha256` and `payload` (each packed file's name and SHA-256). A link or a
special file in the folder is refused. No browser starts during packaging and it
needs no node: Python with `cryptography`, which the image's base has.

After an update or going back a version, Chrome removes the old extension and
installs the image's own. Anything the extension stored in the browser would be
lost then; it stores nothing, and
`control/chrome_tests/test_extension_stores_nothing.py` fails if that changes.

Chrome installs the extension by policy from a file inside the image. Nothing is
published, nothing listens, and no certificate is needed. The image build puts the
four files in `/usr/share/aresos/chrome/`, root-owned, mode 0644:
- `policy.json` holds one `ExtensionSettings` entry for the one ID and nothing
  else: `force_installed`, `toolbar_pin` `force_pinned`, `update_url`
  `file:///usr/share/aresos/chrome/update.xml`, and `override_update_url`, so
  Chrome asks no store about the extension.
- `update.xml` points to `file:///usr/share/aresos/chrome/extension.crx` and
  takes its version from the extension's `manifest.json`.
- `native-host.json` allows exactly one origin, the package's.

`/etc` holds only two root-owned links, which never change, so an update or a
rollback swaps the real files with the image:
`/etc/opt/chrome/policies/managed/aresos.json` to
`/usr/share/aresos/chrome/policy.json`, and
`/etc/opt/chrome/native-messaging-hosts/org.aresos.chrome.json` to
`/usr/share/aresos/chrome/native-host.json`.
Install the host launcher root-owned at its fixed manifest path with mode 0755,
and native_host.py beside it with mode 0644. Its only endpoint is chrome.sock; the service
checks Linux SO_PEERCRED against the configured owner, independently of mode bits.
A same-named user-level host is an accepted decision-24 residual.

`pack.mjs` (`node control/chrome/packaging/pack.mjs KEY.pem OUTPUT`) stays CI's
packer for its own installs. CI creates its ephemeral key in memory, serves its
package from a loopback address and deletes its test package/profile when the
container exits. No image is built with it.

Install `org.aresos.control.chrome-loosen.policy` root-owned, mode 0644, at
`/usr/share/polkit-1/actions/org.aresos.control.chrome-loosen.policy`, and make sure
the image has polkit's `pkcheck` at `/usr/bin/pkcheck` (the `polkit` package) and a
polkit authentication agent in the owner's desktop session. Chrome's details page
reaches the owner-only list through chrome.sock, which any process of the owner's
user can open; so allowing a kind without asking, or turning read-only off, makes
the service run `pkcheck --allow-user-interaction` against the process that
connected (pid, start time and uid). The owner's agent then asks for the admin
password, once for each change: the action is `auth_admin`, never
`auth_admin_keep`. Listing, revoking and turning read-only on need no password.
The policy's `org.freedesktop.policykit.owner` annotation names the service's user
(`unix-user:aresos-tools`, from `aresos-toold.service`); polkit refuses the
service's check for another user's process without it. Without the file, pkcheck
or an agent, those two buttons refuse and `sudo aresos admin chrome sites` still
works. The real-polkit check of this file runs in
`.github/workflows/control-chrome-polkit.yml`; the image's own check with the
owner's real session agent is linux-tools' 18c-b image test.

The owner's excluded-sites list is
`/var/lib/aresos-control/chrome-excluded-sites.json`. It lives in `/var`, which
all deployments share, so an update or going back a version keeps it. The image
ships no list (the repository is public and can't carry his hosts).
`aresos-control-chrome.tmpfiles`, installed as
`/usr/lib/tmpfiles.d/aresos-control-chrome.conf`, makes the folder (`root:root`,
mode 0755) at boot and, when the file is missing, the placeholder
`{"format":0,"hosts":[]}` (`root:aresos-tools`, mode 0640). The service refuses
the placeholder as it refuses a missing, unreadable or unsafe file: every Chrome
read and action answers `chrome_settings_unavailable` until root writes a
`format` 1 list, `{"format":1,"hosts":[]}` or the owner's private DNS host list.
An empty list counts. Each entry covers its host and subdomains; names are
lowercase and contain no scheme, port or path. The file and every parent must be
root-owned, without group or world write permission or symlinks. The service's
group may read the file; only root can change it, and the folder is outside the
paths the unit may write, because the list restricts the service. Keep actual
owner infrastructure out of source control.
The extension receives these exclusions over native messaging, builds session
DNR rules for controlled tabs, and registers its content scripts with runtime
exclusions. A changed list ends control before its new rules take effect.

The image's install map (`os/build.sh`, package 18c) installs the service: the
control/aresos_control runtime modules with their unicode_words.json data,
generated/ and the single files its map lists (launch.py and
chrome/qualification.json among them). It
computes `python3 control/chrome/build.py` on the untouched source tree, before
anything is generated, and writes `{"build":"HASH"}` into the installed
chrome/build-id.json; generated files go only into the image, never back into
the source tree, so that hash equals what CI qualifies for the same commit.
Package 18c-b adds the host launcher and native_host.py, the polkit action, the
tmpfiles file, the four files of `/usr/share/aresos/chrome/` and the two links.
The installed tree holds no copy of these templates, of the extension's sources
or of build.py. Qualification data
and that output marker are excluded from their own hash. Every other executable,
shared approval implementation, definition and installed configuration is included.
An image's build hash and source commit are recorded in chrome/builds.json with
`control/chrome/record_build.py` (`add` when a release ships it, `check` against
the release manifests); it keeps the newest three builds.

The shipped qualification baseline is empty until CI evidence is published. That
means conservative mode, never an invented qualification. The service's daily
fetch accepts only append-only records attested by this repository's
control-chrome workflow on main, through GitHub CLI >=2.102.0. Installation must
supply that verifier. Offline or failed verification keeps the held record.
