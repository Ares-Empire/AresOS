# 18d, parallel start

**Owner's decision, 2026-11-09:** build the remaining packages alongside Mail, not one after another. This note
changes only **where brief 18d starts**. Everything else in `briefs/18d-base-slim.md` stands. Where they differ, this
note wins.

- Branch `pkg/18d-base-slim` starts from the head of the Mail branch `pkg/19-mail` (`d3babf1f`), not from `main` after
  Mail's merge. Mail's boundary check (rounds 15 to 17) and its definitions are already there, so read the files the
  brief names on this branch.
- Don't merge other branches yourself. When Mail merges, the lead tells you to merge `main` in.
- Chrome (brief 20) is being built at the same time on its own branch, from the same Mail head. It will add its ask
  rules to the settings generator as it is today. Keep the generator's interface for adding an app's rules simple and
  documented, so Chrome can move onto the slim generator with little change. Say in the report what Chrome must do.
- **Order of merging:** Mail first, then whichever of 18d, 19b and 20 is ready. The package that merges later merges
  `main` in, regenerates every generated file, reruns every Control workflow twice, and has its reviews cover the
  combined head.
