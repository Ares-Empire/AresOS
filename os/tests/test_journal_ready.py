"""vm.py's journal readiness gate accepts only the exact, complete record (package 21 review 4)."""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
from journal_ready import follower_ready  # noqa: E402

# As the follower printed it in run 42709631386 (journalctl colour codes kept).
READY = '[   73.458055] bazzite aresos-ci[2795]: \x1b[0;1;39m\x1b[0;1;31m\x1b[0;1;39mARESOS_JOURNAL_READY\x1b[0m\r\n'
BEFORE = ("[   73.451944] bazzite audit[1]: \x1b[0;34mSERVICE_START pid=1 msg='unit=aresos-ci-journal'\x1b[0m\r\n")
AFTER = '[   73.460543] bazzite aresos-ci[2796]: \x1b[0;1;39mARESOS_POWER_KEY_ARMED\x1b[0m\r\n'


class JournalReadyTest(unittest.TestCase):
    def test_the_exact_record_counts_with_or_without_colour_and_carriage_return(self):
        self.assertTrue(follower_ready(BEFORE + READY + AFTER))
        self.assertTrue(follower_ready(READY.replace('\r\n', '\n')))
        self.assertTrue(follower_ready('[   12.000001] host aresos-ci[7]: ARESOS_JOURNAL_READY\n'))

    def test_chunked_input_counts_only_once_the_newline_has_arrived(self):
        stream = BEFORE + READY + AFTER
        end = len(BEFORE) + len(READY)
        for size in (1, 3, 7, 64):
            with self.subTest(size=size):
                seen = ''
                first = None
                for start in range(0, len(stream), size):
                    seen += stream[start:start + size]
                    if first is None and follower_ready(seen):
                        first = len(seen)
                self.assertIsNotNone(first)
                # Ready only once the record's newline is in; never earlier.
                self.assertGreaterEqual(first, end)
                self.assertLess(first - size, end)
                self.assertFalse(follower_ready(stream[:end - 1]))

    def test_false_markers_never_count(self):
        prefix = '[   73.458055] bazzite aresos-ci[2795]: '
        for message in ('FAILED ARESOS_JOURNAL_READY', 'ARESOS_JOURNAL_READY_NOT', 'ARESOS_JOURNAL_READY ',
                        ' ARESOS_JOURNAL_READY', 'not ARESOS_JOURNAL_READY yet', 'ARESOS_JOURNAL_REAdY',
                        '\x1b[0;1;31mFAILED\x1b[0m ARESOS_JOURNAL_READY'):
            with self.subTest(message=message):
                self.assertFalse(follower_ready(prefix + message + '\r\n'))
        for line in ('[   73.458055] bazzite kernel: ARESOS_JOURNAL_READY\r\n',
                     '[   73.458055] bazzite aresos-ci-other[2795]: ARESOS_JOURNAL_READY\r\n',
                     '[   73.458055] bazzite aresos-ci: ARESOS_JOURNAL_READY\r\n',
                     'ARESOS_JOURNAL_READY\r\n',
                     'echo [   73.458055] bazzite aresos-ci[2795]: ARESOS_JOURNAL_READY\r\n'):
            with self.subTest(line=line):
                self.assertFalse(follower_ready(BEFORE + line + AFTER))

    def test_no_line_break_may_sit_anywhere_before_the_message(self):
        # Review 5: \s* in the timestamp spanned line breaks.
        good = '[   73.458055] bazzite aresos-ci[2795]: ARESOS_JOURNAL_READY\n'
        self.assertTrue(follower_ready(good))
        message = good.index('ARESOS')
        for position in range(1, message):
            for breaker in ('\n', '\r', '\r\n'):
                with self.subTest(position=position, breaker=repr(breaker)):
                    broken = good[:position] + breaker + good[position:]
                    self.assertFalse(follower_ready(broken), repr(broken))
        for line in ('[\n 1.0] host aresos-ci[7]: ARESOS_JOURNAL_READY\n',
                     '[\r 1.0] host aresos-ci[7]: ARESOS_JOURNAL_READY\n',
                     '[ 1.0]\nhost aresos-ci[7]: ARESOS_JOURNAL_READY\n',
                     '[ 1.0] host aresos-ci[7]:\nARESOS_JOURNAL_READY\n',
                     '[ 1.0] host aresos-ci[7]: \rARESOS_JOURNAL_READY\n',
                     'noise\r[ 1.0] host aresos-ci[7]: ARESOS_JOURNAL_READY\n'):
            with self.subTest(line=repr(line)):
                self.assertFalse(follower_ready(line))

    def test_an_unterminated_record_never_counts(self):
        self.assertFalse(follower_ready(READY.rstrip('\r\n')))
        self.assertFalse(follower_ready(BEFORE + READY.rstrip('\n')))
        self.assertFalse(follower_ready(''))

    def test_vm_uses_only_this_gate(self):
        source = (ROOT / 'os/ci/vm.py').read_text()
        self.assertIn('from journal_ready import follower_ready', source)
        self.assertIn("if follower_ready((evidence / 'serial.log').read_bytes()[journal_start:]", source)
        self.assertNotIn('serial_search', source)


if __name__ == '__main__':
    unittest.main()
