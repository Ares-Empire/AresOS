# Recheck 2 of HOME-OUTSIDE.md revision 4

I read `reviews/332-outside-game-design/RECHECK-R4.md` and the parts of `docs/design/HOME-OUTSIDE.md` that touch its finding 2. That was sections 5 and 6, package 3V's rows, "To tell him", and section 12's harm rows and known limits. I checked only the four points you asked about. A bare `:N` is a line of the note.

1. **The settings row's trigger list is fixed.** Section 5's settings row (`:430`) now says that, from 3V on, each of these ends in `aresos-desktop video`:
   - a change between `picture` and `video`;
   - setting `home` to `video` while it already is `video`;
   - any write of `video-file`, also the same value;
   - a change of `video-battery-pause`.

   The command row (`:429`) says that in the Video style this "starts the player afresh and clears its count of ends". Picking Video again is no longer a no-op.

2. **The "On again" list matches, so the toast works.**
   - `:645` lists: picking Video again (also while the style already is Video), writing a video file (also the same one), changing `video-battery-pause`, or logging in again.
   - It says each of these runs `aresos-desktop video`, which starts the player afresh with the count at zero.
   - It also says this list and section 5's list are the same list.
   - So the toast's instruction now does what it says. That covers the toast itself ("Pick Video again to try it", `:643`) and "To tell him" (`:1304-1305`).
   - The `video-battery-pause` gap that the earlier recheck noted is closed.

3. **3V's test row has the run.** `:1181` now says: "After the video was turned off, picking Video again (the style is still Video) plays it again."

4. **Nothing nearby contradicts these lines in a way that would mislead a builder.**
   - `:454` (a change between Picture and Video ends in `aresos-desktop video` alone) agrees. So does `:646` (a stop for a change of style or settings is not an end).
   - Three wording nits, none blocking:
     - **`:1527-1528`.** This known limit says the video "stays off until he picks Video again or logs in again". It leaves out a write of the video file and a change of `video-battery-pause`. It is shorter than `:430` and `:645` but doesn't contradict them, and those two are the binding lists. Suggested wording: "…or changes a video setting".
     - **`:645`.** It calls itself the same list as `:430`, but it adds "logs in again". A login isn't a settings write and doesn't run the command; the boot starts the player (`:474`). The effect is the same: a fresh player with the count at zero. "Each of these but a new login runs…" would be exact.
     - **`:642-644`.** "It stays off for the session, also across a new supervisor" reads as absolute on its own. The next bullet, "On again", qualifies it. "…until one of the steps under On again" would close that.

READY
