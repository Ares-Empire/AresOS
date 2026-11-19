# aresos-shell/1.2 example messages

The requests, replies and events here implement section 5 of [LAPTOP-HOME.md](../../../../../docs/design/LAPTOP-HOME.md).
Each JSON file shows one message. The wire format uses one UTF-8 JSON object per line. The credentials and IDs
are test values.

- `view-hello-*` shows a view joining and the helper's refusals. A successful reply is followed by
  `apps-running-empty-event.json` when there are no windows.
- `publish-home-*` shows a complete publish and a separate two-part publish. The desktop gets an
  acknowledgement for each part. Views get `home-changed-event.json` after a complete publish.
- `get-home-*` shows the initial empty snapshot, the single-part home, and the two-part home split
  across two reply pages. The examples use a reduced reply size to illustrate paging with two apps.
  The real wire limit is 64 KiB. Return the opaque `next` value unchanged as the next request's
  `cursor`.
- `apps-running-event.json` shows a change to the list of app IDs with windows.
- `desktop-hello-*` shows a 1.2 desktop with window tracking: it offers `shell_search` and the helper offers it
  back. A view and an older desktop are never offered it.
- `shell-search-event.json` (package 53d) asks the desktop for its search over the world: Super was pressed,
  and the helper has asked the compositor to give the world's window the keyboard.
- `open-app-world-*` opens an app on the screen that shows the world (the search over the world's Enter).
  `open-app-bad-screen-*` shows any other `screen` refused as `malformed`, as it is from a view or an older
  desktop.
