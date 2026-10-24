"""Inspect downloaded ISO bytes; do not infer installer behavior from old docs."""
import hashlib
import json
import pathlib
import re
import subprocess
import urllib.request

WORK = pathlib.Path('.work/installer').resolve()
EVIDENCE = pathlib.Path('evidence/installer').resolve()


def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; AresOS-release-check/1.0)'}), timeout=90)


def validate_download(observed, live):
    length = next((value for key, value in observed['headers'].items() if key.lower() == 'content-length'), None)
    if length is not None and observed['bytes'] != int(length):
        raise IOError(f'Incomplete ISO transfer: received {observed["bytes"]} of advertised {length} bytes; this probe must stop')
    assert observed['downloaded_sha256'] == live['sha256'], 'Downloaded ISO differs: STOP'


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    live = next(item for item in json.loads(pathlib.Path('os/manifest/installer-isos.json').read_text())
                if item['kind'] == 'live')
    with fetch(live['checksum_source']) as response:
        checksum = response.read()
    (EVIDENCE / 'live-CHECKSUM.txt').write_bytes(checksum)
    assert checksum.decode().split() == [live['sha256'], live['filename']], 'Official checksum changed: STOP'
    disk = WORK / live['filename']
    digest = hashlib.sha256()
    with fetch(live['url']) as response, disk.open('wb') as output:
        headers = dict(response.headers)
        resolved = response.url
        while data := response.read(8 * 1024 * 1024):
            digest.update(data)
            output.write(data)
    observed = dict(live, downloaded_sha256=digest.hexdigest(), bytes=disk.stat().st_size,
                    resolved_url=resolved, headers=headers)
    (EVIDENCE / 'iso-download.json').write_text(json.dumps(observed, indent=2) + '\n')
    validate_download(observed, live)
    print(f'Pinned live ISO download verified: {digest.hexdigest()} ({disk.stat().st_size} bytes)', flush=True)
    listing = subprocess.check_output(['bsdtar', '-tf', str(disk)]).decode()
    (EVIDENCE / 'iso-files.txt').write_text(listing)
    print(listing, flush=True)
    for name in listing.splitlines():
        if name.endswith(('grub.cfg', 'isolinux.cfg', '.ks', '.treeinfo', '.discinfo')):
            raw = subprocess.check_output(['bsdtar', '-xOf', str(disk), name])
            (EVIDENCE / name.replace('/', '_')).write_bytes(raw)
            print(name + '\n' + raw.decode(errors='replace'), flush=True)
    for name in listing.splitlines():
        if name.endswith('squashfs.img'):
            squash = WORK / 'squashfs.img'
            with squash.open('wb') as output:
                subprocess.run(['bsdtar', '-xOf', str(disk), name], stdout=output, check=True)
            contents = subprocess.check_output(['unsquashfs', '-ll', str(squash)]).decode()
            retained = '\n'.join(line for line in contents.splitlines()
                if 'squashfs-root/var/lib/flatpak/' not in line
                and 'squashfs-root/var/lib/containers/storage/overlay/' not in line) + '\n'
            (EVIDENCE / 'squashfs-files.txt').write_text(retained)
            (EVIDENCE / 'squashfs-listing.json').write_text(json.dumps(dict(
                full_listing_sha256=hashlib.sha256(contents.encode()).hexdigest(),
                full_listing_lines=len(contents.splitlines()),
                omitted='Flatpak runtime and container layer file lists; original ISO hash retained'), indent=2) + '\n')
            print(contents[:3000], flush=True)
            paths = [line.split()[-1].removeprefix('squashfs-root/') for line in retained.splitlines()
                     if 'squashfs-root/' in line and not line.startswith(('d', 'l'))]
            selected = [path for path in paths if path in (
                'usr/lib/os-release', 'usr/bin/liveinst', 'etc/sysconfig/livesys',
                'usr/libexec/anaconda/webui-desktop',
                'usr/libexec/anaconda/cockpit-coproc-wrapper.sh',
                'usr/lib/systemd/system/webui-cockpit-ws.service',
                'usr/share/cockpit/anaconda-webui/manifest.json',
                'etc/anaconda/profile.d/bazzite.conf', 'etc/anaconda/conf.d/anaconda.conf',
                'usr/share/anaconda/interactive-defaults.ks',
                'usr/share/anaconda/post-scripts/install-configure-upgrade.ks',
                'usr/share/anaconda/post-scripts/secureboot-enroll-key.ks',
                'usr/share/anaconda/post-scripts/secureboot-docs.ks',
                'var/lib/containers/storage/overlay-images/images.json')
                or re.fullmatch(r'usr/libexec/livesys/[^/]+', path)
                or re.fullmatch(r'usr/lib64/python3\.[0-9]+/site-packages/pyanaconda/modules/localization/'
                                r'(localed|utils|installation|localization_interface)\.py', path)]
            localization = [path for path in selected if '/pyanaconda/modules/localization/' in path]
            assert {path.rsplit('/', 1)[1] for path in localization} == {
                'localed.py', 'utils.py', 'installation.py', 'localization_interface.py'}, 'Pinned localization source unavailable: STOP'
            localization_sources = []
            for path in selected:
                raw = subprocess.check_output(['unsquashfs', '-cat', str(squash), path])
                assert len(raw) < 2 * 1024 * 1024
                (EVIDENCE / path.replace('/', '_')).write_bytes(raw)
                if path in localization:
                    localization_sources.append(dict(path=path, bytes=len(raw),
                        sha256=hashlib.sha256(raw).hexdigest()))
                print(path + '\n' + raw.decode(errors='replace'), flush=True)
            (EVIDENCE / 'localization-source.json').write_text(json.dumps(dict(
                iso_sha256=digest.hexdigest(), sources=localization_sources), indent=2) + '\n')
            map_path = 'usr/share/cockpit/anaconda-webui/index.js.map'
            assert map_path in paths, 'Pinned UI source map unavailable; do not guess its version'
            raw = subprocess.check_output(['unsquashfs', '-cat', str(squash), map_path])
            source_map = json.loads(raw)
            source_directory = EVIDENCE / 'webui-source'
            source_directory.mkdir()
            sources = []
            for name, content in zip(source_map['sources'], source_map['sourcesContent']):
                if '/src/' not in name or '/node_modules/' in name or content is None:
                    continue
                relative = pathlib.PurePosixPath(name.split('/src/', 1)[1])
                assert not relative.is_absolute() and '..' not in relative.parts
                destination = source_directory.joinpath(*relative.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_text(content)
                sources.append(dict(path=str(relative), sha256=hashlib.sha256(content.encode()).hexdigest()))
            assert sources, 'No application sources in pinned UI source map'
            (EVIDENCE / 'webui-source-map.json').write_text(json.dumps(dict(
                source_map_sha256=hashlib.sha256(raw).hexdigest(), sources=sources), indent=2) + '\n')
            print(f'Extracted {len(sources)} actual pinned Web UI sources for command/selector inspection', flush=True)


if __name__ == '__main__':
    main()
