"""Package 40: a launch that does not open leaves a line in the helper's log.

In the owner's try-out an app "did not open" and neither log said why. The helper logged only launches it started:
an unknown app, an app whose program is missing and a launch that failed after starting were answered to the game and
left no line. Everything here is synthetic, as in test_aresos_shell.
"""
from unittest import mock

from test_aresos_shell import Base, shell


def lines(warning):
    return [call.args[0] % call.args[1:] for call in warning.call_args_list]


class RefusalLogTest(Base):
    def test_an_unknown_and_an_unavailable_app_are_logged(self):
        helper = self.helper()
        conn = self.connect(helper)
        with mock.patch.object(shell.LOG, 'warning') as warning:
            self.request(helper, conn, 'open_app', 'o-1', app_id='spotify')
            self.request(helper, conn, 'open_app', 'o-2', app_id='browser')
            # A resent request is answered from the journal: one line per launch, not per message.
            self.request(helper, conn, 'open_app', 'o-2', app_id='browser')
        self.assertEqual(lines(warning), ["'spotify' not opened: no such app", 'browser not opened: not_installed'])

    def test_an_unknown_id_is_logged_clipped_and_quoted(self):
        helper = self.helper()
        conn = self.connect(helper)
        with mock.patch.object(shell.LOG, 'warning') as warning:
            self.request(helper, conn, 'open_app', 'o-1', app_id='x\n' * 60)
        (line,) = lines(warning)
        self.assertNotIn('\n', line)
        self.assertLess(len(line), 200)

    def test_a_launch_that_shows_no_window_is_logged(self):
        helper = self.helper(tracked=True)
        conn = self.connect(helper)
        self.assertEqual(self.request(helper, conn, 'open_app', 'o-1', app_id='notepad')['state'], 'starting')
        with mock.patch.object(shell.LOG, 'warning') as warning:
            self.now[0] += shell.WINDOW_TIMEOUT + 0.1
            helper.tick()
        self.assertEqual(lines(warning), ['notepad failed after starting: no matching window appeared'])
