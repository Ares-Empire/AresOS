Rechecked PR #114 at `44339be0bc659f24fea30a6ace52b7b8163acdc6`. Two focus failures block it.

- Desktop 1.0 and 1.1 lose the world return when the editor deactivation, the compositor’s next-window activation, and the editor close arrive in three separate reads. The base requested world activation for this sequence. [Handoff logic](/var/home/ares/AresOS-53c-laptop-home/os/config/usr/libexec/aresos-shell:3975)
- After the laptop home reports `view_focus false`, a genuine foreground editor close can still leave the world without focus. I reproduced this when the compositor reports its next-window activation in the same read as the close. [Close handling](/var/home/ares/AresOS-53c-laptop-home/os/config/usr/libexec/aresos-shell:3862)

Five targeted helper tests passed in memory. I inspected the GTK focus and reconnect callbacks statically. No files changed, and I ran no build or CI checks.

CHANGES-NEEDED