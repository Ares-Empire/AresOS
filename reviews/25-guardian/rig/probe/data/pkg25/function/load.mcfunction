# DEVELOPMENT AID of package 25 (the real-game check): the rig's probe blocks. /trigger needs no cheats, so the home
# keeps its commands off, as the AresOS create flow makes it. `/trigger pkg25 set <n>` (n 1 to 56) sets a glass block
# in the air above the home pad (act.mcfunction says where); `set <100 + n>` says whether it is there. Each answer goes to
# chat, and so into the game's log, where the rig reads it.
scoreboard objectives add pkg25 trigger
