import copy
import pathlib
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'ci'))
from rehearsal_guard import require_probe, job_minutes
from installer_webui import Pages, validate_review


class ReviewBoundaryTest(unittest.TestCase):
    def test_probe_navigation_refuses_the_destructive_install_button(self):
        pages = object.__new__(Pages)
        pages.frame = Mock()
        button = pages.frame.locator.return_value
        button.inner_text.return_value = 'Erase data and install'
        with self.assertRaisesRegex(AssertionError, 'cannot invoke installation'):
            pages.next()
        button.click.assert_not_called()

    def test_requires_only_target_rows_and_a_new_target_efi_in_both_orders(self):
        for protected, target in [('vda', 'vdb'), ('vdb', 'vda')]:
            table = dict(disk=target, rows=[
                dict(device=target + '1', mount='/boot/efi', action='format as efi'),
                dict(device=target + '2', mount='/boot', action='format as ext4'),
                dict(device=target + '3', mount='/', action='format as btrfs subvolume')])
            validate_review([table], protected, target)
            for bad_device, bad_action in [(protected + '1', 'format as efi'),
                                           (target + '1', 'mount'), ('unknown', 'format as efi')]:
                wrong = copy.deepcopy(table)
                wrong['rows'][0].update(device=bad_device, action=bad_action)
                with self.assertRaises(AssertionError):
                    validate_review([wrong], protected, target)
            with self.assertRaises(AssertionError):
                validate_review([table, dict(disk=protected, rows=[])], protected, target)
            with self.assertRaises(AssertionError):
                validate_review([], protected, target)


class ProbeAuthorizationTest(unittest.TestCase):
    def test_full_run_rejects_failed_stale_or_different_workflow_probe(self):
        good = dict(event='workflow_dispatch', path='.github/workflows/os-image.yml',
                    head_branch='pkg/11-two-disk-rehearsal', head_sha='a' * 40,
                    display_title='Two-disk rehearsal (probe)', status='completed', conclusion='success')
        require_probe(good, 'a' * 40)
        for key, value in [('head_sha', 'b' * 40), ('conclusion', 'failure'),
                           ('display_title', 'Two-disk rehearsal (full)'), ('event', 'push'),
                           ('head_branch', 'main'), ('path', '.github/workflows/other.yml')]:
            wrong = copy.deepcopy(good)
            wrong[key] = value
            with self.assertRaises(AssertionError):
                require_probe(wrong, 'a' * 40)

    def test_minute_ledger_rounds_each_executed_job_up(self):
        job = dict(conclusion='success', started_at='2026-10-22T23:40:00Z', completed_at='2026-10-22T23:41:01Z')
        self.assertEqual(job_minutes(job), 2)
        job['conclusion'] = 'skipped'
        self.assertEqual(job_minutes(job), 0)


if __name__ == '__main__':
    unittest.main()
