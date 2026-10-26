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
import test_owner_equality
import test_owner_tools
import test_release_squash_binding
import test_ci_api_permissions
import test_owner_media
import test_owner_capabilities


def main():
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m) for m in
        (test_owner_commands,test_owner_export,test_owner_transport,test_owner_walk,test_owner_guard,test_owner_equality,test_owner_tools,
         test_release_squash_binding,test_ci_api_permissions,test_owner_media,test_owner_capabilities))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    assert result.wasSuccessful() and not result.skipped
    walk=test_owner_walk.walk()
    files=set()
    for pattern in ('os/ci/owner*.py','os/ci/offline_webui.py','os/owner-tools/*.py','os/owner-tools/at',
                    'os/owner-tools/commands.json','os/release/*.sh','os/tests/test_owner*.py','os/tests/owner_shim.py',
                    'docs/install-tools/OwnerTools.psm1','reviews/14-owner-tools/walk-host.py',
                    'os/manifest/ci/14/hotplug-sources/*','os/manifest/ci/14/keyboard-sources/*'):
        files.update(p for p in ROOT.glob(pattern) if p.is_file())
    files.update(ROOT/p for p in ('os/ci/installer_webui.py','os/ci/two_disk_vm.py','os/ci/registry_auth.py',
        'os/ci/rehearsal_guard.py','os/ci/rehearsal-packages.json','os/ci/verify_release.py',
        'os/tests/test_release_squash_binding.py','os/tests/test_ci_api_permissions.py','os/tests/owner_fuse_shim.py',
        '.github/workflows/os-image.yml'))
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
