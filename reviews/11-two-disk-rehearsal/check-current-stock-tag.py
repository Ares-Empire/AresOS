"""Read public manifest metadata only; never pull layers or use owner credentials."""
import datetime
import hashlib
import json
import pathlib
import urllib.request


def main():
    repository = 'ublue-os/bazzite-nvidia-open'
    request = urllib.request.Request('https://ghcr.io/token?scope=repository:' + repository + ':pull',
                                     headers={'User-Agent': 'AresOS-installer-preflight'})
    with urllib.request.urlopen(request, timeout=45) as response:
        anonymous = json.load(response)['token']
    request = urllib.request.Request('https://ghcr.io/v2/' + repository + '/manifests/stable', headers={
        'Authorization': 'Bearer ' + anonymous,
        'Accept': 'application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json',
        'User-Agent': 'AresOS-installer-preflight'})
    with urllib.request.urlopen(request, timeout=45) as response:
        raw = response.read()
        digest = response.headers.get('Docker-Content-Digest')
    assert digest == 'sha256:' + hashlib.sha256(raw).hexdigest()
    manifest = json.loads(raw)
    amd64 = [item['digest'] for item in manifest.get('manifests', [])
             if item.get('platform', {}).get('os') == 'linux' and item['platform'].get('architecture') == 'amd64']
    expected = json.loads(pathlib.Path('os/manifest/base.json').read_text())['reference'].split('@')[1]
    result = dict(checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  reference='ghcr.io/' + repository + ':stable', root_digest=digest,
                  amd64_manifest_digests=amd64, expected=expected,
                  matches=(expected in [digest, *amd64]), anonymous_metadata_only=True)
    destination = pathlib.Path('os/manifest/ci/11b')
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'current-stock-tag-manifest.json').write_bytes(raw)
    (destination / 'current-stock-tag.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    assert result['matches'], 'STOP: installer post-script would select stock outside the qualified digest'


if __name__ == '__main__':
    main()
