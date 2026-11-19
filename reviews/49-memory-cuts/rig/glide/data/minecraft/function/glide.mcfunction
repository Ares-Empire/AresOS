# DEVELOPMENT AID of package 49 (copied from package 41) (measurement only): /function glide starts the rig's flight in the Nether home, where
# the caves stop a real flight within blocks and AresOS refuses spectator mode. glidetick moves the player as
# sprint-flying does, straight through whatever is in the way.
scoreboard objectives add pkg41 dummy
scoreboard players set #t pkg41 0
function minecraft:glidetick
