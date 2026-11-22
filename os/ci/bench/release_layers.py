"""Check Podman's unpacked overlay layers before a merge or whiteout can hide a path."""
import json
import pathlib
import stat
import sys

BENCH_PATHS = (
    'tmp/aresos/ci/bench',
    'tmp/aresos/bench',
    'usr/libexec/aresos-bench',
    'usr/lib/systemd/system/aresos-bench.service',
    'usr/lib/systemd/system/multi-user.target.wants/aresos-bench.service',
)


class BenchFile(Exception):
    pass


def layer_paths(image):
    driver = image['GraphDriver']
    if driver['Name'] != 'overlay':
        raise ValueError('Raw layer scan requires Podman overlay storage')
    data = driver['Data']
    roots = [data['UpperDir'], *data.get('LowerDir', '').split(':')] if data.get('LowerDir') else [data['UpperDir']]
    if len(roots) != len(image['RootFS']['Layers']) or len(set(roots)) != len(roots):
        raise ValueError('Incomplete overlay layer list')
    for root in roots:
        path = pathlib.Path(root)
        if not path.is_absolute() or not path.is_dir():
            raise ValueError('Missing overlay layer directory')
        yield path


def scan(image):
    count = 0
    for root in layer_paths(image):
        for name in BENCH_PATHS:
            path = root
            parts = pathlib.PurePosixPath(name).parts
            for index, part in enumerate(parts):
                path = path / part
                try:
                    mode = path.lstat().st_mode
                except FileNotFoundError:
                    break
                if index == len(parts) - 1:
                    raise BenchFile(name)
                # A raw layer has no children beneath a symlink or whiteout.
                if not stat.S_ISDIR(mode):
                    break
        count += 1
    return count


if __name__ == '__main__':
    try:
        count = scan(json.load(sys.stdin)[0])
    except BenchFile as error:
        print(f'Bench file found in raw image layer ({error})', file=sys.stderr)
        sys.exit(1)
    except (KeyError, IndexError, OSError, ValueError):
        print('Could not inspect all raw image layers', file=sys.stderr)
        sys.exit(2)
    print(f'No bench files in {count} raw image layers')
