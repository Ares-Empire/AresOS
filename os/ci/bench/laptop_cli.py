"""Laptop bench entry point. Workload commands are added by later packages."""
import argparse
import os
from pathlib import Path
import sys

from laptop import Busy, Cancelled, Inputs, UserScopes, Watch, watch_tree
from store import Store
from store_paths import validate_cache


class Bench:
    def __init__(self, inputs, store):
        self.inputs = inputs
        self.store = store

    def run(self, mode, peaks, setup, *, policy=Watch(), scopes=None, graceful=None, env=None,
            use_build_store=False):
        """Set up a phase and run its bounded command."""
        with self.store.phase(peaks, start_check=lambda: self.inputs.require(mode),
                              use_build_store=use_build_store) as phase:
            command = phase.workload(setup(phase))
            status = watch_tree(self.inputs, mode, command.argv, policy=policy,
                                scopes=UserScopes(self.inputs) if scopes is None else scopes,
                                files=command.files, file_limit=command.file_limit, disk_reason=phase.disk_reason,
                                graceful=graceful or (lambda reason: print(f'bench: {reason}', file=sys.stderr)),
                                env={} if env is None else env)
            if status:
                raise RunExit(status)

    def status(self, output):
        usage, kept, active = self.store.status()
        print(f'Bench data: {sum(usage.values()):,} / {self.store.cap:,} bytes allocated', file=output)
        for device, size in sorted(usage.items()):
            print(f'  filesystem {device}: {size:,} bytes', file=output)
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


class RunExit(Exception):
    def __init__(self, status):
        self.status = status


def native():
    home = Path.home().absolute()
    cache = validate_cache(Path(os.environ.get('XDG_CACHE_HOME', home / '.cache')))
    worktree = Path(__file__).resolve().parents[3]
    return Bench(Inputs(home), Store(cache / 'aresos-bench', worktree,
                                    home / '.cache/aresos-dev/client-test.lock'))


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
