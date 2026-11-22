"""The input portal source exclusion covers files hidden by later layers."""
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'ci/deskflow'))
from check_layers import added_layers, scan  # noqa: E402


def inspect(*chain):
    return {'GraphDriver': {'Name': 'overlay',
                            'Data': {'UpperDir': str(chain[0]), 'LowerDir': ':'.join(map(str, chain[1:]))}}}


class InputPortalLayersTest(unittest.TestCase):
    def test_scan_only_reads_layers_added_to_the_pinned_base(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            base, image = root / 'base', root / 'image'
            base.mkdir()
            image.mkdir()
            (base / 'rustc').touch()
            installed = image / 'usr/libexec/aresos-input-portal'
            installed.parent.mkdir(parents=True)
            installed.touch()
            (image / 'usr/libexec/config.d').mkdir()
            layers = added_layers(inspect(base), inspect(image, base))
            self.assertEqual(layers, [image])
            scan(layers)

    def test_hidden_source_and_toolchain_are_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            base, intermediate, final = (root / name for name in ('base', 'intermediate', 'final'))
            for path in (base, intermediate, final):
                path.mkdir()
            layers = added_layers(inspect(base), inspect(final, intermediate, base))
            for leak in ('tmp/aresos/input-portal', 'usr/local/bin/rustc', 'opt/crates/Cargo.lock',
                         'usr/share/aresos/input-portal/main.rs', 'opt/project/Cargo.toml',
                         'opt/build/libportal.rlib', 'opt/build/libportal.rmeta', 'opt/build/portal.d',
                         'opt/project/target/portal', 'opt/relocated/libserde_derive-43ae5d4e1341043d.so',
                         'opt/relocated/build-script-build', 'opt/relocated/build_script_build-43ae5d4e1341043d',
                         'opt/relocated/portal-43ae5d4e1341043d', 'opt/relocated/invoked.timestamp'):
                with self.subTest(leak=leak):
                    path = intermediate / leak
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.touch()
                    if path.name == 'main.rs' or path.parent.name == 'relocated':
                        # The final overlay's opaque directory hides relocated build material.
                        hidden = final / path.parent.relative_to(intermediate)
                        hidden.mkdir(parents=True, exist_ok=True)
                        (hidden / '.wh..wh..opq').touch()
                    scan([final])
                    rejected = 'opt/project/target' if 'target' in path.parts else leak
                    with self.assertRaisesRegex(ValueError, rejected):
                        scan(layers)
                    path.unlink()

    def test_rejects_an_unexpected_base_chain(self):
        with self.assertRaisesRegex(AssertionError, 'base overlay chain differs'):
            added_layers(inspect('/correct/base'), inspect('/new/layer', '/wrong/base'))
