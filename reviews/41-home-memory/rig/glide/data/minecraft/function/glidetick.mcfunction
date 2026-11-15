# One server tick of the glide: 1.08 blocks (sprint-flying's 21.6 blocks a second), level, along the flat route's
# legs: north for 300 ticks (15 s), south for 600 (30 s, back over home), north for 300 (15 s); then it stops.
scoreboard players add #t pkg41 1
execute if score #t pkg41 matches ..300 as @a at @s rotated 180 0 run tp @s ^ ^ ^1.08
execute if score #t pkg41 matches 301..900 as @a at @s rotated 0 0 run tp @s ^ ^ ^1.08
execute if score #t pkg41 matches 901..1200 as @a at @s rotated 180 0 run tp @s ^ ^ ^1.08
execute if score #t pkg41 matches ..1199 run schedule function minecraft:glidetick 1t
