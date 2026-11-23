Rechecked PR #121 at `3a1ad6b41dce884550764260c133e922bdc0dd56`. Both round 2b fixes are in place. I found no blocking regression in the paths they touch.

- **Drafts.** Super preserves a hidden recipe-book query, including when an empty Apps screen sits over that inventory. An empty Apps screen over a draft-free inventory still yields to search and closes the container normally. [Draft guard](/var/home/ares/AresOS-53d-world-search/mod/src/client/java/dev/aresos/client/WorldSearchScreen.java:159) · [Container close](/var/home/ares/AresOS-53d-world-search/mod/src/client/java/dev/aresos/client/WorldSearchScreen.java:104)
- **Super handoff.** The one-second deadline cancels the search while leaving the mark in place. A late, split activation still minimizes nothing and sends no `shell_search`. A newer activation observed for another window clears the mark, and an on-time search still waits until the world is reported as the sole active window. [Handoff](/var/home/ares/AresOS-53d-world-search/os/config/usr/libexec/aresos-shell:4168)

**Known limits.** An unanswered request can suppress automatic uncover on the next manual return to the world. I reproduced the same effect when a window’s deactivation and reactivation arrived in one read and left the active set unchanged. A competing activation already in flight when Super is pressed can also drop the search.

All 24 focused helper tests passed with an in-memory journal. I reviewed the client changes by inspection. I ran no build, changed no files, and did not check or wait for CI.

SAFE