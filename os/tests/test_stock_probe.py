import contextlib
import io
import json
import pathlib
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
import stock_probe as probe


class CachedStockProbeTest(unittest.TestCase):
    def setUp(self):
        self.images = json.loads((ROOT / 'os/manifest/ci/11g/probe-2/installer/var_lib_containers_storage_overlay-images_images.json').read_text())
        self.digest = json.loads((ROOT / 'os/manifest/base.json').read_text())['reference'].split('@', 1)[1]

    def test_real_iso_cache_resolves_by_pinned_digest_and_not_mutable_tag(self):
        image = probe.cached_image(self.images, self.digest)
        self.assertEqual(image, '0e4c3c1f2339438b7dc7e88d93ad8aa5f77663e04490fcb875549f4f062a5431')
        self.images[0]['names'] = ['an-untrusted-mutable-name']
        self.assertEqual(probe.cached_image(self.images, self.digest), image)

    def test_missing_ambiguous_or_invalid_cache_fails_without_registry_fallback(self):
        for images in ([], self.images * 2, [dict(self.images[0], digest='sha256:' + '0' * 64)],
                       [dict(self.images[0], id='not-an-image-id')]):
            with self.subTest(images=images), self.assertRaises(AssertionError):
                probe.cached_image(images, self.digest)

    def test_read_only_help_has_no_pull_network_host_mount_or_owner_auth(self):
        image = probe.cached_image(self.images, self.digest)
        command = probe.help_command(image)
        self.assertIn('--pull=never', command)
        self.assertIn('--network=none', command)
        self.assertIn('--read-only', command)
        self.assertIn('--rm', command)
        self.assertFalse(any(x.startswith(('--volume', '--mount', '--privileged')) for x in command))
        source = dict(daemon_comm='rpm-ostree', versions={'rpm-ostree': '2026.3', 'uupd': '1.5.0'},
                      bootloader_versions={'ostree': '2026.4-1.fc44', 'grub2-common': '2.12-66.fc44'})
        result = Mock(returncode=0, stdout=('CACHED_STOCK_CLI_HELP_PASSED\nARESOS_STOCK_IDLE_SOURCE_CHECK ' + json.dumps(source) + '\n').encode(), stderr=b'')
        with patch.object(pathlib.Path, 'read_text', return_value=json.dumps(self.images)), \
             patch.object(probe.subprocess, 'check_output', return_value=json.dumps([dict(Id=image, Digest=self.digest)]).encode()), \
             patch.object(probe.subprocess, 'run', return_value=result) as run, contextlib.redirect_stdout(io.StringIO()):
            probe.main(self.digest)
        self.assertEqual(run.call_args.args[0], command)
        self.assertEqual(run.call_args.kwargs['env']['REGISTRY_AUTH_FILE'], '/dev/null')


if __name__ == '__main__':
    unittest.main()
