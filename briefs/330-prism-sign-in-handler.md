# 330: Prism's sign-in handler: `prismlauncher://` links open Prism

Board brief 330 (board T474). Lead: `linux-aresos`. For R29.

**Builder:** Codex `gpt-6.2-sol` `high`: a small, exactly specified image change. **Brief review:** none. The change is one entry, one line and its checks, and the Claude week is tight; the builder confirms items 2's and 3's assumptions first and stops on any that fail. **Review:** a fresh Codex `gpt-6.2-sol` `high` context. **Bar (decision 24):** "reasonably safe". Must-fix means real harm or a sure failure in the build, the image checks or the VM. Low-harm edge cases go to the report's Known limits.

## Why

On R28 the owner's first start of the desktop asked him to sign in to Microsoft in Prism Launcher. He chose the browser route. Prism's browser sign-in ends with a redirect to `prismlauncher://oauth/microsoft?...`, and Chrome hands that link to the system (`xdg-open`). R28 registers nothing for `x-scheme-handler/prismlauncher`: the image ships Prism's bundle in `/usr/lib/prismlauncher` (package 23, `os/build.sh`) but no desktop entry for it. Chrome therefore kept sending him back without finishing. He signed in with Prism's device code instead (microsoft.com/link), which works.

## What changes

1. **A hidden desktop entry for the scheme,** `os/config/usr/share/applications/aresos-prismlauncher.desktop`:
   - `Type=Application`, `Name=Prism Launcher`, `NoDisplay=true`;
   - `Exec=/usr/bin/prismlauncher %U`;
   - `MimeType=x-scheme-handler/prismlauncher;`;
   - nothing else that changes behaviour.

   It must pass `desktop-file-validate`. The hub's app list skips `NoDisplay` entries (`os/config/usr/libexec/aresos-shell`, around line 977), so the hub must not list Prism. Prove this with the existing app-list tests or a new one.
2. **The default for the scheme:** add `x-scheme-handler/prismlauncher=aresos-prismlauncher.desktop` to `os/config/usr/share/applications/aresos-mimeapps.list`, under `[Default Applications]`, with a one-line comment naming this brief.
   - First find out how that list is read. Its name says it is the desktop-specific list for `XDG_CURRENT_DESKTOP=aresos`; confirm this from the session's environment in `os/config`.
   - If the image also needs its `mimeinfo.cache` regenerated (`update-desktop-database /usr/share/applications`) for `xdg-open` and `gio` to find the entry, do that in the build step that already handles `os/config`. Then say why in PROGRESS.md.
3. **What Prism does with the link.** Prism runs as one instance per data folder (`~/.local/share/PrismLauncher`; the desktop starts it with `prismlauncher --launch AresDesktop`, `aresos-desktop` `prism_command`). A second `prismlauncher <url>` normally hands the link to the running instance and exits.
   - Confirm this from the pinned Prism version's source or its own desktop file (upstream's `org.prismlauncher.PrismLauncher.desktop` lists `x-scheme-handler/prismlauncher` with `%U`). Record the version and where you looked.
   - If the pinned version needs a different `Exec` form, use that form and say why.
4. **Image checks** in `os/ci/image-checks.sh`, next to the default-browser check, each ending in a `pass` line like its neighbours:
   - the entry exists, `desktop-file-validate` is clean, and it has the four keys above;
   - as `ares`, with the session's `XDG_CURRENT_DESKTOP`, `xdg-mime query default x-scheme-handler/prismlauncher` prints `aresos-prismlauncher.desktop`;
   - `gio mime x-scheme-handler/prismlauncher` names the same entry, if `gio` is in the image;
   - the http, https and HTML defaults still print `google-chrome.desktop`.
5. **Tests:**
   - extend `os/tests/test_everyday_account.py`, which already reads `aresos-mimeapps.list`, and pin the new entry's text and the image check lines the way the repo pins its neighbours;
   - run the affected `os/tests` modules and say which ones. Don't run the full suite.
6. **R29's expected image differences:** list in PROGRESS.md each image path this package adds or changes, with a one-line reason. R29's release package explains them.

## Not in this package

- Prism's sign-in itself, the supervisor and `aresos-desktop`'s SETUP flow: the device-code route stays as it is.
- Any guide or owner text, `os/owner-tools/`, `os/release/`, `docs/`.
- Bound files: none is expected. If a test says otherwise, record it with `reviews/27-first-update-release/rebind.py pending "<note>"` and say so.

## Steps

- **One step:**
  - Branch `pkg/330-prism-handler` from main, with this brief as its first commit.
  - Build items 1 to 6, commit and push, open a draft PR into main, and keep `reviews/330-prism-handler/PROGRESS.md` (what's done, what's left, what the code doesn't show).
  - Then stop. The lead dispatches `check_build=build`, whose image checks are this package's proof.
- **Last:** after the review is SAFE and the build is green, the lead commits the report from PROGRESS.md, deletes PROGRESS.md and merges.

AGENTS.md's rules apply. In anything committed, write "the owner", never a name.
