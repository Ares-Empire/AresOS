"""Actual file inspection with a retained, rehashed ISO and public checksum GET.

Only the download source and bsdtar executable/path spelling are adapted.
No assertion, extractor result, source text or manifest value is substituted.
"""
import contextlib
import importlib.util
import json
import pathlib
import shutil
import subprocess

ROOT = pathlib.Path.cwd()
spec = importlib.util.spec_from_file_location('inspect_iso', ROOT/'os/ci/installer_inspect.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
folder = ROOT/'.work/14/14f-installer-replay'
assert not folder.exists(), 'Preserve an existing replay'
assert shutil.disk_usage(ROOT).free > 25*1024**3
folder.mkdir()
module.WORK = folder/'work'
module.EVIDENCE = folder/'evidence'
live, = [x for x in json.loads((ROOT/'os/manifest/installer-isos.json').read_text()) if x['kind']=='live']
retained = ROOT/'.work/14'/live['filename']
assert retained.is_file()
original_fetch = module.fetch
original_run = subprocess.run
original_output = subprocess.check_output


class Retained:
    def __init__(self):
        self.stream = retained.open('rb')
        self.headers = {'Content-Length': str(retained.stat().st_size)}
        self.url = live['url']
    def read(self, n=-1): return self.stream.read(n)
    def __enter__(self): return self
    def __exit__(self, *args): self.stream.close()


def fetch(url):
    return Retained() if url == live['url'] else original_fetch(url)


def adapted(command):
    if command[0] != 'bsdtar': return command
    args = []
    for arg in command[1:]:
        value = str(arg)
        if value.startswith('/mnt/c/'):
            value = 'C:\\' + value[len('/mnt/c/'):].replace('/', '\\')
        args.append(value)
    return ['/mnt/c/Windows/System32/tar.exe', *args]


module.fetch = fetch
subprocess.run = lambda command, **kwargs: original_run(adapted(command), **kwargs)
subprocess.check_output = lambda command, **kwargs: original_output(adapted(command), **kwargs)
with (folder/'inspection.log').open('w') as log, contextlib.redirect_stdout(log):
    module.main()
observed = json.loads((module.EVIDENCE/'iso-download.json').read_text())
localization = json.loads((module.EVIDENCE/'localization-source.json').read_text())
ui = json.loads((module.EVIDENCE/'webui-source-map.json').read_text())
result = dict(sha256=observed['downloaded_sha256'], path=retained.relative_to(ROOT).as_posix(),
    status='passed', kind='actual installer_inspect.main file replay; no VM',
    bytes=observed['bytes'], official_checksum='fresh public HTTPS GET; exact pinned value',
    iso_source='retained ISO, all bytes rehashed by the actual inspection loop',
    archive_tool='Windows system bsdtar 3.8.9; path spelling adapter only',
    squashfs_tool='/usr/bin/unsquashfs', localization_sources=len(localization['sources']),
    webui_sources=len(ui['sources']), ci_inspector_changed=False)
(folder/'result.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
