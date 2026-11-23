"""Submit a hosted bench run after checking the target branch's release ledger."""
import argparse
import json
import subprocess
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from script import LEDGER, PATH, LedgerRef, refuse_ledger_ref

REPO = 'Ares-Empire/AresOS'


def submit(ref, name):
    if not PATH.fullmatch(name):
        raise ValueError('Invalid bench script path')
    refuse_ledger_ref(ref, json.loads(LEDGER.read_bytes()))
    subprocess.run(['git', 'check-ref-format', f'refs/heads/{ref}'], check=True)
    # A newly managed branch can have its ledger entry before it reaches main.
    # The ledger is public, so this read needs no GitHub credential.
    query = urlencode({'ref': f'refs/heads/{ref}'})
    request = Request(f'https://api.github.com/repos/{REPO}/contents/os/ci/rehearsal-packages.json?{query}',
                      headers={'Accept': 'application/vnd.github.raw+json', 'Cache-Control': 'no-cache'})
    with urlopen(request, timeout=10) as response:
        refuse_ledger_ref(ref, json.load(response))
    subprocess.run(['gh', 'workflow', 'run', 'os-image.yml', '--repo', REPO, '--ref', ref,
                    '-f', 'check_build=bench', '-f', f'bench_script={name}'], check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ref', required=True, help='pushed branch')
    parser.add_argument('script', help='reviews/<package>/bench/<name>.json on that branch')
    args = parser.parse_args()
    try:
        submit(args.ref, args.script)
    except LedgerRef as error:
        raise SystemExit(str(error)) from None
    except (KeyError, OSError, TypeError, ValueError, subprocess.CalledProcessError):
        raise SystemExit('Bench dispatch failed (invalid branch, script or unreadable release ledger)') from None
