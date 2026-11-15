# `aresos-shell/1.1` example messages

One example per message kind of the additions in `docs/design/HUB.md` 3.8. They are the contract between the mod's
client (`ShellClient`, package 34) and the OS helper (package 30): the mod's tests read these files
(`ShellListTest`), and the helper's tests read the same ones. Changing a file changes the contract.

On the wire each message is one line; the files are indented for reading. Request IDs, the cursor, the revisions,
the instance, the nonce and the icon paths are made up.

| File | What it is |
|---|---|
| `hello-request.json` | The mod's `hello`: minor 1 and the three new capability names. |
| `hello-reply.json` | A 1.1 helper's answer. |
| `list-apps-request-first.json` | `list_apps` for the first page: no `cursor` field. |
| `list-apps-request-next.json` | `list_apps` for the page after: `cursor` is the `next` of the reply before. |
| `list-apps-reply-first-page.json` | A page with more to come: it has `next`. |
| `list-apps-reply-last-page.json` | The last page: no `next` field. Same `revision` as the first. |
| `entry-full.json` | One entry with every field. |
| `entry-minimal.json` | One entry with none of the new fields: as in 1.0. |
| `apps-changed-event.json` | The event that makes the mod list again. |

The two pages together hold every kind of `source`. By the day-one rule five of the eight are his: the three
starters (`image`), Discord (`flatpak-user`) and Lunar Client (`user`).

## What HUB.md 3.8 left open, and what these files settle

- **The `protocol` field.** The mod's `hello` says `aresos-shell/1.1`, its own version. Every later message of the
  mod says the minor the helper's reply agreed to: `aresos-shell/1.1` with a 1.1 helper, `aresos-shell/1.0` with a
  1.0 helper. The helper does the same in its direction, as it does today. Each side accepts any `aresos-shell/1.x`.
- **Capabilities.** The mod offers `app_details`, `apps_changed` and `list_paging` and requires none of them. The
  helper sends `apps_changed` only to a client that offered that name (the rule it has for every event today).
- **What makes a connection 1.1** is the `minor` in the `hello` reply, nothing else. With minor 0 the mod sends no
  `cursor`, ignores `next` and the new entry fields, and ignores `apps_changed`.
- **`id` of a program.** As for the starters: `[a-z0-9_-]{1,64}`, unique in the list. The helper chooses it, and it
  must stay the same for the same program across restarts and helper updates: the mod saves "mine", pins, names and
  places under it. The examples lower-case the desktop file ID and turn dots into hyphens.
- **`desktop_id`** is the desktop file ID as the system names it, with its `.desktop` ending.
- **`cursor` and `next`** are opaque to the mod: it sends back what it got. A `next` that is empty, not a string or
  longer than 64 characters ends the list as incomplete. `"next": null` reads as no `next`.
- **`revision` in `apps_changed`** is not compared with anything: the mod lists again whatever it says, because a
  picture can change under the same path.
- **`reason`** is unchanged from 1.0: `null` when the program is available.

## What the mod does with a list

- It asks page after page until a reply has no `next`. Only then do the apps reach the game; half a list never does.
- A page whose `revision` differs from the first page's makes it start over, three times at most. After that, after
  64 pages, or after 1024 programs, it keeps the list it had and waits for the next `apps_changed`.
- An entry without a valid `id` and `name` is skipped, as in 1.0. A second entry with an `id` already seen is skipped.
- An optional field that is missing or breaks its rule counts as "not known": a `source` that is not one of the
  five, an `icon` that is not an absolute path, a text that is too long or has control characters, an `exec_name`
  with a slash, a `terminal` that is not true or false. In `categories` and `keywords` a bad word is skipped and
  words after the sixteenth are ignored.
- The mod reads the `icon` file only if it is a regular file of at most 1 MiB that decodes as a PNG of at most
  512 x 512 pixels.
- After `apps_changed` it lists again, at most once every two seconds; events that arrive meanwhile share one list.
