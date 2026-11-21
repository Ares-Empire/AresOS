# 320: known limits

Low-harm edge cases kept as limits under the brief's bar ("The bar"), each with its reason. None of them can stop a
key from changing its level, take the keyboard or the pointer, or touch the owner's running system.

## Step 1 (the keys and the settings)

1. **Two overlapping `aresos-settings set` calls can lose one update.** Each reads the file, changes one value and
   renames a whole new file into place, so the file is never torn, but the later rename can carry the older value of
   the other setting. Reason: the owner changes one setting at a time from one screen (later the mod's
   `set_setting`, one request at a time); a lost update shows at once and is fixed by setting it again. The brief
   lists it for the code review.
2. **A read-back that hangs past 2 s shows no plate for that press.** The change has happened; only the plate is
   skipped. Reason: a hung `wpctl` or `brightnessctl` read means PipeWire or logind is stuck, and the next press tries
   again.
3. **When the change lock stays busy for 1 s, the presses in that time change without it.** Two of them can then take
   the same sequence number, and the plate may drop one of the two. Reason: the lock is only busy that long when a
   device command hangs (each is cut at 3 s); the levels still change, and the next normal press puts the right level
   on the plate.
4. **A plate shown by `aresos-settings set` logs nothing.** `aresos-settings` hands `aresos-level` no output of its
   own (stdout and stderr go to `/dev/null`), so the notifier's reason for a missing plate is not logged on that path,
   and an indicator that `set` started cold keeps `/dev/null` as its stderr for its life (until a minute after the
   last key). Reason: the notifier and the program outlive the `set` call, and a caller that reads `set`'s output (a
   terminal tool, later the shell's `set_setting`) would otherwise wait up to a minute. The keys' path logs to the
   session's journal as usual, and the first key press after a broken start logs the same reason.
5. **A program that never takes its name is retried one launch at a time.** With a held key from cold, each notifier
   that waited for the launch lock and still finds the name unowned starts its own attempt after the previous one was
   ended and reaped, up to 5 s each, never two at once. Reason: this only happens with a broken indicator; the levels
   change at once regardless, and each notifier waits at most 6 s for the lock.
6. **A settings file from a newer version is treated as broken.** It gives the defaults and one journal line, and the
   next `set` replaces it with a version 1 file, dropping values only the newer version knows. Reason: this needs an
   image rollback after a later settings package; the three values are re-set in seconds.
7. **On a machine without a backlight, each brightness-up press logs brightnessctl's line** "Failed to read any devices
   of class 'backlight'." to the journal. Reason: informative, a few lines per press on a desktop PC or VM, and no LED
   is touched.
8. **Volume up at a level above 100 % that a program set brings it down to 100 %.** This is `wpctl --limit 1.0`, as
   the key did before package 320. Reason: the brief keeps today's commands and limits.

## Step 2 (the indicator)

1. **Unrecognised or slow PipeWire routes show “Volume”.** The graph lookup lasts at most 300 ms and repeated
   requests can share an in-flight snapshot. A route that changes during that lookup can leave the previous label
   on one showing. The device action and the level sent by the key stay independent of that label.
2. **A muted fraction has no dim grey half-step.** A muted 62 % lights 12 grey steps, matching the study. The full,
   partial, and mute sprites keep their original appearance.
3. **An up request that first reaches 100 % flashes too.** The indicator receives the new reading, so the first hit
   and a press at the limit look the same. The last step returns to lit after 150 ms, and each repeat restarts that
   interval.
4. **The hide interval starts when the indicator receives the request.** The request carries a sequence and a
   reading. A cold start or a slow read-back can shift the plate's appearance and disappearance later than the
   physical press. Step 3 measures the normal lag and repeat behaviour.

## Step 3 (headless checks)

1. **Tall fallback glyphs can touch the plate's top border.** Pango aligns a fallback face with the Jersey 10
   baseline. The Cyrillic Ж from the test font reaches the first few rows in the 2x capture. Its foreground and
   shadow use the pack's colours, and the rest of the plate matches the study. Reason for keeping the shared
   baseline: the fallback handles uncommon letters in sound device names, and moving the baseline would also shift
   the Jersey 10 letters in a mixed name.
2. **The installed PyGObject emits a deprecation warning at bus registration.** Fedora 44's PyGObject 3.56.3
   reports the warning from `Gio.DBusConnection.register_object` on healthy startup. Reason for leaving it: the
   callback, name ownership, cold and warm calls and the no-protocol exit all worked with the pinned harness
   packages. The warning is diagnostic and the registered method still works.
