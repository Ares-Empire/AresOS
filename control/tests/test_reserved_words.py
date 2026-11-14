"""The command name `aresos` is shared (package 18c, agreed change 13).

The owner asked for `aresos update` instead of the long owner-tools command (board #195), so a later OS package puts
a small dispatcher at /usr/bin/aresos in front of Control's command. These words belong to the owner tools and never
become a served app or a top-level word of Control's CLI.
"""
from pathlib import Path
import unittest

from aresos_control.boundary_policy import user_mcp
from aresos_control.definitions import APPS

RESERVED = frozenset({'update', 'forward', 'previous', 'rollback', 'keep-stock', 'check', 'title', 'records', 'export',
                      'login', 'verify', 'switch', 'install', 'prepare', 'layout', 'reboot', 'logs'})
# cli.main's own words before an app name: `aresos admin <app> <action>` and `aresos log`.
CLI_WORDS = frozenset({'admin', 'log'})
HELP = Path(__file__).resolve().parents[1] / 'generated/cli-help.txt'


def help_words():
    """The first word after `aresos` on every usage and action line of the generated help."""
    words = set()
    for line in HELP.read_text().splitlines():
        parts = line.split()
        if 'aresos' in parts[:2]:
            words.add(parts[parts.index('aresos') + 1])
    return words


class ReservedWords(unittest.TestCase):
    def test_no_served_app_or_top_level_word_is_reserved_for_the_owner_tools(self):
        top_level = CLI_WORDS | APPS | set(user_mcp())
        self.assertLessEqual({'admin', 'log', 'control', 'mail', 'testapp'}, top_level, 'the check must see them')
        self.assertEqual(sorted(top_level & RESERVED), [])

    def test_the_generated_help_uses_only_those_words(self):
        words = help_words()
        # Each line names a word of its own; `[admin]` is the usage line's optional word.
        self.assertLessEqual({'[admin]', 'log', 'admin', 'control', 'mail', 'testapp'}, words)
        self.assertLessEqual(words - {'[admin]'}, CLI_WORDS | APPS, 'a new top-level word must be checked above')
        self.assertEqual(sorted(words & RESERVED), [])


if __name__ == '__main__':
    unittest.main()
