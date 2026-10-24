"""Create only sparse runner files; never accept a device path from the caller."""
import json
import pathlib
import shutil
import subprocess

from disk_audit import boot_entry, gpt, set_variable

WORK = pathlib.Path('.work/installer').resolve()


def run(*args):
    subprocess.run(args, check=True)


def verify_loop(loop, disk):
    # --json changes list output only; without --list losetup can return the
    # legacy/non-list representation. Require the actual backing file before
    # allowing any filesystem tool to open the disposable loop device.
    observed = json.loads(subprocess.check_output([
        'losetup', '--list', '--json', '--output', 'NAME,BACK-FILE', loop]))['loopdevices']
    assert len(observed) == 1 and observed[0]['name'] == loop
    assert pathlib.Path(observed[0]['back-file']).resolve() == disk.resolve(), 'Unexpected loop backing file'


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    assert (pathlib.Path.cwd() / 'AGENTS.md').is_file()
    marker = WORK / 'marker'
    run('gcc', '-I/usr/include/efi', '-I/usr/include/efi/x86_64', '-fpic', '-ffreestanding',
        '-fno-stack-protector', '-fno-stack-check', '-fshort-wchar', '-mno-red-zone',
        '-maccumulate-outgoing-args', '-DEFI_FUNCTION_WRAPPER', '-c', 'os/ci/windows_marker.c', '-o', str(marker) + '.o')
    run('ld', '-nostdlib', '-znocombreloc', '-T', '/usr/lib/elf_x86_64_efi.lds', '-shared',
        '-Bsymbolic', '/usr/lib/crt0-efi-x86_64.o', str(marker) + '.o', '-L/usr/lib', '-lefi', '-lgnuefi', '-o', str(marker) + '.so')
    run('objcopy', '-j', '.text', '-j', '.sdata', '-j', '.data', '-j', '.dynamic', '-j', '.dynsym',
        '-j', '.rel', '-j', '.rela', '-j', '.reloc', '--target=efi-app-x86_64', str(marker) + '.so', str(marker) + '.efi')
    disk = WORK / 'protected.raw'
    assert not disk.exists(), 'Never overwrite an existing rehearsal'
    with disk.open('xb') as output:
        output.truncate(50 * 1024 ** 3)
    run('sgdisk', '--clear', '--new=1:2048:+260M', '--typecode=1:ef00', '--change-name=1:Windows ESP',
        '--new=2:0:+16M', '--typecode=2:0c01', '--change-name=2:Microsoft reserved',
        '--new=3:0:-1024M', '--typecode=3:0700', '--change-name=3:Windows data',
        '--new=4:0:0', '--typecode=4:2700', '--change-name=4:Windows recovery', str(disk))
    layout = gpt(disk)
    # The loop device exists only on the disposable hosted runner, and its
    # backing file is this newly created worktree file. Never supplied by users.
    loop = subprocess.check_output(['losetup', '--find', '--show', '--partscan', str(disk)]).decode().strip()
    try:
        verify_loop(loop, disk)
        run('mkfs.vfat', '-F', '32', '-n', 'WIN_ESP', loop + 'p1')
        run('mmd', '-i', loop + 'p1', '::/EFI', '::/EFI/Microsoft', '::/EFI/Microsoft/Boot', '::/EFI/Boot')
        for dest in ('::/EFI/Microsoft/Boot/bootmgfw.efi', '::/EFI/Boot/bootx64.efi'):
            run('mcopy', '-i', loop + 'p1', str(marker) + '.efi', dest)
        for number, label in ((3, 'WINDOWS_KEEP'), (4, 'RECOVERY_KEEP')):
            run('mkntfs', '-F', '-Q', '-L', label, loop + f'p{number}')
            sentinel = WORK / f'sentinel-{number}.txt'
            sentinel.write_text(f'Protected Windows-like partition {number}: must never change.\n')
            run('ntfscp', loop + f'p{number}', str(sentinel), '/KEEP-UNCHANGED.txt')
    finally:
        run('losetup', '--detach', loop)
    with (WORK / 'target.raw').open('xb') as output:
        output.truncate(49 * 1024 ** 3)
    variables = WORK / 'vars.fd'
    shutil.copyfile('/usr/share/OVMF/OVMF_VARS_4M.fd', variables)
    set_variable(variables, 'Boot0000', boot_entry(layout['partitions'][0]))
    set_variable(variables, 'BootOrder', bytes(2))
    print('Created 50 GiB protected GPT/ESP/MSR/NTFS/recovery disk and empty 49 GiB target; file backing verified')


if __name__ == '__main__':
    main()
