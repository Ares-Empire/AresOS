"""The runtime that the Chrome tests and the browser harness start Chrome from (#79).

Chrome trusts two qualification histories (aresos_control/chrome/qualification.py):
the shipped copy, chrome/qualification.json in its installed runtime, which it
reads when it starts, and the record held in its store. A held record must
extend the shipped copy; otherwise every call that consults qualification is
refused with qualification_rollback.

The fixtures write held records of their own: synthetic entries for the build
under test, some passing and some failing. The shipped copy in the source tree,
though, gains the data branch's attested entries whenever they are copied to
main, and those may cover this very build. So the fixtures start Chrome from a
fixture runtime instead of the source tree: the source runtime's build identity
beside an empty shipped copy (BASELINE), which every fixture record extends,
the way an image ships its own copy. Chrome's rules are unchanged; only the
baseline it starts from belongs to the fixture.

test_qualification_fixture runs fixture tests over an image whose shipped copy
holds history, shows that they meet qualification_rollback without this
runtime, and checks that the real shipped copy is a record Chrome trusts.
"""
import importlib.util
import json
import os
from pathlib import Path
import tempfile

from aresos_control.chrome import adapter

BASELINE = {'format': 1, 'entries': []}
# The runtime Chrome was imported from, before install() points it elsewhere.
SOURCE = adapter.RUNTIME


def build_identity(runtime):
    """The build Chrome measures for runtime, the way it does: build-id.json when installed, else build.py's hash."""
    installed = Path(runtime)/'chrome'/'build-id.json'
    if installed.exists():
        return json.loads(installed.read_text())['build']
    spec = importlib.util.spec_from_file_location('aresos_chrome_build_fixture', Path(runtime)/'chrome'/'build.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_hash()


def fixture_runtime(directory, *, source=SOURCE, baseline=BASELINE):
    """An installed runtime under directory: source's build identity beside baseline as its shipped copy.

    The runtime's folder is named after the build, so processes of one tree
    share it (a crash test's child starts Chrome from its parent's runtime)
    and a changed tree gets a new one. Use one baseline per directory. Files
    are replaced atomically, and only when their content differs.
    """
    build = build_identity(source)
    runtime = Path(directory)/build
    (runtime/'chrome').mkdir(parents=True, exist_ok=True)
    for name, value in [('build-id.json', {'build': build}), ('qualification.json', baseline)]:
        path = runtime/'chrome'/name
        content = json.dumps(value)
        if path.exists() and path.read_text() == content:
            continue
        descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix='.'+name+'-')
        try:
            with os.fdopen(descriptor, 'w') as stream:
                stream.write(content)
            os.replace(temporary, path)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise
    return runtime


def install(directory):
    """Start every Chrome this process creates from now on from a fixture runtime under directory."""
    adapter.RUNTIME = fixture_runtime(directory)
    return adapter.RUNTIME
