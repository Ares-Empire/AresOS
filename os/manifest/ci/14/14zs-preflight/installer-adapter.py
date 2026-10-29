"""Actual inspector replay with native Windows file IO; Linux extraction via WSL.

No CI assertion is patched. Cached ISO transport and platform command/path/
newline spellings are the only adapters. Every actual input byte is rehashed.
"""
import contextlib
import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys,re

ROOT = pathlib.Path.cwd()
spec = importlib.util.spec_from_file_location('inspect_iso', ROOT/'os/ci/installer_inspect.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert re.fullmatch(r'14zs-replay-[1-4]',sys.argv[1])
folder = ROOT/'.work/14'/sys.argv[1]
assert not folder.exists(), 'Preserve existing replay'
assert shutil.disk_usage(ROOT).free > 25*1024**3
folder.mkdir()
module.WORK, module.EVIDENCE = folder/'work', folder/'evidence'
live, = [x for x in json.loads((ROOT/'os/manifest/installer-isos.json').read_text()) if x['kind']=='live']
retained = ROOT/'.work/14'/live['filename']
original_fetch = module.fetch
original_run, original_output = subprocess.run, subprocess.check_output
original_write = pathlib.Path.write_text


class Retained:
    def __init__(self, offset=None):
        self.status = 206 if offset is not None else 200
        self.stream = retained.open('rb')
        size = retained.stat().st_size
        self.stream.seek(offset or 0)
        self.headers = {'Content-Length': str(size-(offset or 0))}
        if offset is not None:self.headers['Content-Range']=f'bytes {offset}-{size-1}/{size}'
        self.url = live['url']
    def read(self, n=-1): return self.stream.read(n)
    def __enter__(self): return self
    def __exit__(self, *args): self.stream.close()


def adapted(command):
    if command[0] == 'bsdtar': return ['C:/Windows/System32/tar.exe', *command[1:]]
    if command[0] != 'unsquashfs': return command
    args = []
    for arg in command[1:]:
        value = str(arg)
        if len(value)>2 and value[1:3] in (':\\', ':/'):
            value = '/mnt/'+value[0].lower()+'/'+value[3:].replace('\\','/')
        args.append(value)
    return ['wsl.exe', '--exec', '/usr/bin/unsquashfs', *args]


def write(path, data, *args, **kwargs):
    kwargs.setdefault('encoding', 'utf-8')
    kwargs.setdefault('newline', '\n')
    return original_write(path, data, *args, **kwargs)


module.fetch = lambda url, offset=None: Retained(offset) if url == live['url'] else original_fetch(url, offset)
subprocess.run = lambda command, **kwargs: original_run(adapted(command), **kwargs)
subprocess.check_output = lambda command, **kwargs: original_output(adapted(command), **kwargs)
pathlib.Path.write_text = write
with (folder/'inspection.log').open('w', encoding='utf-8', newline='\n') as log, contextlib.redirect_stdout(log):
    module.main()
observed = json.loads((module.EVIDENCE/'iso-download.json').read_text())
localization = json.loads((module.EVIDENCE/'localization-source.json').read_text())
ui = json.loads((module.EVIDENCE/'webui-source-map.json').read_text())
result = dict(sha256=observed['downloaded_sha256'], path=retained.relative_to(ROOT).as_posix(),
    status='passed', kind='actual installer_inspect.main replay before14zs probe26/qualification15; local inspector replay only',
    bytes=observed['bytes'], official_checksum='fresh public HTTPS GET; exact pin',
    iso_source='all retained ISO bytes rehashed by actual inspection loop',
    adapters='Windows system bsdtar, WSL unsquashfs, path spellings and Linux LF writes',
    localization_sources=len(localization['sources']), webui_sources=len(ui['sources']),
    ci_inspector_changed=False, download_attempts=observed['attempts'], length_pin=live['bytes'])
(folder/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
