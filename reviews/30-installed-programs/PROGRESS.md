# Package 30, review fixes 1: progress

Brief: `briefs/30-review-fixes-1.md`. **Step A (the security review's five fixes) is done**; step B (the package
review's findings) is next. Builder of step A: a Claude agent (Opus 5.5), 2026-11-13/14. Step B deletes this file.

Step A commits on `pkg/30-installed-programs`, on top of `5fbe6d20`:

- `7efd4994` A4: `--expand-environment=no`
- `cbf2e08a` A1 and A5 (desktop files): bounded discovery off the serving loop, links confined
- `25df944c` A2, A3 and A5 (icons): converter memory ceiling, drawn-only SVG, cache budget, confined icon folders
- `5c6b73dd` helper header, timing margin for one test

`os/` files touched in step A: `config/usr/libexec/aresos-shell`, `ci/image-checks.sh` (one added check),
`tests/test_aresos_shell.py` and `tests/test_aresos_shell_discovery.py` (see "Existing tests changed"), new
`tests/test_aresos_shell_hardening.py`, new `tests/check_aresos_shell_launch.py`, `tests/check_aresos_shell_icons.py`.
Nothing under `mod/`, no registry entry, no doc.

## Done, per finding (security review 1)

Every new test was also run with its part of the fix switched off (a scratch mutation script that patches the
helper in memory); each one failed then. New tests are in `os/tests/test_aresos_shell_hardening.py` unless named
otherwise.

### FIX 1: discovery can't stall or exhaust the helper

- `Catalogue.scan()` is one bounded pass; `ScanBudget` counts every folder entry looked at, accepted or not:
  4096 entries, 256 folders, nesting 8, 32 MiB of desktop entries, 2 seconds. The byte bound is checked from
  the stat sizes before anything is read (hard links cost no disk space), and again as bytes are read.
- A pass that hits a bound, raises or blocks changes nothing: the last good catalogue stays in force. The bound
  is logged once, until a pass completes again.
- Folders are walked through descriptors (`walk_folder`): a linked subfolder is never entered, not even one
  swapped in after the listing (`O_NOFOLLOW` relative to its parent).
- `Discovery` runs the scans on its own thread (`aresos-discovery`). The serving loop only takes a finished
  catalogue and asks for the next scan when one is due, at most one at a time and at most every three seconds
  of helper time. A scan blocked for over 4 s is logged once. `build()` uses it. Before the first scan finishes,
  the reviewed registry alone is in force; `build()` waits up to 3 s for that first scan, so the first list
  normally has every program. `Server.close()` stops it.
- Tests: `DiscoveryBoundsTest.test_ten_thousand_hidden_entries_end_the_scan_at_its_bound_and_keep_the_last_good_catalogue`
  (no file read, one log line over two passes, recovers once the folder is sane),
  `test_hard_links_to_one_large_malformed_entry_are_refused_before_any_is_read` (40 links to one 1 MiB entry, 40 MiB in all: none read),
  `test_bytes_are_counted_as_they_are_read_too`, `test_folders_depth_and_time_are_bounded`,
  `test_a_linked_subfolder_is_never_entered_even_if_swapped_in_after_listing`;
  `DiscoveryOffTheLoopTest.test_build_scans_on_its_own_thread_and_a_blocked_scan_never_stalls_the_helper`
  (through `build()`: a blocked scan, five ticks and lists each under 0.2 s, the change arrives after release),
  `test_a_folder_that_keeps_changing_is_rescanned_at_most_every_few_seconds_and_never_on_the_loop`
  (a writer thread keeps changing a folder for 2.5 s while 0.5 s scans run: no overlap, every tick under
  0.25 s, the last good catalogue always listed),
  `test_a_failing_scan_keeps_the_last_good_catalogue_and_the_helper_answering`,
  `test_before_the_first_scan_the_registry_alone_is_in_force_with_the_1_0_revision`.

### FIX 2: the icon converter has a real memory ceiling

- The converter starts under util-linux `prlimit --as=268435456 --` (256 MiB address space), set before `bwrap`
  starts and inherited by everything it starts. Measured on the laptop with the real sandbox: every icon that
  converts at all (SVG and PNG up to 1024 px; 2048 px already fails ImageMagick's own limits) needs under 128 MiB.
  A missing `bwrap` stays an `OSError`, as before. `image-checks.sh` now also checks `/usr/bin/prlimit`.
- `drawn_svg()` (expat) refuses, before any conversion, an SVG with an `image`, `feImage` or `foreignObject`
  element, XInclude, any `href` or `url()` not to `#id` (`data:` included), a CSS escape or `@import` in plain
  attributes or `<style>`, a processing instruction (`xml-stylesheet`), a DTD or entity, or XML that is not
  well formed. The refusal is remembered for that version of the file.
- Tests: `ConverterMemoryTest.test_the_converter_and_everything_it_starts_run_under_an_address_space_limit`
  (a stand-in converter and its forked child both report the limit and cannot map 512 MiB),
  `test_the_limit_is_set_by_prlimit_before_the_sandboxed_converter_starts`,
  `test_a_small_svg_embedding_a_large_compressed_picture_is_refused_before_conversion` (a 41 KB SVG whose
  embedded PNG decodes to 16000x16000), `test_each_construct_that_refers_to_a_picture_is_refused_before_conversion`
  (16 constructs, one subtest each), `test_drawn_shapes_with_local_references_still_convert`.
  Real converter (`check_aresos_shell_icons.py`): `test_embedded_picture_bomb_is_refused_and_capped_even_if_it_got_through`
  (with the refusal bypassed, the real converter fails under the ceiling within the timeout instead of decoding
  about 1 GB).

### FIX 3: the icon cache has a budget

- Budget: 512 files (two generations for each of `MAX_APPS`) and 32 MiB, checked before converting and again
  with the real size before writing. Over it, the picture is simply not cached: the program keeps its fallback
  look, and "budget used up" is logged once while the cache is full. This is not remembered as a failure, so the
  picture is made once there is room.
- A changed source's older picture is removed as soon as the source changes. After each complete pass, every
  picture no listed program uses is removed (removed programs, earlier helper runs), and so are leftovers of
  interrupted writes (`.icon-*`, `.convert-*`). Other files in the folder are left alone.
- Tests: `IconBudgetTest.test_changing_one_icons_time_a_thousand_times_leaves_one_picture`,
  `test_pictures_of_programs_no_longer_listed_and_leftovers_are_removed_after_a_complete_pass`,
  `test_a_full_cache_keeps_the_fallback_look_and_says_so_once`,
  `test_the_byte_budget_is_checked_with_the_real_picture_size_before_writing`.

### FIX 4: systemd changes no argument

- `ScopeLauncher.command` passes `--expand-environment=no` right before `--`, for every launch.
- Tests: the two existing exact-command assertions (they fail without the flag). Real route,
  `os/tests/check_aresos_shell_launch.py` (explicit laptop check: hosted Ubuntu has no user manager):
  `test_literal_dollar_words_from_exec_name_and_icon_arrive_unchanged` runs a parsed desktop entry through the
  real `systemd-run --user --scope`; a stand-in that writes its arguments and cgroup receives `${HOME}` unchanged
  from `Exec`, `%c` and `%i`, inside `app.slice/app-aresos-…scope`.
  `test_control_the_same_route_without_the_flag_is_expanded_by_systemd` proves the check can fail: without the
  flag, systemd 259.9 turns all three into the HOME value. The stand-in opens no window and gets no display
  variable; its transient scope ends with it, and the check stops it by its unit name if it did not.

### FIX 5: links are checked before anything is read

- `open_confined()` pins the file with `O_PATH` (nothing read, no device or FIFO opened), checks its real
  location in `/proc/self/fd`, and reopens it through the pin, so the file read is the file checked.
- A desktop file must resolve inside the five application folders or a Flatpak deployment
  (`~/.local/share/flatpak/app`, `/var/lib/flatpak/app`); anything else is skipped with one log line.
- Icon theme and size folders are listed only after the same check (`confined_listing`), against their own icon
  root or a Flatpak deployment. A Flatpak export's icon link into its deployment is accepted, so Flatpak programs
  get their pictures (this settles the package review's finding 5). A named icon is opened confined; an explicit
  absolute `Icon` path is read as written, as before.
- Tests: `DesktopLinkTest.test_a_link_to_a_file_outside_is_skipped_with_one_log_line_and_never_read`,
  `test_links_inside_the_application_folders_are_followed`, `test_realistic_flatpak_export_layout_is_listed`
  (the layout `flatpak install` leaves: `exports/…` → `../../../app/<id>/current/active/export/…`, with the
  `current` and `active` links), `test_the_file_read_is_the_file_checked_even_if_the_link_changes_after_the_check`,
  `test_a_link_to_a_fifo_or_device_outside_is_refused_without_opening_it`;
  `IconFolderLinkTest.test_a_theme_folder_that_links_out_is_never_listed`,
  `test_a_flatpak_export_icon_is_found_in_its_deployment_and_converted`,
  `test_a_named_icon_is_read_only_inside_its_folders_but_an_absolute_icon_path_as_written`.

### Existing tests changed (all others unchanged)

- `test_aresos_shell.py` `test_open_app_starts_its_own_user_scope_without_the_launch_secrets` and
  `test_aresos_shell_discovery.py` `test_discovered_launch_uses_its_own_scope_and_app_slice_without_a_shell`:
  their exact `systemd-run` command gains `--expand-environment=no` (FIX 4 cannot be met otherwise).
- `test_aresos_shell_discovery.py` `test_nested_desktop_ids_and_flatpak_file_symlinks`: its "Flatpak" link
  pointed at an arbitrary file outside every folder, which is exactly FIX 5's scenario. The target now lies in a
  Flatpak deployment, as real exports do (`DiscoveryBase` passes that deployment).
- `check_aresos_shell_icons.py` `test_svg_cannot_read_a_neighbor_image_or_reach_a_local_listener`: such SVGs are
  now refused first; with the refusal bypassed the original sandbox assertions still run and pass.

### Real-world smoke run (no window, no launch)

The old (`5fbe6d20`) and new helper ran headless (no `WAYLAND_DISPLAY`, private runtime folder and icon cache,
the laptop's real application folders), each listed over its socket at once and after 25 s, then stopped by PID:
both listed the same 56 programs from all five sources at the first list; pictures 33 (old) and 45 (new): none
lost, 12 gained (the Flatpak icons). The scratch caches were deleted afterwards.

## Left for step B (as the brief cuts it)

1. Finding 1 (blocking): window ownership by reviewed hints (`/usr/share/aresos/apps/hints/`), Lunar Client and
   Steam hints, unowned windows never confirm/keep/return; tests with time moving.
2. Finding 2: a 1.0 client sees today's window behaviour, also after a reconnect.
3. Finding 3: a 1.0 client asking for a discovered ID gets exactly the old failed-launch answer and journal entry.
4. Finding 4: a return that is no longer wanted is dropped.
5. Finding 6: Flatpak forwarding markers only in a recognised `flatpak run … --file-forwarding` command.
6. Finding 7: a Flatpak's app ID from its command when `X-Flatpak` is missing.
7. Verification: the headless end-to-end check (`check_aresos_shell_headless.py`, kcalc and btop) once more, and
   rerun `check_aresos_shell_launch.py` (FIX 4's real route) and `check_aresos_shell_icons.py`; push; both
   hosted runs, each awaited with one blocking `gh run watch`; the "Review fixes 1" section of `REPORT.md`
   (step A's part can be taken from this file); `docs/design/OS-BASE.md` B1 for hints. B1's package-30
   paragraph should also gain one sentence for step A: discovery scans run off the serving loop within hard
   bounds; desktop-file and icon links must stay inside their folders or a Flatpak deployment; the converter
   runs under an address-space ceiling and refuses SVGs that refer to pictures; the icon cache has a budget.
   Then delete this file.

Finding 5 of the package review is already settled by FIX 5 (see above); step B only needs to report it.

## Decisions step A took that the brief did not settle (JUDGMENT-CALL candidates for the report)

- **Bounds and their values:** a scan over any bound is discarded whole (not used partly), since a cut list
  would hide programs at random. Values from the laptop (about 250 entries, 1.6 MB, read in well under a second)
  with wide headroom; all are constants at the top of the helper. The old `MAX_APPS` cut (256 listed programs,
  logged) is unchanged.
- **Start-up:** until the first scan finishes the registry alone is in force; `build()` waits up to 3 s for that
  scan. Rejected: scanning synchronously at start (a stalled mount would stop the helper from ever serving).
- **Flatpak deployments** are `<flatpak root>/app/`, narrower than the brief's `/var/lib/flatpak/` and
  `~/.local/share/flatpak/`: exports only ever link into `app/<id>/…`, and the rest (the ostree repo, runtimes)
  needs no reading. Links between the five application folders are allowed ("inside the application folders").
- **Memory ceiling:** an address-space limit through `prlimit`, 256 MiB per process (bwrap and magick, which
  starts no delegates). Rejected: a memory-limited systemd scope per conversion (a D-Bus round trip to the user
  manager for each icon, for a tree of two processes) and `preexec_fn` (not safe in this threaded helper).
- **SVG refusal** follows the brief's "app icons are drawn shapes": even a local `<image href="#…">` is refused.
  A backslash is refused in plain attributes and `<style>` (librsvg reads them as CSS, where `u\72l(` is `url(`);
  namespaced editor metadata (Inkscape paths with backslashes) is ignored, as librsvg ignores it.
- **`--expand-environment=no` on every launch**, the three registry apps included: their arguments contain no
  `$`, so nothing changes for them, and no launch path is left that systemd could rewrite.
- **Icon folder link-outs are logged at debug level**, not warning: icon passes repeat every three seconds and
  a warning would repeat with them. Desktop-file link-outs log one warning per scan that reads them.
- **A blocked read** (a stalled mount) cannot be interrupted by the time bound; it stops only discovery, which
  keeps its last good catalogue, and is logged once after 4 s.

## Known limits after step A

- Listing still checks each program's executable (`os.access` on its absolute path) on the serving loop, as
  before; an `Exec` path on a stalled mount could still delay a list. Reading the folders is off the loop.
- A folder that stays over the entry bound is walked again (up to the bound) every three seconds, off the loop.
- Icon passes still reread each icon source every three seconds before finding it cached (unchanged behaviour).

## How to run the tests (laptop)

Never run the whole `os/tests` suite here (AGENTS.md: `test_owner_update` reaches the owner's real tools).

```
TMPDIR="$PWD/.work/30-installed-programs/tmp" python3 -m unittest discover -s os/tests -p 'test_aresos_shell*.py'
TMPDIR="$PWD/.work/30-installed-programs/tmp" python3 -m unittest discover -s os/tests -p 'check_aresos_shell_icons.py' -v
TMPDIR="$PWD/.work/30-installed-programs/tmp" python3 -m unittest discover -s os/tests -p 'check_aresos_shell_launch.py' -v
```

Results at the end of step A (2026-11-14): helper modules **Ran 224 tests, OK** (twice; 198 before step A);
real converter checks **Ran 7 tests, OK**; real launch route **Ran 2 tests, OK**. The hosted full-suite count
comes at the end of step B.
