"""Resolve the Deskflow pin against simulated DNF repositories."""
import hashlib
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
NEVRA = 'deskflow-0:1.27.0-1.fc44.x86_64'
DIGEST = hashlib.sha256(b'fixture').hexdigest()
RESOLVE = r'''
set -euo pipefail
source "$1"
deskflow_sha256=$2
dnf5() {
    local args=" $* "
    case "$args" in
        *" repoquery "*"%{full_nevra} %{repoid}"*)
            if [[ $fixture_repo != updates-testing || $args == *" --enable-repo=updates-testing "* ]]; then
                printf '%s %s\n' "$deskflow_nevra" "$fixture_repo"
                if [[ $ambiguous == yes ]]; then printf '%s fedora\n' "$deskflow_nevra"; fi
            fi
            ;;
        *" repoquery "*)
            if [[ $fixture_repo != updates-testing ]]; then printf '%s\n' "$deskflow_nevra"; fi
            ;;
        *" download --resolve "*)
            printf '%s\n' "$*" > download-args
            printf '%s' "$rpm_contents" > deskflow-fixture.rpm
            ;;
        *) return 99 ;;
    esac
}
rpm() { printf '%s' "$deskflow_nevra"; }
resolve_deskflow_candidate "$3" . libportal
'''


class CheckResolveTest(unittest.TestCase):
    def resolve(self, mode, repo, *, ambiguous=False, rpm_contents='fixture'):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                ['/usr/bin/bash', '-c', RESOLVE, 'fixture', ROOT / 'os/deskflow-rpm.sh', DIGEST, mode],
                cwd=directory, capture_output=True, text=True, timeout=5,
                env=dict(PATH='/usr/bin:/bin', fixture_repo=repo, ambiguous='yes' if ambiguous else 'no',
                         rpm_contents=rpm_contents),
            )
            args = pathlib.Path(directory) / 'download-args'
            return result, args.read_text().split() if args.exists() else []

    def test_normal_resolve_records_and_restricts_the_testing_repo(self):
        result, args = self.resolve('resolve', 'updates-testing')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, f'DESKFLOW_RESOLVED repo=updates-testing nevra={NEVRA} sha256={DIGEST}\n')
        self.assertIn('--enable-repo=updates-testing', args)
        self.assertIn(f'--setopt=updates-testing.includepkgs={NEVRA}', args)
        self.assertIn('--setopt=fedora.excludepkgs=deskflow', args)
        self.assertIn('--setopt=updates.excludepkgs=deskflow', args)
        self.assertEqual(args[-2:], ['libportal', NEVRA])

    def test_stable_mode_downloads_only_the_updates_pin(self):
        for mode in ('resolve', 'resolve-deskflow-stable'):
            with self.subTest(mode=mode):
                result, args = self.resolve(mode, 'updates')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, f'DESKFLOW_RESOLVED repo=updates nevra={NEVRA} sha256={DIGEST}\n')
                self.assertIn('--setopt=fedora.excludepkgs=deskflow', args)
                self.assertNotIn('--enable-repo=updates-testing', args)

    def test_stable_mode_rejects_fedora_base_and_testing(self):
        for repo in ('fedora', 'updates-testing'):
            with self.subTest(repo=repo):
                result, args = self.resolve('resolve-deskflow-stable', repo)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, '')
                self.assertEqual(args, [])
                self.assertIn('requires Fedora stable updates, found fedora' if repo == 'fedora'
                              else 'Cannot identify one Fedora repository', result.stderr)

    def test_ambiguous_provenance_and_wrong_hash_never_print_a_receipt(self):
        result, args = self.resolve('resolve', 'updates', ambiguous=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, '')
        self.assertEqual(args, [])
        result, args = self.resolve('resolve-deskflow-stable', 'updates', rpm_contents='wrong bytes')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, '')
        self.assertIn('download', args)
