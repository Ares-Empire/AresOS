"""Account for every local discovery result without hiding unavailable tests."""
import hashlib
import json
import pathlib
import re
import subprocess

review = pathlib.Path('reviews/11-two-disk-rehearsal')
logs = review / 'logs/11n'
text = (logs / 'local-native-tests.txt').read_text(encoding='utf-8')
assert 'Ran 201 tests in 119.174s' in text and 'FAILED (failures=2, errors=9)' in text
unavailable = set(re.findall(r'^(?:ERROR|FAIL): [^\n]+ \(([^)]+)\)', text, re.M))
expected = {
    'test_greeter.GreeterTest.test_active_service_without_drawing_hits_deadline': 'WSL has no Pillow; passed using existing Windows Pillow12.2.0',
    'test_greeter.GreeterTest.test_black_cursor_and_flat_background_are_not_rendered_greeters': 'WSL has no Pillow; passed using existing Windows Pillow12.2.0',
    'test_greeter.GreeterTest.test_capture_waits_for_drawing_and_keeps_ready_evidence': 'WSL has no Pillow; passed using existing Windows Pillow12.2.0',
    'test_inherited_homebrew.InheritedHomebrewTest.test_absent_inherited_installation_is_not_created': 'Requires sudo/systemd-tmpfiles on temporary fixture; local elevation blocked',
    'test_inherited_homebrew.InheritedHomebrewTest.test_denies_daily_execution_and_reading_preserves_owner_and_content_idempotently': 'Requires sudo/chown/setpriv and POSIX ACLs on temporary fixture; local elevation blocked',
    'test_inherited_homebrew.InheritedHomebrewTest.test_preserves_existing_acl_entries_and_restrictive_mask': 'Requires sudo/chown/setpriv and POSIX ACLs on temporary fixture; local elevation blocked',
    'test_sysusers.SysusersRebaseTest.test_preserves_recovery_admin_and_creates_locked_daily_user_idempotently': 'Requires sudo/systemd-sysusers on temporary fixture; local elevation blocked',
    'test_rehearsal_auth.OwnerAuthTest.test_auth_is_outside_workspace_and_always_removed_before_artifact_upload': 'DrvFS reports0777 after requested0600; requires native POSIX filesystem, no assertion change',
}
assert unavailable == set(expected), unavailable ^ set(expected)
assert text.count("ModuleNotFoundError: No module named 'PIL'") == 3
assert 'LOCAL_UNAVAILABLE: local elevation forbidden' in text and '511 != 384' in text
for name in ('test_install_transactions_stop_on_failure_and_never_include_the_reboot',
             'test_owner_switch_prerequisites_stop_before_the_transaction',
             'test_owner_switch_block_is_exact_release_script'):
    assert re.search(r'^' + name + r' .* \.\.\. ok$', text, re.M), name
windows = (logs / 'local-windows-greeter.txt').read_text(encoding='utf-8')
assert 'Ran 4 tests in 1.277s' in windows and windows.rstrip().endswith('OK')
# Only the requested fixture changes. The product block and equality test do not.
unchanged = ['os/release/switch.sh', 'docs/INSTALL.md', 'os/tests/test_grub_bls.py',
             'os/ci/rehearsal_guard.py', 'os/ci/two_disk_vm.py', 'os/ci/disk_audit.py',
             'os/ci/grub_bls.py', 'os/ci/stock_probe.py', 'os/ci/rehearsal_auth.py',
             '.github/workflows/os-image.yml', '.github/workflows/privacy-check.yml',
             '.gitleaks.toml', '.gitleaksignore', 'os/manifest/base.json', 'os/manifest/release.json']
hashes = []
for name in unchanged:
    raw = pathlib.Path(name).read_bytes().replace(b'\r\n', b'\n')
    if name == 'docs/INSTALL.md':
        # The completed report may update qualification prose after the runs.
        # Replay the full pre-dispatch guide from its actual tested Git blob;
        # every executable block in the final guide must still be identical.
        tested = subprocess.check_output(['git', 'show', '46dc2dd:' + name])
        blocks = lambda content: re.findall(rb'^```bash\n(.*?)\n```', content, re.M | re.S)
        assert blocks(raw) == blocks(tested)
        raw = tested
    assert raw == subprocess.check_output(['git', 'show', '04ae68d:' + name]), name
    hashes.append(dict(path=name, sha256=hashlib.sha256(raw).hexdigest()))
directory = pathlib.Path('os/manifest/ci/11n'); directory.mkdir(parents=True, exist_ok=True)
result = dict(status='local-discovery-complete-with-explicit-environment-limits',
              discovered=201, wsl_passed=193, wsl_unavailable=expected, failures=2, errors=9,
              explanation='Eight unique tests; inherited-Homebrew cleanup errors repeat some tests. No tests skipped or weakened.',
              windows_greeter_passed=4, combined_locally_passed=196, native_ci_still_required=5,
              changed_fixture_and_five_negative_cases_passed=True,
              native_before_probe_plan='Existing checks_only dispatch on the tested source,15-minute timeout reserved separately; complete201 tests must pass before probe.',
              owner_guide_limit='Full tested46dc2dd guide equals04ae68d; final executable blocks must match, qualification prose may be updated.',
              unchanged_files=hashes)
(directory / 'local-tests.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
for path in logs.glob('local-*.txt'):
    path.write_text('\n'.join(line.rstrip() for line in path.read_text(encoding='utf-8').splitlines()).rstrip() + '\n', encoding='utf-8', newline='\n')
print('Local201 accounted:193 WSL pass,8 explicit environment limits; Windows greeter4 pass;196 unique tests passed locally,5 require native CI. Exact block/equality/runtime unchanged.')
