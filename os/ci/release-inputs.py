"""Resolve small official release metadata, never download an ISO/image layer."""
import hashlib
import json
import pathlib
import re
import urllib.request

evidence = pathlib.Path('evidence')
evidence.mkdir(exist_ok=True)


def fetch(url, headers=None):
    with urllib.request.urlopen(urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; AresOS-release-check/1.0)', **(headers or {})}), timeout=90) as response:
        return response.read()


name = 'ublue-os/bazzite-nvidia-open'
token = json.loads(fetch(f'https://ghcr.io/token?service=ghcr.io&scope=repository:{name}:pull'))['token']
raw = fetch(f'https://ghcr.io/v2/{name}/manifests/44.20261012.1', {
    'Authorization': f'Bearer {token}',
    'Accept': 'application/vnd.oci.image.index.v1+json, application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json',
})
digest = 'sha256:' + hashlib.sha256(raw).hexdigest()
(evidence / 'base-candidate-manifest.json').write_bytes(raw)
(evidence / 'base-candidate.json').write_text(json.dumps(dict(
    reference=f'ghcr.io/{name}@{digest}', resolved_from=f'ghcr.io/{name}:44.20261012.1',
    version='44.20261012.1', architecture='amd64'), indent=2) + '\n')
print(f'Candidate base: ghcr.io/{name}@{digest}', flush=True)
# The website itself can challenge non-browser clients. Its official Git source
# supplies the same link templates without scraping unrelated site scripts.
source = 'https://raw.githubusercontent.com/ublue-os/bazzite.gg/main/content/themes/betheme-child/script135.js'
content = fetch(source).decode()
assert "https://download.bazzite.gg/" in content
(evidence / 'iso-picker.js').write_text(content)
isos = []
for kind, suffix in [('legacy', ''), ('live', '-live')]:
    filename = f'bazzite-nvidia-open-stable{suffix}-amd64.iso'
    url = f'https://download.bazzite.gg/{filename}'
    checksum = fetch(url + '-CHECKSUM').decode()
    (evidence / f'iso-{kind}-CHECKSUM.txt').write_text(checksum)
    matches = re.findall(r'\b[0-9a-fA-F]{64}\b', checksum)
    assert len(matches) == 1 and filename in checksum, checksum
    isos.append(dict(kind=kind, filename=filename, url=url, sha256=matches[0].lower(),
                     checksum_source=url + '-CHECKSUM', picker_source=source))
(evidence / 'installer-isos.json').write_text(json.dumps(isos, indent=2) + '\n')
print(json.dumps(isos, indent=2), flush=True)
