"""Base suites, with ledger-dependent integration checks selected explicitly."""
import sys
from pathlib import Path
import unittest


OPTIONAL = {
    'test_owner_state_channels.OwnerStateChannels.test_paged_committed_pending_through_every_installed_channel',
    'test_owner_state_oracle.OwnerOracle.test_every_pinned_gap_belongs_to_an_executed_suite',
}


def cases(suite):
    for case in suite:
        if isinstance(case, unittest.TestSuite):
            yield from cases(case)
        else:
            yield case


def select(suite, optional=False):
    return unittest.TestSuite(case for case in cases(suite) if (case.id() in OPTIONAL) == optional)


def main(optional=False):
    root = Path(__file__).resolve().parents[1] / 'tests'
    suite = unittest.defaultTestLoader.discover(str(root))
    return not unittest.TextTestRunner(verbosity=2).run(select(suite, optional)).wasSuccessful()


if __name__ == '__main__':
    raise SystemExit(main('--optional' in sys.argv[1:]))
