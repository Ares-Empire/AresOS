#!/usr/bin/python3
# DEVELOPMENT AID of package 49 (copied from package 41) (measurement only): readies a copy of a save for the rig's glide flight (FLIGHT=glide).
"""usage: prepare-glide.py <save folder>

Installs the rig's glide data pack (rig/glide, as <save>/datapacks/pkg41-glide) and sets level.dat's allowCommands
byte (Data.allowCommands, an NBT byte tag) to 1, as "Allow Cheats" does, so the singleplayer host may run
/function glide. Only for the rig's base copies in .work/pkg49: the AresOS create flow makes worlds with commands
off. Nothing else in the save changes."""
import gzip, os, shutil, sys

pack = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'glide')
target = os.path.join(sys.argv[1], 'datapacks', 'pkg41-glide')
shutil.rmtree(target, ignore_errors=True)
shutil.copytree(pack, target)
print(f'installed {target}')

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
