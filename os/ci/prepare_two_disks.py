"""Create only sparse runner files; never accept a device path from the caller."""
import json
import math
import os
import pathlib
import re
import shutil
import stat
import subprocess
import time

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


def loop_partition_state(loop, number):
    node=pathlib.Path(loop+'p'+str(number))
    sysfs=pathlib.Path('/sys/block')/pathlib.Path(loop).name/node.name
    result=dict(node=str(node),sysfs=str(sysfs),block=False)
    try:
        value=node.lstat()
        result.update(block=stat.S_ISBLK(value.st_mode),rdev=f'{os.major(value.st_rdev)}:{os.minor(value.st_rdev)}')
    except OSError as error:
        result['node_error']=str(error)
    for field in ('start','size','dev'):
        try:
            value=(sysfs/field).read_text(encoding='ascii').strip()
            result[field]=int(value) if field!='dev' else value
        except (OSError,ValueError) as error:
            result[field+'_error']=str(error)
    return result


def wait_loop_partitions(loop, disk, timeout=15):
    """Verify the written GPT, then wait for exactly its kernel partition nodes."""
    assert re.fullmatch(r'/dev/loop[0-9]+',loop), 'STOP: expected an exact loop device'
    assert 0 < timeout <= 15, 'STOP: invalid loop partition wait bound'
    verify_loop(loop,disk)
    layout=gpt(disk)  # validates both GPT headers/tables, in 512-byte sectors
    expected=[dict(number=p['number'],start=p['start_lba'],size=p['end_lba']-p['start_lba']+1)
              for p in layout['partitions']]
    assert expected and len({p['number'] for p in expected})==len(expected), 'STOP: missing or duplicate GPT partitions'
    began=time.monotonic();deadline=began+timeout;retry_at=began+timeout/2
    states=[];commands=[];retried=False

    def command(args):
        remaining=deadline-time.monotonic()
        if remaining<=0:
            raise TimeoutError('loop partition wait deadline expired')
        seconds=max(1,min(5,math.ceil(remaining)))
        if args==['udevadm','settle']:
            args=[*args,'--timeout='+str(seconds)]
        record=dict(command=args)
        commands.append(record)
        result=subprocess.run(args,capture_output=True,text=True,timeout=min(remaining,6))
        record.update(returncode=result.returncode,stdout=result.stdout,stderr=result.stderr)
        if result.returncode:
            raise RuntimeError('loop readiness command failed')

    try:
        command(['udevadm','settle'])
        while True:
            states=[loop_partition_state(loop,p['number']) for p in expected]
            ready=all(s['block'] and s.get('start')==p['start'] and s.get('size')==p['size']
                      and s.get('dev')==s.get('rdev') and s.get('dev') is not None
                      for p,s in zip(expected,states,strict=True))
            if ready:
                proof=dict(status='passed',loop=loop,expected=expected,sysfs=states,commands=commands,partx_retry=retried)
                return proof
            now=time.monotonic()
            if now>=deadline:
                break
            if not retried and now>=retry_at:
                verify_loop(loop,disk)
                retried=True
                command(['partx','--update',loop])
                command(['udevadm','settle'])
            else:
                time.sleep(min(0.25,deadline-now))
    except (OSError,RuntimeError,AssertionError,subprocess.SubprocessError) as error:
        commands.append(dict(error=type(error).__name__+': '+str(error)))
    # Diagnostics read only this loop, never the global udev database.
    states=[loop_partition_state(loop,p['number']) for p in expected]
    try:
        info=subprocess.run(['udevadm','info','--query=all','--path=/sys/block/'+pathlib.Path(loop).name],
                            capture_output=True,text=True,timeout=2)
        udev=dict(returncode=info.returncode,stdout=info.stdout,stderr=info.stderr)
    except (OSError,subprocess.TimeoutExpired) as error:
        udev=dict(error=type(error).__name__+': '+str(error))
    raise AssertionError('STOP: loop partition nodes did not match written GPT: '+json.dumps(
        dict(loop=loop,expected=expected,sysfs=states,udev=udev,commands=commands,partx_retry=retried)))


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
        wait_loop_partitions(loop,disk)
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
