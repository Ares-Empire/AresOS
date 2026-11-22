"""Brief 18c-b, item 5: the test-only Chrome pieces of the Control test layer (check_build=control only).

Run once by os/ci/control/Containerfile, as root inside the layer build, with the image's own Python and
`cryptography`:  python3 -I -B chrome_layer.py <staging folder>
The staging folder holds pack.py with its templates (packaging/), our extension's sources (extension/), the
install proof's probe (probe/) and its host (probe_host.py), all copied from this checkout.

It lays out what the Chrome pass needs beside the image's own browser side, never inside it:
- the probe extension (item 2): packed under its own fresh key like ours, installed by its own policy file that sets
  ExtensionInstallForcelist alone, from its own file: address, with its own test-only native host;
- an extension as he would load one by hand (C2's question, lead's decision 5 after step 2b);
- bundles B and C, each from one pack.py call over the commit's extension (for step 5's C4 and C5).
Each key lives only inside pack.py's call. Only public values (IDs, versions, hashes) are written down.
"""
import json
import os
import pathlib
import shutil
import sys

TEST = pathlib.Path('/usr/share/aresos-install-test')
PROBE_FILES = TEST / 'probe'
ORDINARY = TEST / 'ordinary'
BUNDLES = TEST / 'bundles'
PROBE_HOST = pathlib.Path('/usr/libexec/aresos-install-test/probe-host')
PROBE_NAME = 'org.aresos.install_probe'
POLICIES = pathlib.Path('/etc/opt/chrome/policies/managed')
PROBE_POLICY = POLICIES / 'aresos-install-probe.json'
HOSTS = pathlib.Path('/etc/opt/chrome/native-messaging-hosts')
# The probe host's two paths in the container (proof.py's /out and /run folders); the guest has no /out, so both
# move to the run folder the Chrome pass makes at boot.
RUN = '/run/aresos-install-test'
HOST_PATHS = {"SOCKET = '/run/aresos-install-test/probe.sock'": f"SOCKET = '{RUN}/probe.sock'",
              "LOG = '/out/install/probe.jsonl'": f"LOG = '{RUN}/probe.jsonl'"}
RECORD = TEST / 'layer.json'


def write(path, data, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else data.encode())
    os.chmod(path, mode)


def probe_host(source):
    """Move the proof host's paths and record startup before the guest socket can fail."""
    text = source.read_text()
    connect = '        connection.connect(SOCKET)'
    starts = {
        '    with socket.socket': "    note('started', 'true')\n    with socket.socket",
        connect: ('        try:\n' + '    ' + connect + '\n'
                  "        except OSError as error:\n"
                  "            note('connect_error', json.dumps(str(error)))\n"
                  '            raise'),
    }
    for old, new in {**HOST_PATHS, **starts}.items():
        assert text.count(old) == 1, f'probe_host.py must hold {old!r} exactly once'
        text = text.replace(old, new)
    return text


def main(staging):
    sys.path.insert(0, str(staging / 'packaging'))
    import pack

    manifest = json.loads((staging / 'probe/manifest.json').read_text())
    assert manifest['update_url'] == 'http://localhost:18766/probe/update.xml', manifest['update_url']
    files, probe = pack.pack(staging / 'probe')
    write(PROBE_FILES / 'extension.crx', files['extension.crx'])
    write(PROBE_FILES / 'update.xml',
          '<?xml version="1.0" encoding="UTF-8"?>\n<gupdate xmlns="http://www.google.com/update2/response" '
          f'protocol="2.0"><app appid="{probe["id"]}"><updatecheck codebase="file://{PROBE_FILES}/extension.crx" '
          f'version="{probe["version"]}" /></app></gupdate>\n')
    # Chrome takes each policy key from one file only: this file sets the one key ours doesn't.
    write(PROBE_POLICY, json.dumps({'ExtensionInstallForcelist': [f'{probe["id"]};file://{PROBE_FILES}/update.xml']}))
    write(PROBE_HOST, probe_host(staging / 'probe_host.py'), 0o755)
    write(HOSTS / f'{PROBE_NAME}.json', json.dumps({
        'name': PROBE_NAME, 'description': 'Test-only host of the install probe', 'path': str(PROBE_HOST),
        'type': 'stdio', 'allowed_origins': [f'chrome-extension://{probe["id"]}/']}))
    write(ORDINARY / 'manifest.json', json.dumps({
        'manifest_version': 3, 'name': 'AresOS install proof: loaded by hand (test only)', 'version': '1.0.0',
        'permissions': ['management']}))
    write(ORDINARY / 'page.html', '<!doctype html><title>Loaded by hand</title>')
    bundles = {}
    for name in ('b', 'c'):
        record = pack.write(str(staging / 'extension'), str(BUNDLES / name))
        bundles[name] = {key: record[key] for key in ('id', 'version', 'public_key_sha256', 'crx_sha256')}
    os.chmod(BUNDLES, 0o755)
    ids = [probe['id'], *(bundle['id'] for bundle in bundles.values())]
    assert len(set(ids)) == 3, ids
    write(RECORD, json.dumps({'probe': {key: probe[key] for key in ('id', 'version')}, 'bundles': bundles},
                             indent=1, sort_keys=True) + '\n')
    for folder in (TEST, PROBE_HOST.parent):
        for path in [folder, *folder.rglob('*')]:
            os.chown(path, 0, 0, follow_symlinks=False)
            if path.is_dir():
                os.chmod(path, 0o755)
    print('CONTROL_CHROME_LAYER ' + json.dumps({'probe': probe['id'], **{k: v['id'] for k, v in bundles.items()}}))


if __name__ == '__main__':
    assert len(sys.argv) == 2, 'usage: chrome_layer.py <staging folder>'
    main(pathlib.Path(sys.argv[1]))
    shutil.rmtree(sys.argv[1])
