# One request of the host (tick.mcfunction): set probe block n, or say whether it is there. Then the score is 0 again.
# Block n (1 to 56) is at x = 1 + (n - 1) mod 14, y = 90, z = 2 + (n - 1) div 14: all in the home pad's chunk.
execute if score @s pkg25 matches 1 run setblock 1 90 2 minecraft:glass
execute if score @s pkg25 matches 1 if block 1 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 1 placed"}]
execute if score @s pkg25 matches 101 if block 1 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 1 present"}]
execute if score @s pkg25 matches 101 unless block 1 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 1 absent"}]
execute if score @s pkg25 matches 2 run setblock 2 90 2 minecraft:glass
execute if score @s pkg25 matches 2 if block 2 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 2 placed"}]
execute if score @s pkg25 matches 102 if block 2 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 2 present"}]
execute if score @s pkg25 matches 102 unless block 2 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 2 absent"}]
execute if score @s pkg25 matches 3 run setblock 3 90 2 minecraft:glass
execute if score @s pkg25 matches 3 if block 3 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 3 placed"}]
execute if score @s pkg25 matches 103 if block 3 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 3 present"}]
execute if score @s pkg25 matches 103 unless block 3 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 3 absent"}]
execute if score @s pkg25 matches 4 run setblock 4 90 2 minecraft:glass
execute if score @s pkg25 matches 4 if block 4 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 4 placed"}]
execute if score @s pkg25 matches 104 if block 4 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 4 present"}]
execute if score @s pkg25 matches 104 unless block 4 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 4 absent"}]
execute if score @s pkg25 matches 5 run setblock 5 90 2 minecraft:glass
execute if score @s pkg25 matches 5 if block 5 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 5 placed"}]
execute if score @s pkg25 matches 105 if block 5 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 5 present"}]
execute if score @s pkg25 matches 105 unless block 5 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 5 absent"}]
execute if score @s pkg25 matches 6 run setblock 6 90 2 minecraft:glass
execute if score @s pkg25 matches 6 if block 6 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 6 placed"}]
execute if score @s pkg25 matches 106 if block 6 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 6 present"}]
execute if score @s pkg25 matches 106 unless block 6 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 6 absent"}]
execute if score @s pkg25 matches 7 run setblock 7 90 2 minecraft:glass
execute if score @s pkg25 matches 7 if block 7 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 7 placed"}]
execute if score @s pkg25 matches 107 if block 7 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 7 present"}]
execute if score @s pkg25 matches 107 unless block 7 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 7 absent"}]
execute if score @s pkg25 matches 8 run setblock 8 90 2 minecraft:glass
execute if score @s pkg25 matches 8 if block 8 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 8 placed"}]
execute if score @s pkg25 matches 108 if block 8 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 8 present"}]
execute if score @s pkg25 matches 108 unless block 8 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 8 absent"}]
execute if score @s pkg25 matches 9 run setblock 9 90 2 minecraft:glass
execute if score @s pkg25 matches 9 if block 9 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 9 placed"}]
execute if score @s pkg25 matches 109 if block 9 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 9 present"}]
execute if score @s pkg25 matches 109 unless block 9 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 9 absent"}]
execute if score @s pkg25 matches 10 run setblock 10 90 2 minecraft:glass
execute if score @s pkg25 matches 10 if block 10 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 10 placed"}]
execute if score @s pkg25 matches 110 if block 10 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 10 present"}]
execute if score @s pkg25 matches 110 unless block 10 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 10 absent"}]
execute if score @s pkg25 matches 11 run setblock 11 90 2 minecraft:glass
execute if score @s pkg25 matches 11 if block 11 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 11 placed"}]
execute if score @s pkg25 matches 111 if block 11 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 11 present"}]
execute if score @s pkg25 matches 111 unless block 11 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 11 absent"}]
execute if score @s pkg25 matches 12 run setblock 12 90 2 minecraft:glass
execute if score @s pkg25 matches 12 if block 12 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 12 placed"}]
execute if score @s pkg25 matches 112 if block 12 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 12 present"}]
execute if score @s pkg25 matches 112 unless block 12 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 12 absent"}]
execute if score @s pkg25 matches 13 run setblock 13 90 2 minecraft:glass
execute if score @s pkg25 matches 13 if block 13 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 13 placed"}]
execute if score @s pkg25 matches 113 if block 13 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 13 present"}]
execute if score @s pkg25 matches 113 unless block 13 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 13 absent"}]
execute if score @s pkg25 matches 14 run setblock 14 90 2 minecraft:glass
execute if score @s pkg25 matches 14 if block 14 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 14 placed"}]
execute if score @s pkg25 matches 114 if block 14 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 14 present"}]
execute if score @s pkg25 matches 114 unless block 14 90 2 minecraft:glass run tellraw @a [{"text":"pkg25 probe 14 absent"}]
execute if score @s pkg25 matches 15 run setblock 1 90 3 minecraft:glass
execute if score @s pkg25 matches 15 if block 1 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 15 placed"}]
execute if score @s pkg25 matches 115 if block 1 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 15 present"}]
execute if score @s pkg25 matches 115 unless block 1 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 15 absent"}]
execute if score @s pkg25 matches 16 run setblock 2 90 3 minecraft:glass
execute if score @s pkg25 matches 16 if block 2 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 16 placed"}]
execute if score @s pkg25 matches 116 if block 2 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 16 present"}]
execute if score @s pkg25 matches 116 unless block 2 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 16 absent"}]
execute if score @s pkg25 matches 17 run setblock 3 90 3 minecraft:glass
execute if score @s pkg25 matches 17 if block 3 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 17 placed"}]
execute if score @s pkg25 matches 117 if block 3 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 17 present"}]
execute if score @s pkg25 matches 117 unless block 3 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 17 absent"}]
execute if score @s pkg25 matches 18 run setblock 4 90 3 minecraft:glass
execute if score @s pkg25 matches 18 if block 4 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 18 placed"}]
execute if score @s pkg25 matches 118 if block 4 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 18 present"}]
execute if score @s pkg25 matches 118 unless block 4 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 18 absent"}]
execute if score @s pkg25 matches 19 run setblock 5 90 3 minecraft:glass
execute if score @s pkg25 matches 19 if block 5 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 19 placed"}]
execute if score @s pkg25 matches 119 if block 5 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 19 present"}]
execute if score @s pkg25 matches 119 unless block 5 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 19 absent"}]
execute if score @s pkg25 matches 20 run setblock 6 90 3 minecraft:glass
execute if score @s pkg25 matches 20 if block 6 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 20 placed"}]
execute if score @s pkg25 matches 120 if block 6 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 20 present"}]
execute if score @s pkg25 matches 120 unless block 6 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 20 absent"}]
execute if score @s pkg25 matches 21 run setblock 7 90 3 minecraft:glass
execute if score @s pkg25 matches 21 if block 7 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 21 placed"}]
execute if score @s pkg25 matches 121 if block 7 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 21 present"}]
execute if score @s pkg25 matches 121 unless block 7 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 21 absent"}]
execute if score @s pkg25 matches 22 run setblock 8 90 3 minecraft:glass
execute if score @s pkg25 matches 22 if block 8 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 22 placed"}]
execute if score @s pkg25 matches 122 if block 8 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 22 present"}]
execute if score @s pkg25 matches 122 unless block 8 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 22 absent"}]
execute if score @s pkg25 matches 23 run setblock 9 90 3 minecraft:glass
execute if score @s pkg25 matches 23 if block 9 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 23 placed"}]
execute if score @s pkg25 matches 123 if block 9 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 23 present"}]
execute if score @s pkg25 matches 123 unless block 9 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 23 absent"}]
execute if score @s pkg25 matches 24 run setblock 10 90 3 minecraft:glass
execute if score @s pkg25 matches 24 if block 10 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 24 placed"}]
execute if score @s pkg25 matches 124 if block 10 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 24 present"}]
execute if score @s pkg25 matches 124 unless block 10 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 24 absent"}]
execute if score @s pkg25 matches 25 run setblock 11 90 3 minecraft:glass
execute if score @s pkg25 matches 25 if block 11 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 25 placed"}]
execute if score @s pkg25 matches 125 if block 11 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 25 present"}]
execute if score @s pkg25 matches 125 unless block 11 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 25 absent"}]
execute if score @s pkg25 matches 26 run setblock 12 90 3 minecraft:glass
execute if score @s pkg25 matches 26 if block 12 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 26 placed"}]
execute if score @s pkg25 matches 126 if block 12 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 26 present"}]
execute if score @s pkg25 matches 126 unless block 12 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 26 absent"}]
execute if score @s pkg25 matches 27 run setblock 13 90 3 minecraft:glass
execute if score @s pkg25 matches 27 if block 13 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 27 placed"}]
execute if score @s pkg25 matches 127 if block 13 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 27 present"}]
execute if score @s pkg25 matches 127 unless block 13 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 27 absent"}]
execute if score @s pkg25 matches 28 run setblock 14 90 3 minecraft:glass
execute if score @s pkg25 matches 28 if block 14 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 28 placed"}]
execute if score @s pkg25 matches 128 if block 14 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 28 present"}]
execute if score @s pkg25 matches 128 unless block 14 90 3 minecraft:glass run tellraw @a [{"text":"pkg25 probe 28 absent"}]
execute if score @s pkg25 matches 29 run setblock 1 90 4 minecraft:glass
execute if score @s pkg25 matches 29 if block 1 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 29 placed"}]
execute if score @s pkg25 matches 129 if block 1 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 29 present"}]
execute if score @s pkg25 matches 129 unless block 1 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 29 absent"}]
execute if score @s pkg25 matches 30 run setblock 2 90 4 minecraft:glass
execute if score @s pkg25 matches 30 if block 2 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 30 placed"}]
execute if score @s pkg25 matches 130 if block 2 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 30 present"}]
execute if score @s pkg25 matches 130 unless block 2 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 30 absent"}]
execute if score @s pkg25 matches 31 run setblock 3 90 4 minecraft:glass
execute if score @s pkg25 matches 31 if block 3 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 31 placed"}]
execute if score @s pkg25 matches 131 if block 3 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 31 present"}]
execute if score @s pkg25 matches 131 unless block 3 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 31 absent"}]
execute if score @s pkg25 matches 32 run setblock 4 90 4 minecraft:glass
execute if score @s pkg25 matches 32 if block 4 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 32 placed"}]
execute if score @s pkg25 matches 132 if block 4 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 32 present"}]
execute if score @s pkg25 matches 132 unless block 4 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 32 absent"}]
execute if score @s pkg25 matches 33 run setblock 5 90 4 minecraft:glass
execute if score @s pkg25 matches 33 if block 5 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 33 placed"}]
execute if score @s pkg25 matches 133 if block 5 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 33 present"}]
execute if score @s pkg25 matches 133 unless block 5 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 33 absent"}]
execute if score @s pkg25 matches 34 run setblock 6 90 4 minecraft:glass
execute if score @s pkg25 matches 34 if block 6 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 34 placed"}]
execute if score @s pkg25 matches 134 if block 6 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 34 present"}]
execute if score @s pkg25 matches 134 unless block 6 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 34 absent"}]
execute if score @s pkg25 matches 35 run setblock 7 90 4 minecraft:glass
execute if score @s pkg25 matches 35 if block 7 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 35 placed"}]
execute if score @s pkg25 matches 135 if block 7 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 35 present"}]
execute if score @s pkg25 matches 135 unless block 7 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 35 absent"}]
execute if score @s pkg25 matches 36 run setblock 8 90 4 minecraft:glass
execute if score @s pkg25 matches 36 if block 8 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 36 placed"}]
execute if score @s pkg25 matches 136 if block 8 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 36 present"}]
execute if score @s pkg25 matches 136 unless block 8 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 36 absent"}]
execute if score @s pkg25 matches 37 run setblock 9 90 4 minecraft:glass
execute if score @s pkg25 matches 37 if block 9 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 37 placed"}]
execute if score @s pkg25 matches 137 if block 9 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 37 present"}]
execute if score @s pkg25 matches 137 unless block 9 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 37 absent"}]
execute if score @s pkg25 matches 38 run setblock 10 90 4 minecraft:glass
execute if score @s pkg25 matches 38 if block 10 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 38 placed"}]
execute if score @s pkg25 matches 138 if block 10 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 38 present"}]
execute if score @s pkg25 matches 138 unless block 10 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 38 absent"}]
execute if score @s pkg25 matches 39 run setblock 11 90 4 minecraft:glass
execute if score @s pkg25 matches 39 if block 11 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 39 placed"}]
execute if score @s pkg25 matches 139 if block 11 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 39 present"}]
execute if score @s pkg25 matches 139 unless block 11 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 39 absent"}]
execute if score @s pkg25 matches 40 run setblock 12 90 4 minecraft:glass
execute if score @s pkg25 matches 40 if block 12 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 40 placed"}]
execute if score @s pkg25 matches 140 if block 12 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 40 present"}]
execute if score @s pkg25 matches 140 unless block 12 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 40 absent"}]
execute if score @s pkg25 matches 41 run setblock 13 90 4 minecraft:glass
execute if score @s pkg25 matches 41 if block 13 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 41 placed"}]
execute if score @s pkg25 matches 141 if block 13 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 41 present"}]
execute if score @s pkg25 matches 141 unless block 13 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 41 absent"}]
execute if score @s pkg25 matches 42 run setblock 14 90 4 minecraft:glass
execute if score @s pkg25 matches 42 if block 14 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 42 placed"}]
execute if score @s pkg25 matches 142 if block 14 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 42 present"}]
execute if score @s pkg25 matches 142 unless block 14 90 4 minecraft:glass run tellraw @a [{"text":"pkg25 probe 42 absent"}]
execute if score @s pkg25 matches 43 run setblock 1 90 5 minecraft:glass
execute if score @s pkg25 matches 43 if block 1 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 43 placed"}]
execute if score @s pkg25 matches 143 if block 1 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 43 present"}]
execute if score @s pkg25 matches 143 unless block 1 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 43 absent"}]
execute if score @s pkg25 matches 44 run setblock 2 90 5 minecraft:glass
execute if score @s pkg25 matches 44 if block 2 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 44 placed"}]
execute if score @s pkg25 matches 144 if block 2 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 44 present"}]
execute if score @s pkg25 matches 144 unless block 2 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 44 absent"}]
execute if score @s pkg25 matches 45 run setblock 3 90 5 minecraft:glass
execute if score @s pkg25 matches 45 if block 3 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 45 placed"}]
execute if score @s pkg25 matches 145 if block 3 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 45 present"}]
execute if score @s pkg25 matches 145 unless block 3 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 45 absent"}]
execute if score @s pkg25 matches 46 run setblock 4 90 5 minecraft:glass
execute if score @s pkg25 matches 46 if block 4 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 46 placed"}]
execute if score @s pkg25 matches 146 if block 4 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 46 present"}]
execute if score @s pkg25 matches 146 unless block 4 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 46 absent"}]
execute if score @s pkg25 matches 47 run setblock 5 90 5 minecraft:glass
execute if score @s pkg25 matches 47 if block 5 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 47 placed"}]
execute if score @s pkg25 matches 147 if block 5 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 47 present"}]
execute if score @s pkg25 matches 147 unless block 5 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 47 absent"}]
execute if score @s pkg25 matches 48 run setblock 6 90 5 minecraft:glass
execute if score @s pkg25 matches 48 if block 6 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 48 placed"}]
execute if score @s pkg25 matches 148 if block 6 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 48 present"}]
execute if score @s pkg25 matches 148 unless block 6 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 48 absent"}]
execute if score @s pkg25 matches 49 run setblock 7 90 5 minecraft:glass
execute if score @s pkg25 matches 49 if block 7 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 49 placed"}]
execute if score @s pkg25 matches 149 if block 7 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 49 present"}]
execute if score @s pkg25 matches 149 unless block 7 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 49 absent"}]
execute if score @s pkg25 matches 50 run setblock 8 90 5 minecraft:glass
execute if score @s pkg25 matches 50 if block 8 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 50 placed"}]
execute if score @s pkg25 matches 150 if block 8 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 50 present"}]
execute if score @s pkg25 matches 150 unless block 8 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 50 absent"}]
execute if score @s pkg25 matches 51 run setblock 9 90 5 minecraft:glass
execute if score @s pkg25 matches 51 if block 9 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 51 placed"}]
execute if score @s pkg25 matches 151 if block 9 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 51 present"}]
execute if score @s pkg25 matches 151 unless block 9 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 51 absent"}]
execute if score @s pkg25 matches 52 run setblock 10 90 5 minecraft:glass
execute if score @s pkg25 matches 52 if block 10 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 52 placed"}]
execute if score @s pkg25 matches 152 if block 10 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 52 present"}]
execute if score @s pkg25 matches 152 unless block 10 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 52 absent"}]
execute if score @s pkg25 matches 53 run setblock 11 90 5 minecraft:glass
execute if score @s pkg25 matches 53 if block 11 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 53 placed"}]
execute if score @s pkg25 matches 153 if block 11 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 53 present"}]
execute if score @s pkg25 matches 153 unless block 11 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 53 absent"}]
execute if score @s pkg25 matches 54 run setblock 12 90 5 minecraft:glass
execute if score @s pkg25 matches 54 if block 12 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 54 placed"}]
execute if score @s pkg25 matches 154 if block 12 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 54 present"}]
execute if score @s pkg25 matches 154 unless block 12 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 54 absent"}]
execute if score @s pkg25 matches 55 run setblock 13 90 5 minecraft:glass
execute if score @s pkg25 matches 55 if block 13 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 55 placed"}]
execute if score @s pkg25 matches 155 if block 13 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 55 present"}]
execute if score @s pkg25 matches 155 unless block 13 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 55 absent"}]
execute if score @s pkg25 matches 56 run setblock 14 90 5 minecraft:glass
execute if score @s pkg25 matches 56 if block 14 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 56 placed"}]
execute if score @s pkg25 matches 156 if block 14 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 56 present"}]
execute if score @s pkg25 matches 156 unless block 14 90 5 minecraft:glass run tellraw @a [{"text":"pkg25 probe 56 absent"}]
scoreboard players set @s pkg25 0
