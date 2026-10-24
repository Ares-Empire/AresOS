"""Bind the automatic-option predicate to the installed Ubuntu OVMF source."""
import json
import pathlib
import re
import subprocess
import sys
import uuid

from disk_audit import sha256


def check_source(text):
    definition = re.search(r'EFI_GUID\s+mBmAutoCreateBootOptionGuid\s*=\s*\{(.*?)\};', text, re.S)
    assert definition, 'PLAN-GAP: automatic-option GUID definition missing'
    values = [int(n, 16) for n in re.findall(r'0x[0-9a-fA-F]+', definition[1])]
    assert values == [0x8108ac4e, 0x9f11, 0x4d59, 0x85, 0x0e, 0xe2, 0x1a, 0x52, 0x2c, 0x59, 0xb2]
    function = re.search(r'BmIsAutoCreateBootOption\s*\([^)]*\)\s*\{(.*?)\n\}', text, re.S)
    assert function, 'PLAN-GAP: automatic-option predicate missing'
    compact = re.sub(r'\s+', '', function[1])
    assert 'BootOption->OptionalDataSize==sizeof(EFI_GUID)' in compact
    assert 'CompareGuid((EFI_GUID*)BootOption->OptionalData,&mBmAutoCreateBootOptionGuid)' in compact
    return definition[0] + '\n' + function[0]


def main():
    directory = pathlib.Path(sys.argv[1])
    installed = subprocess.check_output(['dpkg-query', '-W', '-f=${Version}\t${source:Package}\t${source:Version}', 'ovmf']).decode().split('\t')
    expected = json.loads(pathlib.Path('os/ci/toolchain.json').read_text())['packages']['ovmf']
    assert installed == [expected, 'edk2', expected], 'OVMF source/binary package version mismatch'
    source, = directory.glob('edk2-*/MdeModulePkg/Library/UefiBootManagerLib/BmBoot.c')
    excerpt = check_source(source.read_text())
    evidence = pathlib.Path('evidence')
    (evidence / 'firmware-contract-source.txt').write_text(excerpt + '\n')
    result = dict(guid=str(uuid.UUID('8108ac4e-9f11-4d59-850e-e21a522c59b2')), optional_data_bytes=16,
        binary_package='ovmf', source_package='edk2', version=expected,
        source_origin='signed Ubuntu snapshot indexes used by install-tools.sh',
        source_file=str(source.relative_to(directory)), source_sha256=sha256(source),
        source_descriptors={p.name: sha256(p) for p in directory.glob('*.dsc')},
        firmware_sha256=sha256('/usr/share/OVMF/OVMF_CODE_4M.fd'))
    assert len(result['source_descriptors']) == 1
    (evidence / 'firmware-contract.json').write_text(json.dumps(result, indent=2) + '\n')
    print('OVMF exact 16-byte auto-option GUID predicate verified against installed package source')


if __name__ == '__main__':
    main()
