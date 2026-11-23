#!/usr/bin/python3
# DEVELOPMENT AID of package 25 (the real-game check).
"""usage: region.py <world folder> <x> <y> <z>

Says which block a saved world holds at one place, read from its region file on the disk and nothing else: what a
game that opens the world would find there. Only reads. `None` means the chunk is not in any region file."""
import gzip
import pathlib
import struct
import sys
import zlib

SIMPLE = {1: '>b', 2: '>h', 3: '>i', 4: '>q', 5: '>f', 6: '>d'}


class Reader:
    """Just enough of NBT (big-endian, uncompressed) for a chunk."""

    def __init__(self, data):
        self.data, self.at = data, 0

    def take(self, form):
        (value,) = struct.unpack_from(form, self.data, self.at)
        self.at += struct.calcsize(form)
        return value

    def text(self):
        size = self.take('>H')
        value = self.data[self.at:self.at + size].decode('utf-8', 'replace')
        self.at += size
        return value

    def many(self, letter, width):
        count = self.take('>i')
        values = struct.unpack_from(f'>{count}{letter}', self.data, self.at)
        self.at += count * width
        return list(values)

    def payload(self, tag):
        if tag in SIMPLE:
            return self.take(SIMPLE[tag])
        if tag == 7:
            return self.many('b', 1)
        if tag == 8:
            return self.text()
        if tag == 9:
            kind, count = self.take('>b'), self.take('>i')
            return [self.payload(kind) for _ in range(count)]
        if tag == 10:
            found = {}
            while True:
                kind = self.take('>b')
                if kind == 0:
                    return found
                name = self.text()
                found[name] = self.payload(kind)
        if tag == 11:
            return self.many('i', 4)
        if tag == 12:
            return self.many('q', 8)
        raise ValueError(f'unknown NBT tag {tag}')


def parse(data):
    reader = Reader(data)
    tag = reader.take('>b')
    reader.text()
    return reader.payload(tag)


def region_folders(world):
    """The Overworld's region folder: at the world's top, or under dimensions/ where the game keeps it there."""
    world = pathlib.Path(world)
    return [folder for folder in (world / 'region', world / 'dimensions/minecraft/overworld/region')
            if folder.is_dir()]


def chunk(world, cx, cz):
    for folder in region_folders(world):
        path = folder / f'r.{cx >> 5}.{cz >> 5}.mca'
        if not path.is_file():
            continue
        with open(path, 'rb') as source:
            source.seek(4 * ((cx & 31) + (cz & 31) * 32))
            entry = source.read(4)
            offset = int.from_bytes(entry[:3], 'big')
            if len(entry) < 4 or offset == 0:
                continue
            source.seek(offset * 4096)
            length, kind = struct.unpack('>IB', source.read(5))
            raw = source.read(length - 1)
        if kind == 1:
            return parse(gzip.decompress(raw))
        if kind == 2:
            return parse(zlib.decompress(raw))
        if kind == 3:
            return parse(raw)
        raise ValueError(f'chunk compression {kind} is not read by this rig')
    return None


def block(world, x, y, z):
    """The block's name at (x, y, z) of the Overworld as saved, or None when its chunk is not on the disk."""
    data = chunk(world, x >> 4, z >> 4)
    if data is None:
        return None
    for section in data.get('sections', []):
        if section.get('Y') != y >> 4:
            continue
        states = section.get('block_states')
        if not states:
            return 'minecraft:air'
        palette, longs = states['palette'], states.get('data')
        if not longs:
            return palette[0]['Name']
        # Since 1.16 an entry never spans two longs: each long holds 64 // bits entries, lowest bits first.
        bits = max(4, (len(palette) - 1).bit_length())
        index = ((y & 15) << 8) | ((z & 15) << 4) | (x & 15)
        word = longs[index // (64 // bits)] & 0xFFFFFFFFFFFFFFFF
        return palette[(word >> (bits * (index % (64 // bits)))) & ((1 << bits) - 1)]['Name']
    return 'minecraft:air'


if __name__ == '__main__':
    print(block(sys.argv[1], *(int(value) for value in sys.argv[2:5])))
