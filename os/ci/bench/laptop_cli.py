"""Laptop bench entry point. Workload commands are added by later packages."""
import argparse
import os
from pathlib import Path
import pwd
import sys

from egress import REFUSAL, require_laptop_network
from laptop import Busy, Cancelled, Inputs, UserScopes, Watch, log_error, watch_tree
from network import Level
from store import OTHER_EVIDENCE, Store
from store_paths import absolute, validate_cache


class Bench:
    def __init__(self, inputs, store):
        self.inputs = inputs
        self.store = store

    def run(self, mode, peaks, setup, *, policy=Watch(), scopes=None, graceful=None, env=None,
            use_build_store=False, network=Level.NONE):
        """Set up a phase and run its bounded command."""
        require_laptop_network(network)
        with self.store.phase(peaks, start_check=lambda: self.inputs.require(mode),
                              use_build_store=use_build_store) as phase:
            command = phase.workload(setup(phase))
            status = watch_tree(self.inputs, mode, command.argv, policy=policy,
                                scopes=UserScopes(self.inputs) if scopes is None else scopes,
                                files=command.files, file_limit=command.file_limit, disk_reason=phase.disk_reason,
                                before_release=phase.recheck_command_space,
                                graceful=graceful or log_error,
                                env={} if env is None else env)
            if status:
                raise RunExit(status)
            phase.publish_evidence()

    def status(self, output):
        usage, kept, active = self.store.status()
        print(f'Bench data: {sum(usage.values()):,} / {self.store.cap:,} bytes allocated', file=output)
        print(f'  other-worktree evidence allowance: {OTHER_EVIDENCE:,} bytes charged to the cap', file=output)
        for pool, size in sorted(usage.items()):
            print(f'  filesystem pool {pool}: {size:,} bytes', file=output)
        for kind, reason in kept:
            print(f'  kept {kind} ({reason})', file=output)
        if not kept:
            print('  no retained data', file=output)
        if active:
            print('  phase journal present', file=output)
        for mode in ('vm', 'build'):
            for gate, reason in self.inputs.gates(mode).items():
                print(f'  {mode} {gate}: {reason or "ready"}', file=output)
        print(f'  home-screen game: {self.inputs.home_game()}', file=output)
        print(f'  network: {REFUSAL}', file=output)


class RunExit(Exception):
    def __init__(self, status):
        self.status = status


def native(*, worktree=None):
    home = absolute(Path(pwd.getpwuid(os.getuid()).pw_dir))
    if Path(os.environ.get('HOME', home)) != home:
        raise ValueError('HOME must match the account home')
    cache = home / '.cache'
    if Path(os.environ.get('XDG_CACHE_HOME', cache)) != cache:
        raise ValueError('XDG_CACHE_HOME must match the account cache directory')
    validate_cache(cache)
    if worktree is None:
        worktree = Path(__file__).resolve().parents[3]
    return Bench(Inputs(home), Store(cache / 'aresos-bench', worktree,
                                    cache / 'aresos-dev/client-test.lock'))


def main(argv=None, *, bench=None, output=None, errors=None):
    parser = argparse.ArgumentParser(prog='bench', description=__doc__)
    parser.add_argument('command', choices=('status', 'clean'))
    args = parser.parse_args(argv)
    output = sys.stdout if output is None else output
    errors = sys.stderr if errors is None else errors
    try:
        bench = native() if bench is None else bench
        if args.command == 'status':
            bench.status(output)
        else:
            bench.store.clean()
            print('Bench data removed', file=output)
    except Busy as error:
        print(f'bench: {error}', file=errors)
        return 75
    except Cancelled as error:
        print(f'bench: {error}', file=errors)
        return 1
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f'bench: {error}', file=errors)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
