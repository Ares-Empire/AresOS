#!/usr/bin/python3
"""Package 311e: the SHA-256 of the bytes the loader maps from an x86-64 ELF file.

  loaded_image.py <path>    prints the hash, or stops with one line on stderr and exit 1 if the file is refused

The loaded image is the file from offset 0 to the end of its last segment, exactly as it is on disk, with two ranges
set to zero because they differ between builds of the same code: e_shoff and the descriptor of the GNU build-id note.
Bytes between segments stay in: they are mapped with the page they share.

Only program headers are read. The loader never uses section headers, so a file can say anything in them. Bytes after
the last segment (.gnu_debuglink, .gnu_debugdata, the section headers) are not in the hash: the loader never reads them.
"""
import hashlib
import pathlib
import struct
import sys

ELF_HEADER_SIZE = 64
PROGRAM_HEADER_SIZE = 56
ELFCLASS64, ELFDATA2LSB, EM_X86_64 = 2, 1, 62
E_SHOFF, E_SHOFF_SIZE = 0x28, 8
# 0xffff means the real count is kept in a section header, which this file never reads.
MAX_PROGRAM_HEADERS = 0xfffe
PT_NOTE = 4
NOTE_HEADER = struct.Struct('<III')
NOTE_ALIGNMENTS = (4, 8)
NT_GNU_BUILD_ID = 3
GNU_NOTE_NAME = b'GNU\0'


class LoadedImageRefused(Exception):
    """This file is not one whose loaded image can be pinned."""


def align_up(value, alignment):
    return (value + alignment - 1) & -alignment


def program_headers(data):
    """Each header as (type, offset, file size, alignment), once the ELF header and the table are known to be sound."""
    if len(data) < ELF_HEADER_SIZE or data[:4] != b'\x7fELF':
        raise LoadedImageRefused('it is not an ELF file')
    if data[4] != ELFCLASS64:
        raise LoadedImageRefused('it is not ELF64')
    if data[5] != ELFDATA2LSB:
        raise LoadedImageRefused('it is not little-endian')
    machine = struct.unpack_from('<H', data, 0x12)[0]
    if machine != EM_X86_64:
        raise LoadedImageRefused(f'its machine is {machine}, not x86-64')
    table = struct.unpack_from('<Q', data, 0x20)[0]
    entry_size, count = struct.unpack_from('<HH', data, 0x36)
    if entry_size != PROGRAM_HEADER_SIZE:
        raise LoadedImageRefused(f'e_phentsize is {entry_size}, not {PROGRAM_HEADER_SIZE}')
    if not 1 <= count <= MAX_PROGRAM_HEADERS:
        raise LoadedImageRefused(f'e_phnum is {count}')
    table_end = table + count * PROGRAM_HEADER_SIZE
    if table_end > len(data):
        raise LoadedImageRefused('the program header table lies outside the file')
    headers = []
    for index in range(count):
        kind, _, offset, _, _, file_size, _, alignment = struct.unpack_from(
            '<IIQQQQQQ', data, table + index * PROGRAM_HEADER_SIZE)
        if offset + file_size > len(data):
            raise LoadedImageRefused(f'program header {index} lies outside the file')
        headers.append((kind, offset, file_size, alignment))
    end = max(offset + file_size for _, offset, file_size, _ in headers)
    if ELF_HEADER_SIZE > end or table_end > end:
        raise LoadedImageRefused('the ELF header or the program header table lies outside the loaded image')
    return headers, end


def build_id_descriptors(data, start, size, alignment):
    """The (offset, size) of every GNU build-id descriptor in one PT_NOTE segment."""
    if alignment not in NOTE_ALIGNMENTS:
        raise LoadedImageRefused(f'a PT_NOTE segment has alignment {alignment}')
    found = []
    position = 0
    while position < size:
        if size - position < NOTE_HEADER.size:
            raise LoadedImageRefused('a note overruns its segment')
        name_size, descriptor_size, kind = NOTE_HEADER.unpack_from(data, start + position)
        name = position + NOTE_HEADER.size
        descriptor = align_up(name + name_size, alignment)
        if name + name_size > size or descriptor + descriptor_size > size:
            raise LoadedImageRefused('a note overruns its segment')
        if kind == NT_GNU_BUILD_ID and data[start + name:start + name + name_size] == GNU_NOTE_NAME:
            found.append((start + descriptor, descriptor_size))
        position = align_up(descriptor + descriptor_size, alignment)
    return found


def loaded_sha256(path):
    """The SHA-256 of this file's loaded image. Raises LoadedImageRefused for a file it cannot vouch for."""
    try:
        data = pathlib.Path(path).read_bytes()
    except OSError as error:
        raise LoadedImageRefused(f'it cannot be read: {error}') from error
    headers, end = program_headers(data)
    descriptors = [descriptor for kind, offset, file_size, alignment in headers if kind == PT_NOTE
                   for descriptor in build_id_descriptors(data, offset, file_size, alignment)]
    if len(descriptors) != 1:
        raise LoadedImageRefused(f'it holds {len(descriptors)} GNU build-id notes, not exactly one')
    image = bytearray(data[:end])
    image[E_SHOFF:E_SHOFF + E_SHOFF_SIZE] = bytes(E_SHOFF_SIZE)
    offset, size = descriptors[0]
    image[offset:offset + size] = bytes(size)
    return hashlib.sha256(image).hexdigest()


def main(argv):
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        print(loaded_sha256(argv[1]))
    except LoadedImageRefused as refusal:
        print(f'LOADED_IMAGE_REFUSED {argv[1]}: {refusal}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
