"""Offline file-disk and EDK2 audits for the disposable two-disk rehearsal."""
import hashlib
import json
import pathlib
import re
import struct
import subprocess
import uuid
import zlib

AUTH_STORE = uuid.UUID('aaf32c78-947b-439a-a180-2e144ec37792').bytes_le
EFI_GLOBAL = uuid.UUID('8be4df61-93ca-11d2-aa0d-00e098032b8c').bytes_le
AUTO_BOOT_GUID = uuid.UUID('8108ac4e-9f11-4d59-850e-e21a522c59b2').bytes_le


def sha256(path):
    digest = hashlib.sha256()
    with pathlib.Path(path).open('rb') as stream:
        while data := stream.read(8 * 1024 * 1024):
            digest.update(data)
    return digest.hexdigest()


def gpt(path):
    """Validate both headers and tables; retain GUIDs and exact LBA boundaries."""
    with pathlib.Path(path).open('rb') as stream:
        size = stream.seek(0, 2)
        assert size % 512 == 0
        headers = []
        tables = []
        for lba in (1, size // 512 - 1):
            stream.seek(lba * 512)
            raw = stream.read(512)
            assert raw[:8] == b'EFI PART', 'Missing GPT header'
            length, crc = struct.unpack_from('<II', raw, 12)
            assert 92 <= length <= 512
            checked = bytearray(raw[:length])
            checked[16:20] = b'\0' * 4
            assert zlib.crc32(checked) == crc, 'GPT header CRC differs'
            current, other, first, last = struct.unpack_from('<QQQQ', raw, 24)
            assert current == lba and other == (size // 512 - 1 if lba == 1 else 1)
            entries_lba, count, width, entries_crc = struct.unpack_from('<QIII', raw, 72)
            assert width >= 128 and count * width <= 16 * 1024 * 1024
            stream.seek(entries_lba * 512)
            table = stream.read(count * width)
            assert len(table) == count * width and zlib.crc32(table) == entries_crc, 'GPT table CRC differs'
            headers.append(dict(disk_guid=str(uuid.UUID(bytes_le=raw[56:72])), first_usable=first,
                                last_usable=last, count=count, width=width))
            tables.append(table)
        assert headers[0] == headers[1] and tables[0] == tables[1], 'GPT backup differs'
        partitions = []
        for offset in range(0, len(tables[0]), headers[0]['width']):
            entry = tables[0][offset:offset + headers[0]['width']]
            if entry[:16] == bytes(16):
                continue
            start, end, flags = struct.unpack_from('<QQQ', entry, 32)
            assert headers[0]['first_usable'] <= start <= end <= headers[0]['last_usable']
            partitions.append(dict(number=offset // headers[0]['width'] + 1,
                type_guid=str(uuid.UUID(bytes_le=entry[:16])), guid=str(uuid.UUID(bytes_le=entry[16:32])),
                start_lba=start, end_lba=end, bytes=(end - start + 1) * 512, flags=flags,
                name=entry[56:128].decode('utf-16le').rstrip('\0')))
    assert partitions, 'No partitions'
    return dict(bytes=size, **headers[0], partitions=partitions)


def protected_writes(stats):
    candidates = [item for item in stats if item.get('device') == 'protected']
    assert len(candidates) == 1, 'Protected QEMU device missing or ambiguous'
    values = candidates[0]['stats']
    assert values['wr_bytes'] == 0 and values['wr_operations'] == 0, 'PRODUCT FAILURE: protected disk was written'
    return dict(wr_bytes=values['wr_bytes'], wr_operations=values['wr_operations'])


def offline_disk(path, process=None):
    assert process is None or process.poll() is not None, 'Refuse an online disk hash'
    # QEMU has exited; also reject any other process holding the image open.
    check = subprocess.run(['fuser', str(path)], capture_output=True)
    assert check.returncode == 1 and not check.stdout.strip(), 'Disk image still open'
    result = dict(sha256=sha256(path), gpt=gpt(path), offline=True)
    files = efi_files(path, result['gpt'])
    assert any(p.endswith('/microsoft/boot/bootmgfw.efi') for p in files), files
    assert any(p.endswith('/boot/bootx64.efi') for p in files), files
    result['efi_files'] = files
    return result


def efi_files(path, layout):
    esp, = [p for p in layout['partitions'] if p['type_guid'] == 'c12a7328-f81f-11d2-ba4b-00a0c93ec93b']
    location = f'{path}@@{esp["start_lba"] * 512}'
    listing = subprocess.check_output(['mdir', '-i', location, '-a', '-b', '-s', '::/EFI']).decode()
    files = {}
    for name in listing.splitlines():
        if name.endswith('/'):
            continue
        raw = subprocess.check_output(['mtype', '-i', location, name])
        files[name.replace('\\', '/').lower()] = dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
    return files


def compare_disk(before, after):
    assert before == after, 'PRODUCT FAILURE: protected disk hash, GPT or EFI files changed'


def variables(raw):
    """EDK2 AUTHENTICATED_VARIABLE_HEADER; compare live values, not deleted history.

    Layout: tianocore/edk2 MdeModulePkg/Include/Guid/VariableFormat.h.
    Never edits a physical firmware store: callers supply a runner file.
    """
    raw = bytes(raw)
    start = raw.index(AUTH_STORE)
    length = struct.unpack_from('<I', raw, start + 16)[0]
    assert raw[start + 20:start + 22] == b'\x5a\xfe'
    end = start + length
    assert end <= len(raw)
    position = (start + 28 + 3) & ~3
    values = {}
    offsets = {}
    while position + 60 <= end and raw[position:position + 2] == b'\xaa\x55':
        state = raw[position + 2]
        attrs = struct.unpack_from('<I', raw, position + 4)[0]
        namesize, datasize = struct.unpack_from('<II', raw, position + 36)
        guid = raw[position + 44:position + 60]
        assert namesize >= 2 and namesize % 2 == 0 and position + 60 + namesize + datasize <= end
        name = raw[position + 60:position + 60 + namesize].decode('utf-16le').rstrip('\0')
        data = raw[position + 60 + namesize:position + 60 + namesize + datasize]
        key = (guid, name)
        if state in (0x3f, 0x3e):
            if state == 0x3f or key not in values:
                values[key] = dict(attributes=attrs, data=data)
                offsets[key] = position
        position = (position + 60 + namesize + datasize + 3) & ~3
    assert raw[position:position + 2] in (b'\xff\xff', b'\0\0'), 'Unknown variable record'
    return values, offsets, position, end


def set_variable(path, name, data):
    raw = bytearray(pathlib.Path(path).read_bytes())
    values, offsets, position, end = variables(raw)
    key = (EFI_GLOBAL, name)
    if key in offsets:
        raw[offsets[key] + 2] &= 0xfd
    encoded = (name + '\0').encode('utf-16le')
    record = (struct.pack('<HBBIQ', 0x55aa, 0x3f, 0, 7, 0) + bytes(16)
              + struct.pack('<III', 0, len(encoded), len(data)) + EFI_GLOBAL + encoded + data)
    assert position + len(record) <= end, 'OVMF variable store full'
    raw[position:position + len(record)] = record
    pathlib.Path(path).write_bytes(raw)


def boot_entry(partition, label='Windows Boot Manager', filename='\\EFI\\Microsoft\\Boot\\bootmgfw.efi'):
    drive = struct.pack('<BBHIQQ16sBB', 4, 1, 42, partition['number'], partition['start_lba'],
        partition['end_lba'] - partition['start_lba'] + 1, uuid.UUID(partition['guid']).bytes_le, 2, 2)
    file = (filename + '\0').encode('utf-16le')
    path = drive + struct.pack('<BBH', 4, 4, len(file) + 4) + file + b'\x7f\xff\x04\0'
    return struct.pack('<IH', 1, len(path)) + (label + '\0').encode('utf-16le') + path


def load_option(data):
    """Separate the bounded device path from OptionalData, without label heuristics."""
    assert len(data) >= 12, 'Truncated EFI load option'
    _, length = struct.unpack_from('<IH', data)
    position = 6
    while data[position:position + 2] != b'\0\0':
        assert position + 2 < len(data)
        position += 2
    description = data[6:position].decode('utf-16le')
    position += 2
    end = position + length
    assert end <= len(data)
    nodes = []
    while position < end:
        kind, subtype, size = struct.unpack_from('<BBH', data, position)
        assert size >= 4 and position + size <= end
        node = data[position:position + size]
        nodes.append((kind, subtype, node))
        position += size
    assert nodes and nodes[-1][:2] == (0x7f, 0xff) and len(nodes[-1][2]) == 4, 'Missing EFI path terminator'
    assert all(kind != 0x7f for kind, _, _ in nodes[:-1]), 'Unsupported multi-instance EFI path'
    return dict(description=description, nodes=nodes, optional=data[end:])


def firmware_hardware(option):
    """The supported Q35 root PCI path, with an exact SATA port when present."""
    nodes = option['nodes'][:-1]
    assert len(nodes) >= 2, 'PLAN-GAP: firmware option has no supported hardware path'
    kind, subtype, root = nodes[0]
    assert (kind, subtype) == (2, 1) and len(root) == 12, 'PLAN-GAP: unsupported firmware root'
    hid, uid = struct.unpack_from('<II', root, 4)
    assert hid in (0x0a0341d0, 0x0a0841d0) and uid == 0, 'PLAN-GAP: unsupported PCI root'
    kind, subtype, pci = nodes[1]
    assert (kind, subtype) == (1, 1) and len(pci) == 6, 'PLAN-GAP: unsupported firmware PCI node'
    function, slot = pci[4:6]
    key = f'pci:00:{slot:02x}.{function}'
    rest = nodes[2:]
    if rest and rest[0][:2] == (3, 18):
        assert len(rest) == 1 and len(rest[0][2]) == 10, 'PLAN-GAP: unsupported SATA path'
        key += '/sata:' + ':'.join(str(v) for v in struct.unpack_from('<HHH', rest[0][2], 4))
    else:
        assert all(kind == 3 and subtype in (11, 12, 13) for kind, subtype, _ in rest), 'PLAN-GAP: unsupported firmware device path'
    return key


def firmware_baseline(nvram, devices):
    attached = {device['key'] for device in devices['attached']}
    owned = {}
    for name, value in nvram.items():
        if not re.fullmatch(r'Boot[0-9A-F]{4}', name):
            continue
        option = load_option(bytes.fromhex(value['hex']))
        if option['optional'] != AUTO_BOOT_GUID:
            continue
        try:
            device = firmware_hardware(option)
        except AssertionError:
            device = None
        if device is not None:
            assert device in attached, 'PLAN-GAP: baseline automatic option names an unattached device'
        owned[name] = dict(optional_data=option['optional'].hex(), device=device)
    assert owned, 'PLAN-GAP: no baseline EDK2 automatic-option GUID found'
    assert load_option(bytes.fromhex(nvram['Boot0000']['hex']))['optional'] == b'', 'Windows fixture must have no OptionalData'
    return owned


def entry_target(data):
    option = load_option(data)
    partitions = []
    files = []
    for kind, subtype, node in option['nodes']:
        if (kind, subtype) == (4, 1):
            assert len(node) == 42 and node[40:42] == b'\x02\x02', 'Not a GPT hard-drive node'
            number, start, count = struct.unpack_from('<IQQ', node, 4)
            partitions.append(dict(number=number, start_lba=start, sectors=count,
                                   guid=str(uuid.UUID(bytes_le=node[24:40]))))
        elif (kind, subtype) == (4, 4):
            files.append(node[4:].decode('utf-16le').rstrip('\0'))
    assert len(partitions) == 1 and files, 'Missing or ambiguous EFI boot target'
    return dict(description=option['description'], partition=partitions[0], file=''.join(files))


def boot_variables(path):
    values, *_ = variables(pathlib.Path(path).read_bytes())
    return {name: dict(attributes=value['attributes'], hex=value['data'].hex())
            for (guid, name), value in values.items()
            if guid == EFI_GLOBAL and re.fullmatch(r'Boot(?:[0-9A-Fa-f]{4}|Order|Next)', name)}


def all_variables(path):
    values, *_ = variables(pathlib.Path(path).read_bytes())
    return {f'{uuid.UUID(bytes_le=guid)}/{name}': dict(attributes=value['attributes'],
                sha256=hashlib.sha256(value['data']).hexdigest(), bytes=len(value['data']))
            for (guid, name), value in values.items()}


def compare_nvram(before, after, windows='Boot0000', before_devices=None, after_devices=None, target_esp=None):
    assert windows in before and after.get(windows) == before[windows], 'PRODUCT FAILURE: Windows firmware entry lost or changed'
    changes = {name: dict(before=before.get(name), after=after.get(name))
               for name in before.keys() | after.keys() if before.get(name) != after.get(name)}
    for name, change in changes.items():
        if name in ('BootOrder', 'BootNext'):
            continue
        assert re.fullmatch(r'Boot[0-9A-F]{4}', name), 'PLAN-GAP: unknown boot variable change'
        assert change['before'] is None or change['after'] is None, 'PRODUCT FAILURE: existing boot entry changed'
        value = change['before'] or change['after']
        data = bytes.fromhex(value['hex'])
        option = load_option(data)
        if option['optional'] == AUTO_BOOT_GUID:
            assert before_devices is not None and after_devices is not None, 'PLAN-GAP: missing per-boot device evidence'
            device = firmware_hardware(option)
            previous = {item['key'] for item in before_devices['attached']}
            current = {item['key'] for item in after_devices['attached']}
            if change['after'] is None:
                assert device in previous and device not in current, 'PRODUCT FAILURE: auto option removal does not match a detached device'
                reason = 'firmware removed an exact-GUID automatic option for a device detached in this boot'
            else:
                assert device in current, 'PRODUCT FAILURE: auto option addition does not match an attached device'
                reason = 'firmware added an exact-GUID automatic option for an attached device'
            change['firmware_owned'] = dict(device=device, reason=reason, optional_data=option['optional'].hex())
        else:
            assert AUTO_BOOT_GUID not in option['optional'], 'PRODUCT FAILURE: OptionalData contains but is not exactly the automatic-option GUID'
            assert change['before'] is None, 'PRODUCT FAILURE: existing non-firmware boot entry removed'
            assert option['description'].lower() in ('fedora', 'bazzite'), 'Unexpected non-Linux boot entry added'
            assert entry_target(data)['file'].lower() in ('\\efi\\fedora\\shimx64.efi', '\\efi\\fedora\\grubx64.efi'), 'Unexpected Linux loader path'
            if target_esp is not None:
                target = entry_target(data)['partition']
                assert target['guid'] == target_esp['guid'] and target['start_lba'] == target_esp['start_lba'] and target['sectors'] == target_esp['bytes'] // 512, 'PRODUCT FAILURE: new Linux entry does not target the target ESP'
    order = bytes.fromhex(after['BootOrder']['hex'])
    assert bytes.fromhex(windows[4:])[::-1] in [order[i:i + 2] for i in range(0, len(order), 2)], 'Windows entry absent from BootOrder'
    def fixed_order(store):
        raw = bytes.fromhex(store['BootOrder']['hex'])
        assert len(raw) % 2 == 0, 'Malformed BootOrder'
        numbers = list(struct.unpack('<' + 'H' * (len(raw) // 2), raw))
        assert len(numbers) == len(set(numbers)), 'Duplicate BootOrder entries'
        fixed = []
        for number in numbers:
            name = f'Boot{number:04X}'
            assert name in store, 'BootOrder names a missing option'
            if changes.get(name, {}).get('firmware_owned'):
                continue
            option = load_option(bytes.fromhex(store[name]['hex']))
            if option['optional'] != AUTO_BOOT_GUID and option['description'].lower() in ('fedora', 'bazzite'):
                continue
            fixed.append(number)
        return fixed
    assert fixed_order(before) == fixed_order(after), 'PLAN-GAP: BootOrder changed beyond separate Linux or exempted firmware options'
    return changes
