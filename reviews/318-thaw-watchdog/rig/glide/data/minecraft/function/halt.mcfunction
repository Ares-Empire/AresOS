# Stops the glide and says in chat (and so in the game's log) how many ticks of it ran: 1200 is the whole route.
schedule clear minecraft:glidetick
tellraw @a [{"text":"pkg41 glide ticks: "},{"score":{"name":"#t","objective":"pkg41"}}]
