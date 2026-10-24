import copy
import pathlib
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'ci'))
from rehearsal_guard import require_probe, job_minutes
from installer_webui import Pages, validate_review, validate_keyboard_selection, validate_keyboard_proof, completion_selectors
from installer_inspect import validate_download


class DownloadCompletenessTest(unittest.TestCase):
    def test_actual_short_transfer_is_not_mistaken_for_a_complete_new_iso(self):
        import json
        root = pathlib.Path(__file__).resolve().parents[2]
        observed = json.loads((root / 'os/manifest/ci/11b/probe-4/installer/iso-download.json').read_text())
        with self.assertRaisesRegex(IOError, 'Incomplete ISO transfer'):
            validate_download(observed, dict(sha256=observed['sha256']))

    def test_complete_transfer_still_requires_the_exact_pin(self):
        observed = dict(headers={'content-length': '10'}, bytes=10, downloaded_sha256='a' * 64)
        validate_download(observed, dict(sha256='a' * 64))
        with self.assertRaisesRegex(AssertionError, 'Downloaded ISO differs: STOP'):
            validate_download(observed, dict(sha256='b' * 64))


class ReviewBoundaryTest(unittest.TestCase):
    def test_completion_selectors_follow_actual_dynamic_class_and_modal_sources(self):
        folder = pathlib.Path(__file__).resolve().parents[2] / 'os/manifest/ci/11b/inspect-8/installer/webui-source'
        names = ['components/installation/InstallationProgress.jsx', 'components/Error.jsx', 'components/AnacondaWizardFooter.jsx']
        sources = {name: (folder / name).read_text() for name in names}
        selected = completion_selectors(sources)
        self.assertEqual(selected['success'], '.anaconda-screen-progress-status-success')
        self.assertEqual(selected['critical'], '#critical-error-bz-report-modal')
        self.assertNotIn('status-success', sources[names[0]])
        self.assertNotIn('critical-error-bz-report-modal', sources[names[1]])
        for name, before, after in [(names[0], 'setStatus("success")', 'setStatus("finished")'),
                                    (names[1], '"critical-error"', '"changed-prefix"')]:
            with self.assertRaises(AssertionError):
                completion_selectors(dict(sources, **{name: sources[name].replace(before, after)}))

    def test_read_only_module_proof_rejects_wrong_choices_and_changed_module(self):
        settings = dict(XLayouts=['de'], VirtualConsoleKeymap='', LayoutSwitchingOptions=[])
        proof = dict(xlayouts=['de'], model_keymap='', layout_switching_options=[],
                     module_before=settings, module_after=settings,
                     same_installation_resolver=True, read_only=True,
                     module_configuration_unchanged=True)
        validate_keyboard_proof(proof)
        for key, wrong in [('model_keymap', 'us'), ('xlayouts', ['us']),
                           ('same_installation_resolver', False), ('read_only', False),
                           ('module_configuration_unchanged', False),
                           ('module_after', dict(settings, LayoutSwitchingOptions=['caps:escape']))]:
            with self.assertRaises(AssertionError):
                validate_keyboard_proof(dict(proof, **{key: wrong}))

    def test_actual_modal_requires_only_german_before_next_commits_it(self):
        import json
        root = pathlib.Path(__file__).resolve().parents[2]
        frames = json.loads((root / 'os/manifest/ci/11b/probe-5/two-disk/keyboard-german-selected.json').read_text())
        selected = frames[0]['text'].split('Selected (top = current)\n')[1].split('\nSave')[0]
        validate_keyboard_selection(selected)
        for wrong in ('us', 'us\nde', 'de\nus', 'de(nodeadkeys)', ''):
            with self.assertRaises(AssertionError):
                validate_keyboard_selection(wrong)
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
