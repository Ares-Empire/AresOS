#!/usr/bin/python3
"""Records what the pinned mod builder image really has on its PATH (package 23).

The Containerfile's `mod` stage runs `build.sh mod` and Gradle in the digest-pinned JDK image
(minecraft/desktop.lock.json, "builder"). That image is minimal: no curl, no wget. This reads the image straight
from its registry (the manifest by digest, then every layer, whiteouts applied) and writes
minecraft/builder-tools.txt: its PATH and JAVA_HOME, and every executable in its PATH folders. The tests run the
mod stage's script with exactly those tools, so a step that needs something the image lacks fails in the tests,
not in an image build.

    python3 os/ci/builder-tools.py            write os/minecraft/builder-tools.txt
    python3 os/ci/builder-tools.py --check    exit 1 if the committed list differs from the image
"""
import hashlib
import io
import json
import pathlib
import posixpath
import sys
import tarfile
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
LOCK = ROOT / 'os/minecraft/desktop.lock.json'
OUTPUT = ROOT / 'os/minecraft/builder-tools.txt'
ACCEPT = ', '.join(('application/vnd.oci.image.index.v1+json',
                    'application/vnd.docker.distribution.manifest.list.v2+json',
                    'application/vnd.oci.image.manifest.v1+json',
                    'application/vnd.docker.distribution.manifest.v2+json'))


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def get(url, headers, follow=True):
    """GET with the registry token; a blob redirect (to a CDN) is followed without the token."""
    opener = urllib.request.build_opener(NoRedirect)
    try:
        return opener.open(urllib.request.Request(url, headers=headers), timeout=120)
    except urllib.error.HTTPError as error:
        if follow and error.code in (301, 302, 303, 307, 308):
            location = urllib.parse.urljoin(url, error.headers['Location'])
            return urllib.request.urlopen(location, timeout=120)
        raise


def builder_reference():
    lock = json.loads(LOCK.read_text())
    return next(mod['builder'] for mod in lock['mods'] if mod['file'] == 'aresos.jar')


def read_image(reference):
    name, digest = reference.split('@', 1)
    registry, repository = name.split('/', 1)
    repository = repository.rsplit(':', 1)[0]
    assert registry == 'docker.io', registry
    token = json.load(urllib.request.urlopen(
        'https://auth.docker.io/token?service=registry.docker.io&scope=repository:' + repository + ':pull',
        timeout=60))['token']
    headers = {'Authorization': 'Bearer ' + token, 'Accept': ACCEPT}
    base = f'https://registry-1.docker.io/v2/{repository}'

    def manifest(ref):
        data = get(f'{base}/manifests/{ref}', headers).read()
        if ref.startswith('sha256:'):
            assert 'sha256:' + hashlib.sha256(data).hexdigest() == ref, 'the registry sent other bytes'
        return json.loads(data)

    top = manifest(digest)
    if 'manifests' in top:
        chosen = next(m for m in top['manifests']
                      if m['platform'].get('os') == 'linux' and m['platform'].get('architecture') == 'amd64')
        top = manifest(chosen['digest'])

    def blob(item):
        response = get(f'{base}/blobs/{item["digest"]}', {'Authorization': headers['Authorization']})
        data = response.read()
        assert 'sha256:' + hashlib.sha256(data).hexdigest() == item['digest'], 'a layer has other bytes'
        return data

    config = json.loads(blob(top['config']))['config']
    files = {}
    for layer in top['layers']:
        with tarfile.open(fileobj=io.BytesIO(blob(layer)), mode='r:*') as archive:
            for member in archive:
                path = posixpath.normpath(member.name.lstrip('./')) if member.name not in ('.', './') else ''
                folder, leaf = posixpath.split(path)
                if leaf == '.wh..wh..opq':
                    files = {p: v for p, v in files.items() if not p.startswith(folder + '/')}
                    continue
                if leaf.startswith('.wh.'):
                    gone = posixpath.join(folder, leaf[4:])
                    files = {p: v for p, v in files.items() if p != gone and not p.startswith(gone + '/')}
                    continue
                if member.issym():
                    files[path] = ('link', member.linkname)
                elif member.isfile():
                    files[path] = ('file', member.mode)
                elif member.isdir():
                    files[path] = ('dir', member.mode)
    return config, files


def resolve(files, path, depth=0):
    """A path with symlinks followed (merged /usr: bin -> usr/bin)."""
    parts, out = path.strip('/').split('/'), ''
    for index, part in enumerate(parts):
        out = posixpath.join(out, part)
        kind = files.get(out)
        if kind and kind[0] == 'link' and depth < 20:
            target = kind[1] if kind[1].startswith('/') else posixpath.join(posixpath.dirname(out), kind[1])
            return resolve(files, posixpath.join(posixpath.normpath(target), *parts[index + 1:]), depth + 1)
    return out


def listing(reference):
    config, files = read_image(reference)
    env = dict(item.split('=', 1) for item in config.get('Env', []))
    lines = [f'# builder {reference}', f'# PATH={env.get("PATH", "")}', f'# JAVA_HOME={env.get("JAVA_HOME", "")}']
    names = set()
    for folder in env.get('PATH', '').split(':'):
        real = resolve(files, folder)
        for path, (kind, value) in files.items():
            if posixpath.dirname(path) != real:
                continue
            target = resolve(files, path)
            entry = files.get(target)
            if entry and entry[0] == 'file' and entry[1] & 0o111:
                names.add(posixpath.basename(path))
    return '\n'.join(lines + sorted(names)) + '\n'


def main(argv):
    text = listing(builder_reference())
    if argv[1:] == ['--check']:
        if OUTPUT.read_text() != text:
            print('minecraft/builder-tools.txt differs from the pinned builder image', file=sys.stderr)
            return 1
        print('BUILDER_TOOLS_MATCH')
        return 0
    OUTPUT.write_text(text)
    print(f'{len(text.splitlines()) - 3} executables written to {OUTPUT}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
