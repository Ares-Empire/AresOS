"""Inspect downloaded ISO bytes; do not infer installer behavior from old docs."""
import hashlib
import json
import pathlib
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
            (EVIDENCE / 'squashfs-files.txt').write_text(contents)
            print(contents[:3000], flush=True)


if __name__ == '__main__':
    main()
