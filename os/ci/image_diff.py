"""Compare complete merged image files; only the reviewed keyboard files may differ."""
import hashlib
import gzip
import json
import os
import pathlib
import stat
import subprocess

CHANGES = {'usr/bin/aresos-session': 'os/config/usr/bin/aresos-session',
           'usr/libexec/aresos-keyboard': 'os/config/usr/libexec/aresos-keyboard'}
TOOLS = None


def inventory(root):
    root = pathlib.Path(root)
    result = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in sorted(dirs + files):
            path = pathlib.Path(directory) / name
            meta = path.lstat()
            value = dict(mode=stat.S_IMODE(meta.st_mode), uid=meta.st_uid, gid=meta.st_gid,
                         kind=stat.S_IFMT(meta.st_mode))
            value['xattrs'] = {key: os.getxattr(path, key, follow_symlinks=False).hex()
                              for key in sorted(os.listxattr(path, follow_symlinks=False))}
            if stat.S_ISLNK(meta.st_mode):
                value['target'] = os.readlink(path)
            elif stat.S_ISREG(meta.st_mode):
                with path.open('rb') as stream:
                    value['sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
                value['bytes'] = meta.st_size
            elif not stat.S_ISDIR(meta.st_mode):
                value['device'] = meta.st_rdev
            result[str(path.relative_to(root))] = value
    return result


def compare(old, new, expected):
    changed = {name: dict(before=old.get(name), after=new.get(name)) for name in sorted(old.keys() | new.keys())
               if old.get(name) != new.get(name)}
    assert set(changed) == set(expected), 'STOP: unexplained image file differences: ' + repr(sorted(changed.keys() ^ expected.keys()))
    for name, digest in expected.items():
        after = new[name]
        assert after['sha256'] == digest and after['mode'] == 0o755 and after['uid'] == after['gid'] == 0
        if name in old:
            assert {k: v for k, v in old[name].items() if k not in ('sha256', 'bytes')} == {
                k: v for k, v in after.items() if k not in ('sha256', 'bytes')}, 'STOP: unrelated keyboard-file metadata change'
    units = lambda data: {p: v for p, v in data.items() if '/systemd/' in p}
    assert units(old) == units(new), 'STOP: systemd units changed'
    return changed


def command(*args):
    assert TOOLS is not None and args[0] in ('podman', 'skopeo'), 'STOP: image diff tools were not validated'
    return subprocess.check_output([TOOLS[args[0]], *args[1:]], text=True).strip()


def main(tools):
    global TOOLS
    from build_tools import validate
    TOOLS = validate(tools)
    evidence = pathlib.Path('evidence/image-diff'); evidence.mkdir(parents=True)
    release = json.loads(pathlib.Path('os/manifest/releases/06.json').read_text())
    previous = release['reference']
    mounts = []
    try:
        data = []
        packages = []
        for name, image in (('old', previous), ('new', 'localhost/aresos:ci')):
            container = command('podman', 'create', '--pull=never', '--network=none', '--entrypoint=/usr/bin/true', image)
            mounts.append(container)
            root = pathlib.Path(command('podman', 'mount', container))
            record = inventory(root)
            # Full inventories stay reviewable without exceeding the inherited
            # evidence cap; compression does not omit any path or metadata.
            with gzip.open(evidence / (name + '-files.json.gz'), 'wt', encoding='utf-8') as stream:
                json.dump(record, stream, sort_keys=True)
                stream.write('\n')
            actual = command('podman', 'run', '--pull=never', '--network=none', '--read-only', '--rm',
                             '--entrypoint=/usr/bin/rpm', image, '-qa', '--qf', '%{NEVRA}\n').splitlines()
            packages.append(sorted(actual))
            lock = json.loads((root / 'usr/share/aresos/manifest/packages.lock.json').read_text())
            assert lock == json.loads(pathlib.Path('os/packages.lock.json').read_text()), 'STOP: locked packages changed'
            data.append(record)
        assert packages[0] == packages[1], 'STOP: package inventory changed'
        (evidence / 'packages.json').write_text(json.dumps(dict(old=packages[0], new=packages[1]), indent=2) + '\n')
        expected = {name: hashlib.sha256(pathlib.Path(source).read_bytes()).hexdigest() for name, source in CHANGES.items()}
        changes = compare(*data, expected)
        configs = []
        for image in (previous, 'localhost/aresos:ci'):
            configs.append(json.loads(command('skopeo', 'inspect', '--config', 'containers-storage:' + image)))
        base = json.loads(command('skopeo', 'inspect', '--config', 'docker://' + release['base']))
        assert configs[0]['rootfs']['diff_ids'][:len(base['rootfs']['diff_ids'])] == base['rootfs']['diff_ids'], 'STOP: previous release base ancestry differs'
        assert configs[1]['rootfs']['diff_ids'][:len(configs[0]['rootfs']['diff_ids'])] == configs[0]['rootfs']['diff_ids'], 'STOP: new release lost immutable previous layers'
        old_config, new_config = (dict(c['config']) for c in configs)
        old_labels, new_labels = old_config.pop('Labels'), new_config.pop('Labels')
        assert old_config == new_config, 'STOP: unrelated OCI runtime configuration changed'
        label_changes = {k: dict(before=old_labels.get(k), after=new_labels.get(k)) for k in old_labels.keys() | new_labels.keys()
                         if old_labels.get(k) != new_labels.get(k)}
        assert set(label_changes) <= {'org.opencontainers.image.source', 'org.opencontainers.image.revision', 'io.buildah.version'}
        assert new_labels['org.opencontainers.image.source'] == 'https://github.com/Ares-Empire/AresOS'
        assert new_labels['org.opencontainers.image.revision'] == os.environ['GITHUB_SHA']
        if 'io.buildah.version' in label_changes:
            assert new_labels['io.buildah.version'] == command('podman', 'info', '--format', '{{.Host.BuildahVersion}}')
        result = dict(status='passed', previous=previous, pinned_base=release['base'],
            package_count=len(packages[0]), packages_equal=True, units_equal=True,
            compared_files=[len(d) for d in data], files=changes, labels=label_changes,
            metadata_note='New OCI creation/history and layer digests describe this build; file mtimes/inodes are storage metadata, excluded from the semantic inventory.',
            base_ancestry_verified=True, previous_layer_prefix_preserved=True)
        (evidence / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print('IMAGE_DIFF_PASSED: exact packages/units/base ancestry; only the two reviewed keyboard files changed')
    finally:
        for container in reversed(mounts):
            command('podman', 'unmount', container)
            command('podman', 'rm', container)


if __name__ == '__main__':
    import sys
    from build_tools import load
    main(load(sys.argv[1]))
