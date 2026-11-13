"""Decision 24: unrelated policy sources and plugins never gate our tools."""
from pathlib import Path
from unittest.mock import patch

from aresos_control import boundary
import test_boundary_exact as previous


class PolicySources(previous.ExactBoundary):
    def test_dropins_plugins_remote_cache_and_private_home_are_not_read(self):
        directory = self.settings.with_name('managed-settings.d')
        directory.mkdir()
        (directory / '99-open.json').write_text('{"permissions":{"allow":["mcp__mail__*"]}}')
        (directory / 'notes.txt').write_text('unrelated settings')
        remote = self.settings.parent / 'private-owner' / '.claude' / 'remote-settings.json'
        remote.parent.mkdir(parents=True)
        remote.write_text('{}')
        registry = remote.parent / 'plugins' / 'installed_plugins.json'
        registry.parent.mkdir()
        registry.write_text('{"plugins":{"personal@local":[]}}')
        real_open = boundary.os.open
        def protected_open(path, *args, **kwargs):
            self.assertNotIn(str(path), {'managed-settings.d', 'private-owner', str(remote), str(registry)})
            return real_open(path, *args, **kwargs)
        with patch('aresos_control.boundary.os.open', side_effect=protected_open):
            self.engine.boundary.require()
        directory.rename(directory.with_name('other-sources'))
        directory.symlink_to(directory.with_name('other-sources'), target_is_directory=True)
        self.engine.boundary.require()
        self.assertEqual(self.data('testapp_send', self.approval)['operation']['state'], 'done')
