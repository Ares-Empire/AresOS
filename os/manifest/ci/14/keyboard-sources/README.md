# Actual pinned ISO console maps

These three complete maps were read as ordinary compressed files from the
already whole-hash-verified package 14 ISO, with `unsquashfs -cat` at offset
314167296, then decompressed in memory. `index.json` records compressed and
decompressed hashes. No map was loaded and no keyboard setting changed.

The XKB-derived maps under `/usr/lib/kbd/keymaps/xkb` show German keycode 26
producing U+00FC, and US International keycode 21 with AltGr producing U+00FC.
Plain US keycode 26 produces `[`. These differ from the legacy 7-bit German map;
future physical testing must check the actually loaded map and public text,
not infer password entry from an upstream legacy map's filename. The intended
successful trial could use console `us-intl` and X11 `us` variant `intl`, followed
by a return to German. This is source evidence only: that trial has **not run**.
