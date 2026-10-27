"""Run the zero-cost package14 walk and bind its result to reviewed sources.

No VM, privilege, hardware query or token is needed. Command responses are
explicit stand-ins; this is prerequisite evidence, never VM acceptance.
"""
import hashlib
import json
import pathlib
import sys
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'os/tests'))
import test_owner_commands
import test_owner_export
import test_owner_transport
import test_owner_walk
import test_owner_guard
import test_organization_budget
import test_rehearsal_budget
import test_installer_download
import test_installer_webui
import test_owner_equality
import test_owner_tools
import test_release_squash_binding
import test_ci_api_permissions
import test_ci_step_environment
import test_owner_media
import test_owner_capabilities
import test_guest_framing
import test_owner_console
import test_owner_devices
import test_owner_entry
import test_owner_devices_native
import test_loop_nodes
import test_owner_firmware
import test_owner_diagnostics
import test_owner_artifact_class
import test_owner_format_audit


def main():
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m) for m in
        (test_owner_commands,test_owner_export,test_owner_transport,test_owner_walk,test_owner_guard,test_organization_budget,test_rehearsal_budget,test_installer_download,test_installer_webui,test_owner_equality,test_owner_tools,
         test_release_squash_binding,test_ci_api_permissions,test_ci_step_environment,test_owner_media,test_owner_capabilities,test_guest_framing,
         test_owner_console,test_owner_devices,test_owner_entry,test_owner_devices_native,test_loop_nodes,
         test_owner_firmware,test_owner_diagnostics,test_owner_artifact_class,test_owner_format_audit))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    assert result.wasSuccessful() and not result.skipped
    walk=test_owner_walk.walk()
    files=set()
    for pattern in ('os/ci/owner*.py','os/ci/offline_webui.py','os/owner-tools/*.py','os/owner-tools/at',
                    'os/owner-tools/commands.json','os/release/*.sh','os/tests/test_owner*.py','os/tests/owner_shim.py',
                    'docs/install-tools/OwnerTools.psm1','reviews/14-owner-tools/walk-host.py',
                    'os/manifest/ci/14/hotplug-sources/*','os/manifest/ci/14/keyboard-sources/*',
                    'os/tests/fixtures/owner-console/*','os/tests/fixtures/owner-tools/storage-*.json',
                    'os/tests/fixtures/owner-tools/blkid-p-gpt*', 'os/tests/fixtures/owner-tools/efibootmgr*',
                    'os/tests/fixtures/owner-tools/dumpkeys-*','os/tests/fixtures/owner-tools/tool-output-sources.json',
                    'os/manifest/ci/14/parser-sources/*','reviews/14-owner-tools/classify-artifacts.py',
                    'reviews/14-owner-tools/verify-parser-rpmdb.py'):
        files.update(p for p in ROOT.glob(pattern) if p.is_file())
    files.update(ROOT/p for p in ('os/ci/installer_webui.py','os/ci/two_disk_vm.py','os/ci/registry_auth.py',
        'os/ci/rehearsal_guard.py','os/ci/rehearsal-packages.json','os/ci/verify_release.py',
        'os/tests/test_release_squash_binding.py','os/tests/test_ci_api_permissions.py','os/tests/test_ci_step_environment.py','os/tests/test_organization_budget.py','os/tests/test_rehearsal_budget.py','os/tests/owner_fuse_shim.py',
        'os/ci/switch_vm.py','os/ci/serial_console.py','os/tests/guest_shell.py','os/tests/test_guest_framing.py',
        'os/tests/test_keyboard_walk.py','os/ci/prepare_two_disks.py','os/tests/test_loop_nodes.py',
        '.github/workflows/os-image.yml','os/ci/installer_inspect.py','os/manifest/installer-isos.json',
        'os/tests/test_installer_download.py','os/tests/test_installer_webui.py'))
    proof=dict(status='passed',kind='local stand-ins, not VM qualification',tests=result.testsRun,
        stick_across_reboot=False, stages=walk['stages'],markers=walk['markers'],checks=walk['checks'],
        typed_profiles=sorted({profile for text,profile in walk['typed']}),
        sources=[dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(), path=p.relative_to(ROOT).as_posix())
                 for p in sorted(files)])
    folder=ROOT/'os/manifest/ci/14/host-walk';folder.mkdir(exist_ok=True)
    (folder/'result.json').write_text(json.dumps(proof,indent=2)+'\n', newline='\n')
    (folder/'guest-commands.json').write_text(json.dumps(walk['commands'],indent=2)+'\n', newline='\n')
    print('PASS local owner host walk; no stick across any reboot; no VM started')


if __name__=='__main__':main()
