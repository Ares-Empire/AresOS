These are image-side templates for laptop-aresos; this package changes no image.

Build a signed CRX3 with `node control/chrome/packaging/pack.mjs KEY.pem OUTPUT`.
The same RSA key gives the same extension ID on every release; keep the production
key outside this repository. CI creates its ephemeral key in memory and deletes
its test package/profile when the container exits. No browser starts during packaging.

Replace EXTENSION_ID in native-host.json, policy.json and update.xml with the
reported ID. Set UPDATE_URL to the image's local HTTPS update endpoint and CRX_URL
to the published signed package. Install the policy root-owned under
/etc/opt/chrome/policies/managed/, and the native manifest root-owned under
/etc/opt/chrome/native-messaging-hosts/. Install native_host.py root-owned at its
fixed manifest path with mode 0755. Its only endpoint is chrome.sock; the service
checks Linux SO_PEERCRED against the configured owner, independently of mode bits.
A same-named user-level host is an accepted decision-24 residual.

Copy all control/aresos_control runtime modules, generated/, settings/, launch.py,
requirements.lock and chrome/{extension,native_host.py,build.py,packaging,
qualification.json} into the installed service tree. During the image build,
compute `python3 control/chrome/build.py` on the complete source tree and write
`{"build":"HASH"}` into the installed chrome/build-id.json. Qualification data
and that output marker are excluded from their own hash. Every other executable,
shared approval implementation, definition and installed configuration is included.
The lead records an image's build hash and source commit in chrome/builds.json;
keep the newest three still-used builds. This is the manual handoff until the
image-side integration is agreed.

The shipped qualification baseline is empty until CI evidence is published. That
means conservative mode, never an invented qualification. The service's daily
fetch accepts only append-only records attested by this repository's
control-chrome workflow on main, through GitHub CLI >=2.102.0. Installation must
supply that verifier. Offline or failed verification keeps the held record.
