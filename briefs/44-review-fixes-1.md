# 44, review fixes 1: the draft a build can follow

Review 1 (`reviews/44-laptop-home/REVIEW-1.md`, fresh Claude Opus 5.5 reviewer): CHANGES-NEEDED. The owner can choose a
direction from the study as it is; the draft (`docs/design/LAPTOP-HOME.md`) needs fixes before a build can follow it.
None of them changes the recommended direction (Night street).

**Builder:** one fresh Claude agent on Opus 5.5: text, two prototype changes, two pictures and one measurement against
a findings list.

Apply findings 1 to 13 as their "Fix" lines say, in LAPTOP-HOME.md, the report (`PROGRESS.md`) and the prototypes
where they apply. Where a finding offers a choice, these are the lead's calls:
- **2 (the login):** a token of the laptop home's own that lasts the whole session and is accepted only for the view
  role, so a view can never displace the game. Write down who makes it and hands it over (the supervisor, package 23c's
  side, `linux-aresos`) as a PLAN-GAP.
- **4 (more than 16 apps in a group):** design the answer in Night street (for example, the street pages or shifts so
  the house he is looking for comes into view; your call), show it with a picture of a town of about 45 apps with one
  group past 16, and correct the report's "every app is always on screen".
- **5 (from the world to the laptop):** describe the way; keep JUDGMENT-CALL 5 (a reserved key) as the owner's call,
  with your recommendation.
- **6 (typing):** search the helper's names, generic names and keywords as the helper gives them; other programs show
  under the helper's own grouping or none, never a group the laptop invents.
- **7 (companions' motion):** measure one moving sprite at a companion's size in WebKit headless (CPU and memory, a
  minute), and write the result and what it means for the companions version.
- **8 (JUDGMENT-CALL 3):** add a picture of Night street with every logo in full colour, and make section 10's questions
  match the report's six, each with a recommendation.

Keep the rules of `briefs/44-laptop-home.md`. Also: run no `rpm-ostree`, `bootc` or `ostree` command and no
`test_owner_*` module. Don't edit REVIEW-1.md. Commit and push after each part that works; commits end with
`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. No `gh` commands.
