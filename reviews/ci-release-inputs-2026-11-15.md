# Review: CI release inputs after Bazzite removed the legacy ISO (2026-11-15)

Commit under review: `46101d4d` on `main`, "CI: find Bazzite's ISO picker from the site index; the legacy ISO left the site" (one file, `os/ci/release-inputs.py`).
Reviewer: a fresh Claude agent (Opus), not the integrator who wrote it. Read-only apart from this file.

## Findings, ranked

None block this commit. All four are notes.

1. **Low, outside this commit: the pinned manifest's `picker_source` is now a dead link.** `os/manifest/installer-isos.json:8` and `:16` still name `.../main/content/themes/betheme-child/script135.js`, which now returns 404 (checked). Nothing fetches `picker_source` (only `release-inputs.py:57` writes the field, into evidence), so nothing breaks. The field is provenance only. Next time the manifest changes, a commit-SHA URL (`.../bazzite.gg/<sha>/...`) would keep it readable. Leave the hashes alone.
2. **Low: the offered-kinds test depends on the JS quoting style.** At `os/ci/release-inputs.py:45-46` the test is an exact substring match on `'-stable{suffix}-amd64.iso'`, single quotes included. If upstream changes the style (double quotes, a template literal), the live assert at `:47` stops the job loudly, which is the right failure. A legacy link would be dropped silently, but that is now intended. The `Picker offers:` line at `:48` records the outcome in the log. No change needed.
3. **Info: the index regex matches a substring.** `os/ci/release-inputs.py:36` would also match inside a longer path such as `wp-content/themes/betheme-child/scriptN.js`. Then `source` (`:38`) would point to a path that doesn't exist, and the fetch would 404 loudly. That fails closed, so no change is needed.
4. **Info, unchanged by this commit: the evidence step never compares hashes with the pins.** The resolved live SHA-256 is not checked against `os/manifest/installer-isos.json`. Drift is caught only when a rehearsal runs `os/ci/installer_inspect.py:89` and `:166` ("Official checksum changed: STOP"). Today they match: `776b76f3…d8e6` resolved, `776b76f3…d8e6` pinned.

## 1. Is the logic right?

Yes.

- **Index regex** (`release-inputs.py:34-38`). The pattern `content/themes/betheme-child/script\d+\.js`, run over `index.html` from the official Git source, finds exactly one reference today: `content/themes/betheme-child/script136.js`. The prefix comes from the regex and the number from the site, so the URL can't be steered off `raw.githubusercontent.com/ublue-os/bazzite.gg/main/`. `sorted(set(...))` folds repeated references to the same file into one.
- **"Exactly one script" assert** (`:37`). This is right, and it fails closed. If the site loads two picker scripts during a transition, the job stops with both names instead of guessing.
- **Offered-kinds test** (`:45-46`). Today's `script136.js` has only `'-stable-live-amd64.iso'` (line 575 of the picker, plus `-CHECKSUM` and `.sig` at 577-578). The legacy `'-stable-amd64.iso'` template is gone. I also ran the test against an archived old picker (`os/manifest/ci/11n/native-1/iso-picker.js`, from script135). It matches both kinds there, so the test tells the two pickers apart correctly in both directions. The `-CHECKSUM` and `.sig` variants don't cause false positives, because the closing quote is part of the match.
- **Live required** (`:47`). This is right. The live ISO is the only one on the install path (`docs/INSTALL-REFERENCE.md:64`; `two_disk_vm.py:24`, `installer_inspect.py:173` and `installer_webui.py:89` all select `kind == 'live'`).
- The asserts run because the workflow calls `python3` without `-O` (`os-image.yml:132`).

## 2. Is it safe? Does anything read the evidence?

Yes, it is safe. Nothing reads the evidence.

- `evidence/installer-isos.json`, `iso-picker.js` and `iso-*-CHECKSUM.txt` are written only by `release-inputs.py`. In the same `regressions` job (`os-image.yml:53-142`), the only later reader is the cosign step (`:136-137`), and it reads only `base-candidate.json`. The whole folder is then uploaded as artifact `release-inputs` (`:138-142`, 3-day retention). No workflow downloads that artifact: the only `download-artifact` in `os-image.yml` is `os-image-evidence` at `:498`.
- No module in `os/ci/*.py` and no test in `os/tests/` reads `evidence/installer-isos.json`, `iso-picker.js` or `iso-legacy-CHECKSUM.txt`, or expects a `legacy` entry. I grepped for `iso-legacy`, `'legacy'`, `installer-isos`, `release-inputs`, `picker_source`, `checksum_source` and `script13x`.
- The one test that touches the manifest, `os/tests/test_owner_equality.py:66`, reads hashes from the pinned `os/manifest/installer-isos.json` with no network access. The commit doesn't change that file, and the pinned legacy hash stays there.
- The archived `os/manifest/ci/*/installer-isos.json` and `ci.json` records are historical. Nothing compares new evidence with them.

## 3. Live run

The script succeeded with exit code 0. It produced:

- `base-candidate.json` and `base-candidate-manifest.json`, with candidate `ghcr.io/ublue-os/bazzite-nvidia-open@sha256:ed93d215…5151`;
- the log line `Picker offers: live`;
- `iso-picker.js` (from `script136.js`), `iso-live-CHECKSUM.txt` and `installer-isos.json`. The JSON has one live entry, with `sha256` `776b76f3417723440ee1823d79ec02a2c22860df196d219024edb062ad00d8e6`, the same as the pin.

No `iso-legacy-CHECKSUM.txt` was written.

## 4. Is the pinned legacy ISO at new risk?

- **The file is still there.** `download.bazzite.gg` still serves `bazzite-nvidia-open-stable-amd64.iso`: HEAD returns 200, 8,079,671,296 bytes, Last-Modified 2025-10-18. Its `-CHECKSUM` still reads `85e701c0…24b8`, which is the pinned hash. Now that the site no longer links it, a later cleanup could remove it without notice.
- **No CI or harness path downloads it.** `two_disk_vm.py:24`, `installer_inspect.py:173` and `installer_webui.py:89` (plus the archived 14x installer adapters) all take only the live entry. The only workflow cache is the mod's Gradle cache (`mod.yml:40`), and no ISO cache exists. If the file were removed, no job, harness module or test would fail.
- **Only the same-drive fallback route needs it.** `docs/INSTALL-SAME-DRIVE.md:53` and `:172` tell the owner to get the exact legacy ISO and SHA-256. That route would lose its install media, and would need re-qualifying on the live ISO or a privately kept copy of the pinned file. The primary own-SSD route (`docs/INSTALL.md`, `docs/INSTALL-REFERENCE.md:64`) uses only the live ISO.
- **Related risk on the live route.** The live ISO is also published under a rolling `stable` name. When upstream rebuilds it, `installer_inspect.py:166` stops with "Official checksum changed". That would happen whether or not this commit exists.

## What I ran

- `git show 46101d4d`, then read `os/ci/release-inputs.py` and `os-image.yml:53-142`.
- `git grep` across `os/ci`, `os/tests`, `.github` and `docs` for consumers of the evidence files, for the `legacy` kind, `installer-isos`, `release-inputs`, `picker_source` and `script13x`, and for `download-artifact` and `actions/cache` in the workflows.
- Read `installer_inspect.py:60-200`, the `LIVE` uses in `two_disk_vm.py` and `test_owner_equality.py:60-78`.
- `python3 -I /var/home/ares/AresOS/os/ci/release-inputs.py` in a scratch folder, which I deleted afterwards.
- Listed the ISO templates in the fetched `script136.js` and the `script\d+.js` references in the live `index.html`, and ran the kinds test against the archived `script135` picker.
- Small HTTPS checks:
  - `script135.js` on `main`: 404;
  - legacy ISO: HEAD returns 200;
  - legacy `-CHECKSUM`: GET returns 200 with the pinned hash.
- Nothing was committed, pushed or dispatched, and nothing ran with sudo.

SAFE
