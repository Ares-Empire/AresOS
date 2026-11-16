# Package 44: the laptop-screen home (design study): progress

Builder: one Claude agent on Fable 5.2 (a new design that is not scoped yet). Nothing under `os/` or `mod/` changes.
Everything in this folder is a development aid for choosing a design, not product code.

## Plan (2026-11-16)

What I learned before drawing anything:
- The world shows the town from inside: big logos, one row at a time, noon. What it cannot show is everything at once.
  The laptop screen can, so each direction below shows all of My apps in one look.
- The laptop sits beside a bright world. It should be calm: near-black, little motion, gold only as an accent.
- The companions' runtime (`~/companions/runtime/README.md`, read only) sees a screen from the side: a floor, ledges
  with a left end, a right end and a height, and boxes that hide things. A home built from floors and ledges is ready
  for them as it is.
- The app helper serves one client today: a second `hello` closes the first one's connection, and "My apps", pins and
  short names live in the mod's own file, not in the helper. The report says what the protocol needs for a second
  client.

Three directions, each a clickable page at 1920 x 1080 with the same test town (5, 12, 24 or 40 test apps):

1. **Night street** (`prototypes/street/`): the same town seen from the side, at night. The four avenues are four
   streets, one above the other, each with its group colour. Every app is its block logo standing on its street, with
   its doorway, its name and its short name, as in the world. A house is lit while its app runs. Its floors and roofs
   are the ledges companions walk on later. Why: it is the town itself, it is calm, and it is the one whose shape the
   companions already understand.
2. **Map table** (`prototypes/map/`): the town from straight above, every logo laid flat at its real place around
   the gold home block. Why: the most literal "same home from another angle", and what he learns in the world (Games
   are east) works here too.
3. **Console** (`prototypes/console/`): no picture at all. The clock, a `/name` line as in the chat, and his apps as
   four short columns in the group colours. Why: the plainest and fastest, to compare the two pictures against.

Shared by all three, because they are the world's own habits: the hotbar's nine pinned apps along the bottom with the
keys 1 to 9, typing a name or a short name to find an app, a click to open it.

Order of work: this plan, the prototypes, pictures of each (headless only), a memory measurement in the system's web
engine, the report here, `docs/design/LAPTOP-HOME.md`, the pull request.

## Done

- (nothing yet)
