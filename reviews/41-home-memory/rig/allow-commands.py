#!/usr/bin/python3
# DEVELOPMENT AID of package 41 (measurement only): allows commands in a copy of a save, for the rig's spectator flight.
"""usage: allow-commands.py <save folder>

Sets level.dat's allowCommands byte (Data.allowCommands, an NBT byte tag) to 1, as "Allow Cheats" does, so the
singleplayer host may use /gamemode. Only for the rig's base copies in .work/pkg41: the AresOS create flow makes
worlds with commands off, and nothing else in the save changes."""
import gzip, os, sys

path = os.path.join(sys.argv[1], 'level.dat')
data = bytearray(gzip.decompress(open(path, 'rb').read()))
tag = b'\x01' + len(b'allowCommands').to_bytes(2, 'big') + b'allowCommands'
at = data.find(tag)
if at < 0 or data.find(tag, at + 1) >= 0:
    sys.exit(f'{path}: expected exactly one allowCommands byte tag')
value = at + len(tag)
print(f'allowCommands was {data[value]}; now 1')
data[value] = 1
tmp = path + '.pkg41-tmp'
with open(tmp, 'wb') as out:
    out.write(gzip.compress(bytes(data)))
os.replace(tmp, path)
