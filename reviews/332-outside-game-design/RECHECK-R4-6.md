# Recheck 6 of HOME-OUTSIDE.md revision 4

Codex `gpt-6.2-sol` `high`, read-only, on `be4f4950` (the lead's fix for recheck 5). The should-fix (icons return only on the clean-read back-out, section 6 at :566) and the nit (the overlap test forces a Picture commit against `set look C`) go to package 12's brief (board).

`be4f4950` closes all four R4-5 points. Package 12 can lock the settings directory in `set_value` before `chosen` and hold it through `write`’s atomic replacement, with the supervisor’s style commit using the same path. The failed-read SETUP exit now preserves the file, returns to OFF (`quit`), and shows a notice. The test notes cover both laptop states, unchanged bytes, and an unchanged home style after `set look C`. Both section references are correct. [Settings code](os/config/usr/libexec/aresos-settings:110) · [Lock rule](docs/design/HOME-OUTSIDE.md:475) · [SETUP transition](docs/design/HOME-OUTSIDE.md:854) · [Test notes](docs/design/HOME-OUTSIDE.md:1481)

- **Should-fix** — The prose still promises that icons return whenever the owner backs out. The failed-read exit keeps the Minecraft style, which hides them. Tie the return of icons to the clean-read Picture outcome. [docs/design/HOME-OUTSIDE.md:566](docs/design/HOME-OUTSIDE.md:566)
- **Nit** — In the package 12 brief, make the overlap test force a Picture commit to contend with `set look C`, then assert that both values survive. Two calls launched together can pass without exercising the stale-read race. [docs/design/HOME-OUTSIDE.md:1484](docs/design/HOME-OUTSIDE.md:1484)

READY