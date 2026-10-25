"""Read-only source replay of the tools-USB PLAN-GAP; no VM/hardware operation.

Exit 2 is the expected dispatch STOP. Synthetic device paths are explicitly
source-derived fixtures, not observations of a new QEMU or owner machine.
"""
import hashlib
import json
import pathlib
import struct
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
from disk_audit import AUTO_BOOT_GUID, firmware_hardware, load_option
from firmware_contract import check_source


def main():
    folder = ROOT / 'os/manifest/ci/14/firmware-walk'
    index = json.loads((folder / 'sources.json').read_text())
    raw = (folder / index['archive']).read_bytes()
    assert len(raw) == index['bytes'] and hashlib.sha256(raw).hexdigest() == index['sha256']
    with zipfile.ZipFile(folder / index['archive']) as archive:
        assert len(archive.namelist()) == len(set(archive.namelist())) == len(index['files']) == 4
        files = {row['file']: archive.read(row['file']) for row in index['files']}
        for row in index['files']:
            assert len(files[row['file']]) == row['bytes']
            assert hashlib.sha256(files[row['file']]).hexdigest() == row['sha256']
    retained = json.loads((ROOT / index['pinned_binary_binding']['retained_contract']).read_text())
    assert retained['version'] == '2024.02-2ubuntu0.10'
    assert hashlib.sha256(files['BmBoot.c']).hexdigest() == retained['source_sha256']
    boot = files['BmBoot.c'].decode()
    check_source(boot)
    enum = boot.split('BmEnumerateBootOptions (', 1)[1].split('// Parse simple file system', 1)[0]
    assert 'BlkIo->Media->LogicalPartition' in enum
    assert 'BlkIo->Media->RemovableMedia' in enum and 'BlkIo->Media->MediaPresent' in enum
    assert 'DevicePathFromHandle (Handles[Index])' in enum
    assert 'EfiBootManagerInitializeLoadOption (' in enum
    assert 'SimpleFileSystem' not in enum and 'EFI\\BOOT' not in enum
    refresh = boot.split('EfiBootManagerRefreshAllBootOption (', 1)[1]
    assert 'BmEnumerateBootOptions (&BootOptionCount)' in refresh
    assert 'AllocateCopyPool (sizeof (EFI_GUID), &mBmAutoCreateBootOptionGuid)' in refresh
    assert 'EfiBootManagerAddLoadOptionVariable' in refresh
    header = files['DevicePath.h'].decode()
    assert '#define MSG_USB_DP  0x05' in header
    assert '#define MSG_DEVICE_LOGICAL_UNIT_DP  0x11' in header
    usb = files['UsbEnumer.c'].decode()
    assert 'UsbNode.Header.SubType   = MSG_USB_DP;' in usb
    assert 'UsbNode.ParentPortNumber = Device->ParentPort;' in usb
    assert 'UsbNode.InterfaceNumber  = UsbIf->IfSetting->Desc.InterfaceNumber;' in usb
    assert 'AppendDevicePathNode (HubIf->DevicePath, &UsbNode.Header)' in usb

    # Q35 root + PCI USB controller + USB port/interface + optional LUN + End.
    # The exact future port is immaterial: all USB nodes are currently rejected.
    root = struct.pack('<BBHII', 2, 1, 12, 0x0a0341d0, 0)
    pci = struct.pack('<BBHBB', 1, 1, 6, 0, 5)
    end = b'\x7f\xff\x04\0'
    rejected = []
    for port, interface, lun in ((0, 0, None), (1, 0, None), (2, 1, 0)):
        path = root + pci + struct.pack('<BBHBB', 3, 5, 6, port, interface)
        if lun is not None:
            path += struct.pack('<BBHB', 3, 17, 5, lun)
        path += end
        raw = struct.pack('<IH', 1, len(path)) + 'Synthetic tools USB\0'.encode('utf-16le') + path + AUTO_BOOT_GUID
        option = load_option(raw)
        assert option['optional'] == AUTO_BOOT_GUID
        try:
            firmware_hardware(option)
        except AssertionError as error:
            assert str(error) == 'PLAN-GAP: unsupported firmware device path'
            rejected.append(dict(port=port, interface=interface, lun=lun, result=str(error)))
        else:
            raise AssertionError('Audit unexpectedly accepts a USB path; review the rule before dispatch')
    # Removing the USB node would identify only the controller, which also hosts
    # the keyboard and survives unplugging the stick. That is not a safe mapping.
    assert firmware_hardware(dict(nodes=load_option(raw)['nodes'][:2] + [(127, 255, end)])) == 'pci:00:05.0'
    result = dict(status='STOP-PLAN-GAP', source_integrity='passed', source_files=4,
        pinned_BmBoot_source_matches=True, binary_version=retained['version'],
        usb_auto_entry_expected_from_source=True, actual_new_vm_observation=False,
        fixtures='synthetic source-derived paths; no device accessed', rejected=rejected,
        controller_only_mapping_would_lose_stick_identity=True,
        dispatch_authorized=False, vm_dispatches=0, audit_rule_changed=False)
    print(json.dumps(result, indent=2))
    if sys.argv[1:] == ['--record']:
        (folder / 'verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    else:
        assert not sys.argv[1:]
    return 2


if __name__ == '__main__':
    sys.exit(main())
