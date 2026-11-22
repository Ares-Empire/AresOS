"""Check image additions in the unmerged overlay directories, including deleted files."""
import json
import os
import pathlib
import sys

EXCLUDED_COMPONENTS = frozenset({'.cargo', '.rustup', 'Cargo.lock', 'Cargo.toml',
                                 'cargo', 'rustc', 'rustup', 'wl-harness'})
BUILDER_PATHS = {'src', 'out', 'source/os/input-portal', 'tmp/aresos/input-portal'}
RUST_FILE_SUFFIXES = ('.rs', '.rlib', '.rmeta', '.d')


def added_layers(base, image):
    def layers(value):
        driver = value['GraphDriver']
        assert driver['Name'] == 'overlay', driver['Name']
        data = driver['Data']
        return [data['UpperDir'], *filter(None, data.get('LowerDir', '').split(':'))]

    ancestors, full = layers(base), layers(image)
    assert len(full) > len(ancestors) and full[-len(ancestors):] == ancestors, 'base overlay chain differs'
    return [pathlib.Path(path) for path in full[:-len(ancestors)]]


def scan(layers):
    def fail(error):
        raise error

    for layer in layers:
        assert layer.is_dir(), layer
        for directory, dirs, files in os.walk(layer, onerror=fail):
            excluded = EXCLUDED_COMPONENTS | {name for name in files if name.endswith(RUST_FILE_SUFFIXES)}
            if 'target' in dirs:
                excluded |= {'target'}
            for name in dirs + files:
                path = (pathlib.Path(directory) / name).relative_to(layer)
                if name in excluded or path.as_posix() in BUILDER_PATHS:
                    raise ValueError(f'Input portal build or harness material in {layer.parent.name}: {path}')


def main(base, image):
    layers = added_layers(*(json.loads(pathlib.Path(name).read_text())[0] for name in (base, image)))
    scan(layers)
    print(f'INPUT_PORTAL_LAYERS_PASSED {len(layers)} added layers')


if __name__ == '__main__':
    main(*sys.argv[1:])
