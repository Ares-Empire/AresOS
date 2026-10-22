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
    assert digest.hexdigest() == live['sha256'], 'Downloaded ISO differs: STOP'
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
                or re.fullmatch(r'usr/libexec/livesys/[^/]+', path)]
            for path in selected:
                raw = subprocess.check_output(['unsquashfs', '-cat', str(squash), path])
                assert len(raw) < 2 * 1024 * 1024
                (EVIDENCE / path.replace('/', '_')).write_bytes(raw)
                print(path + '\n' + raw.decode(errors='replace'), flush=True)


if __name__ == '__main__':
    main()
