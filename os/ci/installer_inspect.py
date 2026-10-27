"""Inspect downloaded ISO bytes; do not infer installer behavior from old docs."""
import hashlib
import http.client
import json
import pathlib
import re
import subprocess
import time
import urllib.error
import urllib.request

WORK = pathlib.Path('.work/installer').resolve()
EVIDENCE = pathlib.Path('evidence/installer').resolve()
ATTEMPTS = 6
BACKOFF = (1, 2, 3, 4, 5)
CHUNK = 8 * 1024 * 1024
CONNECTION_ERRORS = (OSError, urllib.error.URLError, http.client.HTTPException)


def fetch(url, offset=None):
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; AresOS-release-check/1.0)',
               'Accept-Encoding': 'identity'}
    if offset is not None:
        headers['Range'] = f'bytes={offset}-'
    return urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=90)


def validate_download(observed, live):
    assert type(live['bytes']) is int and live['bytes'] > 0, 'Missing pinned ISO size: STOP'
    if observed['bytes'] != live['bytes']:
        raise IOError(f'Incomplete ISO transfer: received {observed["bytes"]} of pinned {live["bytes"]} bytes; this probe must stop')
    assert observed['downloaded_sha256'] == live['sha256'], 'Downloaded ISO differs: STOP'
    assert observed['official_sha256'] == live['sha256'], 'Official checksum changed: STOP'


class DownloadProtocolError(IOError):
    pass


def response_length(response, offset, size, attempt):
    # Duplicate framing headers are ambiguous even if a dict would hide them.
    headers = {}
    for name in ('content-length', 'content-range', 'content-encoding'):
        values = [value for key, value in response.headers.items() if key.lower() == name]
        attempt[name] = values
        if len(values) > 1:
            raise DownloadProtocolError('STOP: duplicate ISO response ' + name)
        headers[name] = values[0].strip(' \t') if values else None
    if headers['content-encoding'] not in (None, 'identity'):
        raise DownloadProtocolError('STOP: encoded ISO response')
    status = response.status
    if status == 200:
        if headers['content-range'] is not None:
            raise DownloadProtocolError('STOP: Content-Range on a 200 response')
        expected = size
    elif status == 206:
        match = re.fullmatch(r'bytes ([0-9]+)-([0-9]+)/([0-9]+)', headers['content-range'] or '', re.IGNORECASE)
        if not match:
            raise DownloadProtocolError('STOP: missing or malformed ISO Content-Range')
        start, end, total = map(int, match.groups())
        if start != offset or total != size or not start <= end < total:
            raise DownloadProtocolError('STOP: ISO Content-Range differs from offset/pinned size')
        expected = end - start + 1
    else:
        raise DownloadProtocolError('STOP: unexpected ISO HTTP status ' + str(status))
    length = headers['content-length']
    if length is not None and (not re.fullmatch('[0-9]+', length) or int(length) != expected):
        raise DownloadProtocolError('STOP: ISO Content-Length differs from response range/pinned size')
    return expected, length is not None


def download_iso(live, official_sha256):
    """Only verified ranges may extend this run's file; never trust an old cache."""
    size = live['bytes']
    assert type(size) is int and size > 0, 'Missing pinned ISO size: STOP'
    disk = WORK / live['filename']
    digest, received = hashlib.sha256(), 0
    observed = dict(sha256=live['sha256'], downloaded_sha256=digest.hexdigest(),
        official_sha256=official_sha256, filename=live['filename'], url=live['url'],
        pinned_bytes=size, bytes=0, max_attempts=ATTEMPTS, attempts=[], status='downloading')

    def checkpoint():
        observed.update(downloaded_sha256=digest.hexdigest(), bytes=received)
        temporary = EVIDENCE / 'iso-download.json.tmp'
        temporary.write_text(json.dumps(observed, indent=2) + '\n')
        temporary.replace(EVIDENCE / 'iso-download.json')

    try:
        assert official_sha256 == live['sha256'], 'Official checksum changed: STOP'
        with disk.open('wb') as output:
            for number in range(1, ATTEMPTS + 1):
                if number > 1:
                    time.sleep(BACKOFF[number - 2])
                offset = received
                attempt = dict(attempt=number, offset=offset, range_requested=number > 1, status=None, bytes=0,
                    stored_bytes=0, received_total=received, restarted=False, outcome='connecting')
                observed['attempts'].append(attempt)
                checkpoint()
                try:
                    try:
                        response = fetch(live['url'], offset if number > 1 else None)
                    except urllib.error.HTTPError as error:
                        attempt['status'] = error.code
                        error.close()
                        raise DownloadProtocolError('STOP: ISO HTTP error ' + str(error.code)) from error
                    except CONNECTION_ERRORS as error:
                        attempt.update(outcome='connection-error', error_type=type(error).__name__)
                        continue
                    with response:
                        attempt['status'] = response.status
                        expected, framed = response_length(response, offset, size, attempt)
                        if response.status == 200 and number > 1:
                            output.seek(0)
                            output.truncate()
                            digest, received = hashlib.sha256(), 0
                            attempt['restarted'] = True
                        attempt.update(applied_offset=received, received_total=received, outcome='reading')
                        checkpoint()
                        while True:
                            error = None
                            try:
                                data = response.read(min(CHUNK, expected - attempt['bytes'] + 1))
                            except http.client.IncompleteRead as failure:
                                data, error = failure.partial, failure
                            except CONNECTION_ERRORS as failure:
                                data, error = b'', failure
                            attempt['bytes'] += len(data)
                            if attempt['bytes'] > expected or received + len(data) > size:
                                raise DownloadProtocolError('STOP: ISO response exceeds its range/pinned size')
                            if data:
                                if output.write(data) != len(data):
                                    raise IOError('STOP: short local ISO file write')
                                digest.update(data)
                                received += len(data)
                                attempt['stored_bytes'] += len(data)
                                attempt['received_total'] = received
                                checkpoint()
                            if error is not None:
                                attempt.update(outcome='connection-error', error_type=type(error).__name__)
                                break
                            if not data or framed and attempt['bytes'] == expected:
                                attempt['outcome'] = 'complete-response' if attempt['bytes'] == expected else 'short-read'
                                break
                    if received == size:
                        checkpoint()
                        validate_download(observed, live)
                        observed['status'] = 'passed'
                        return observed
                except BaseException as error:
                    attempt.update(outcome='stopped', error_type=type(error).__name__)
                    raise
                finally:
                    checkpoint()
        raise IOError(f'STOP: ISO download exhausted {ATTEMPTS} attempts; received {received} of pinned {size} bytes')
    except BaseException as error:
        observed.update(status='stopped', error_type=type(error).__name__)
        raise
    finally:
        checkpoint()


def official_checksum(live):
    with fetch(live['checksum_source']) as response:
        checksum = response.read()
    (EVIDENCE / 'live-CHECKSUM.txt').write_bytes(checksum)
    assert checksum.decode().split() == [live['sha256'], live['filename']], 'Official checksum changed: STOP'
    return checksum.decode().split()[0]


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    live = next(item for item in json.loads(pathlib.Path('os/manifest/installer-isos.json').read_text())
                if item['kind'] == 'live')
    official = official_checksum(live)
    disk = WORK / live['filename']
    observed = download_iso(live, official)
    print(f'Pinned live ISO download verified: {observed["downloaded_sha256"]} ({disk.stat().st_size} bytes)', flush=True)
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
                    localization_sources.append(dict(sha256=hashlib.sha256(raw).hexdigest(),
                        path=path, bytes=len(raw)))
                print(path + '\n' + raw.decode(errors='replace'), flush=True)
            (EVIDENCE / 'localization-source.json').write_text(json.dumps(dict(
                iso_sha256=observed['downloaded_sha256'], sources=localization_sources), indent=2) + '\n')
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
                sources.append(dict(sha256=hashlib.sha256(content.encode()).hexdigest(), path=str(relative)))
            assert sources, 'No application sources in pinned UI source map'
            (EVIDENCE / 'webui-source-map.json').write_text(json.dumps(dict(
                source_map_sha256=hashlib.sha256(raw).hexdigest(), sources=sources), indent=2) + '\n')
            print(f'Extracted {len(sources)} actual pinned Web UI sources for command/selector inspection', flush=True)


if __name__ == '__main__':
    main()
