"""Decide whether a checks-only run needs package 22c's full ways-back model.

The full exploration (about 963,000 states, 12 to 21 minutes on a hosted runner)
only repeats its last result unless something it depends on changed. So every
checks-only run explores a fixed bounded slice, and the full model runs when its
dependencies differ from the merge base with main (brief 22c, stage 1b, addition 1):

- the owner tools (os/owner-tools/**) and the release scripts (os/release/**);
- the model and every module it imports from os/tests or os/ci, found by reading
  their import statements (also the ones inside functions), recursively;
- the data those modules read: fixtures, release records, any non-Python file
  in os/tests, and this script.

Anything uncertain counts as changed: no merge base, a failing git command, a
module that cannot be parsed. The workflow's full_model input forces the full
model. Prints `scope=full` or `scope=slice` (for $GITHUB_OUTPUT) and the reasons
on stderr. Reads the checkout only; no network, no privilege.
"""
import ast
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
MODEL = 'test_ways_back_model'
MODULE_DIRS = ('os/tests', 'os/ci')
# Data the model's modules read by path (os/tests' fixtures and other non-Python
# files are added in depends()). The model test checks this list against every
# repository file a bounded exploration actually opens.
DATA = ('os/owner-tools/', 'os/release/', 'os/manifest/release.json', 'os/manifest/releases/',
        'os/ci/model_scope.py')


def imported_names(source):
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            yield from (alias.name.split('.')[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module.split('.')[0]


def closure(root=ROOT, start=MODEL):
    """The model's module paths and, recursively, every os/tests or os/ci path its imports can name.

    A name is kept for both folders whether or not the file exists: a deleted
    imported module, or a new file that would shadow an imported name, counts too.
    """
    names, todo = set(), [start]
    while todo:
        name = todo.pop()
        if name in names:
            continue
        names.add(name)
        for folder in MODULE_DIRS:
            path = root / folder / (name + '.py')
            if path.is_file():
                todo.extend(imported_names(path.read_text(encoding='utf-8')))
    return {folder + '/' + name + '.py' for name in names for folder in MODULE_DIRS}


def depends(path, modules):
    return (path in modules or path.startswith(DATA)
            or path.startswith('os/tests/') and not path.endswith('.py'))


def classify(paths, modules):
    """`full` with the dependency paths among `paths`, or `slice` with none."""
    hits = sorted(p for p in paths if depends(p, modules))
    return ('full' if hits else 'slice'), hits


def git(root, *arguments):
    return subprocess.run(['git', '-C', str(root), *arguments], check=True, capture_output=True, text=True).stdout


def changed(root=ROOT, main='origin/main'):
    """Every path that differs between the merge base with main and the checkout (both sides of a rename)."""
    base = git(root, 'merge-base', 'HEAD', main).strip()
    return [p for p in git(root, 'diff', '--name-only', '--no-renames', '-z', base, '--').split('\0') if p]


def decide(force=False, root=ROOT, main='origin/main'):
    if force:
        return 'full', ['forced by the full_model input']
    try:
        scope, hits = classify(changed(root, main), closure(root))
    except Exception as error:  # uncertain counts as changed
        return 'full', ['uncertain: ' + type(error).__name__ + ': ' + str(error).strip()]
    return scope, hits or ['no dependency of the full model changed since the merge base with ' + main]


def main(argv):
    if argv not in ([], ['--force', 'true'], ['--force', 'false'], ['--force', '']):
        raise SystemExit('usage: model_scope.py [--force true|false]')
    scope, reasons = decide(force=argv[1:] == ['true'])
    for reason in reasons:
        print('model scope ' + scope + ': ' + reason, file=sys.stderr)
    print('scope=' + scope)


if __name__ == '__main__':
    main(sys.argv[1:])
