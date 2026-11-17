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

The browser harness (chrome/ci/service.py) starts from harness_shipped() and
harness_record(): the empty baseline and one synthetic entry, except in one
latency leg, which measures a record of realistic size (#79 O2).
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile

from aresos_control.chrome import adapter
from aresos_control.chrome.policy import CORE_GROUPS, HOSTS

BASELINE = {'format': 1, 'entries': []}
# The record is append-only and never trimmed, and every call that consults
# qualification validates it, so one latency leg measures a record this long
# instead of one entry. Several hundred entries: the data branch gathered 8 in
# its first three days (a stable and a beta entry per qualified build).
LATENCY_HISTORY = 300
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


def install(directory, *, baseline=BASELINE):
    """Start every Chrome this process creates from now on from a fixture runtime under directory."""
    adapter.RUNTIME = fixture_runtime(directory, baseline=baseline)
    return adapter.RUNTIME


def history(count):
    """count attested entries of earlier builds, as the data branch gathers them.

    Each earlier build has a stable and a beta entry on the Chrome versions of
    its day. None is for the build under test, so they leave its switches
    alone and add only the cost of a long record.
    """
    entries = []
    for index in range(count):
        channel = ('stable', 'beta')[index % 2]
        major = 120 + index // 40 + (2 if channel == 'beta' else 0)
        entries.append({'build': hashlib.sha256(f'earlier-build-{index // 2}'.encode()).hexdigest(),
                        'version': f'{major}.0.{6000 + index // 2}.{index % 7}', 'channel': channel,
                        'run': str(40000000000 + index // 2),
                        'core': dict.fromkeys(CORE_GROUPS, True), 'adapters': dict.fromkeys(HOSTS, True)})
    return entries


def realistic_leg(environment):
    """The latency leg that measures a long record: the plain profile's current runtime.

    The old runtime keeps one entry, as in the frozen reference, because it
    measures the runner's speed; with the long record too it would read the
    record's cost as runner noise and loosen the ceilings by as much. The
    audit leg stays like for like with the reference.
    """
    return (environment.get('LATENCY_PROBE') == 'true' and environment.get('LATENCY_PRIVACY') == 'plain'
            and environment.get('LATENCY_BASELINE') == 'current'
            and environment.get('EFFICIENCY_PROBE') != 'true')


def harness_shipped(environment):
    """The shipped copy the browser harness installs: history in the realistic leg, else the empty baseline."""
    return {'format': 1, 'entries': history(LATENCY_HISTORY) if realistic_leg(environment) else []}


def harness_record(shipped, build, version):
    """The held record the browser harness writes: the shipped copy plus this build qualified on this Chrome."""
    return {'format': 1, 'entries': [*shipped['entries'], {
        'build': build, 'version': version, 'channel': 'stable', 'run': 'synthetic-fixture-setup',
        'core': dict.fromkeys(CORE_GROUPS, True), 'adapters': dict.fromkeys(HOSTS, True)}]}
