"""Reproduce the pinned resolver's options loss without a bus or any host writes."""
import ast
import hashlib
import json
import pathlib
import re
import subprocess
import types
import zipfile
from abc import ABC

ROOT = pathlib.Path.cwd()
RECORDS = ROOT / 'os/manifest/ci/11h'
FOLDER = RECORDS / 'inspect-1'
SOURCE = '6b08aa30251da875481b4af0c646e508d245d935'
ISO = '776b76f3417723440ee1823d79ec02a2c22860df196d219024edb062ad00d8e6'
ARCHIVE = ROOT / 'reviews/11-two-disk-rehearsal/artifacts/11h-inspect-1-two-disk-evidence.zip'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


metadata, = read(FOLDER / 'artifacts.json')['artifacts']
assert metadata['digest'] == 'sha256:' + hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
run = read(FOLDER / 'run.json')
assert run['head_sha'] == SOURCE and run['conclusion'] == 'success'
assert run['display_title'] == 'Two-disk rehearsal (inspect)' and run['event'] == 'workflow_dispatch'
iso = read(FOLDER / 'installer/iso-download.json')
assert iso['downloaded_sha256'] == iso['sha256'] == ISO and iso['bytes'] == 9068650496
receipt = read(FOLDER / 'installer/localization-source.json')
assert receipt['iso_sha256'] == ISO
sources = {}
with zipfile.ZipFile(ARCHIVE) as archive:
    for item in receipt['sources']:
        name = 'installer/' + item['path'].replace('/', '_')
        raw = archive.read(name)
        assert len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256']
        assert (FOLDER / name).read_bytes() == raw, 'Expanded source differs from original artifact'
        sources[item['path'].rsplit('/', 1)[1]] = raw.decode()
assert set(sources) == {'localed.py', 'utils.py', 'installation.py'}
assert next(x['sha256'] for x in receipt['sources'] if x['path'].endswith('/installation.py')) == read(
    ROOT / 'os/manifest/ci/11g/probe-3/two-disk/webui-keyboard-proof.json')['installation_source_sha256']

# Execute the original AST nodes. Only imports, the bus, logging and the plain-layout
# parser/formatter are stubbed. No installer/wrapper method body is rewritten.
namespace = dict(ABC=ABC, log=types.SimpleNamespace(debug=lambda *args: None),
                 DEFAULT_KEYBOARD='us', get_live_keyboard_instance=lambda: None,
                 InvalidLayoutVariantSpec=ValueError)
def parse_plain(value):
    assert value in ('us', 'de'), 'This counterexample exercises plain layouts only'
    return value, ''
def join_plain(layout, variant):
    assert layout in ('us', 'de') and variant == ''
    return layout
namespace.update(parse_layout_variant=parse_plain, join_layout_variant=join_plain)
for name, wanted in [('localed.py', {'LocaledWrapperBase', 'LocaledWrapper'}),
                     ('utils.py', {'get_missing_keyboard_configuration', '_resolve_missing_by_conversion'})]:
    tree = ast.parse(sources[name])
    nodes = [node for node in tree.body if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in wanted]
    assert {node.name for node in nodes} == wanted
    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'pinned-iso/' + name, 'exec'), namespace)


class ImmediateLocaled:
    """Synchronous property storage: no delayed callbacks or external writers."""
    def __init__(self, options):
        self.VConsoleKeymap = 'us'
        self.X11Layout, self.X11Variant, self.X11Options = 'de', '', options
        self.calls = []

    def SetX11Keyboard(self, layout, model, variant, options, convert, interactive):
        self.calls.append(dict(method='SetX11Keyboard', args=[layout, model, variant, options, convert, interactive]))
        self.X11Layout, self.X11Variant, self.X11Options = layout, variant, options
        if convert:
            assert layout == 'de'
            self.VConsoleKeymap = 'de'

    def SetVConsoleKeyboard(self, keymap, toggle, convert, interactive):
        self.calls.append(dict(method='SetVConsoleKeyboard', args=[keymap, toggle, convert, interactive]))
        assert not convert
        self.VConsoleKeymap = keymap


def snapshot(wrapper):
    return [wrapper.keymap, wrapper.get_layouts_variants(), wrapper.options]


cases = []
for options in ('', 'caps:escape'):
    proxy = ImmediateLocaled(options)
    wrapper = namespace['LocaledWrapper'].__new__(namespace['LocaledWrapper'])
    wrapper._localed_proxy = proxy
    before = snapshot(wrapper)
    layouts, keymap = namespace['get_missing_keyboard_configuration'](wrapper, ['de'], '')
    after = snapshot(wrapper)
    assert layouts == ['de'] and keymap == 'de', 'German resolution must still succeed'
    assert [call['method'] for call in proxy.calls] == ['SetX11Keyboard', 'SetX11Keyboard', 'SetVConsoleKeyboard']
    assert proxy.calls[0]['args'] == ['de', 'pc105', '', '', True, False]
    assert proxy.calls[1]['args'] == ['de', 'pc105', '', '', False, False]
    assert proxy.calls[2]['args'] == ['us', '', False, False]
    # Repeated reads model 0..15 seconds with no asynchronous producer. They are
    # counterexample observations, NOT timings from an actual localed or VM run.
    observations = [dict(simulated_elapsed_seconds=n / 2, value=snapshot(wrapper)) for n in range(31)]
    restored = all(item['value'] == before for item in observations)
    assert restored == (options == '')
    cases.append(dict(initial_options=options, before=before, after_immediate=after,
        resolved_layouts=layouts, resolved_keymap=keymap, calls=proxy.calls,
        simulated_observations=observations, exact_tuple_restored=restored))

failure_path = ROOT / 'os/manifest/ci/11g/full-3/two-disk/webui-keyboard-proof.txt'
failure = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', failure_path.read_text(encoding='utf-8'))
assert 'Conversion did not restore live settings' in failure and 'as 1 "de"' in failure
assert not (failure_path.parent / 'webui-keyboard-proof.json').exists()
assert not (FOLDER / 'two-disk').exists(), 'Inspection must not be a VM run'
jobs = read(FOLDER / 'jobs.json')['jobs']
job, = [job for job in jobs if job['conclusion'] != 'skipped']
steps = {step['name']: step['conclusion'] for step in job['steps']}
skipped = [name for name in steps if name in (
    'Create runner-temporary pinned-image credentials',
    'Verify exact private manifest with owner read-only credentials',
    'Qualify the exact pinned layer pull without installing',
    'Prepare disposable file disks and qualify the real live environment')]
assert len(skipped) == 4 and all(steps[name] == 'skipped' for name in skipped)
assert steps['Remove owner registry credentials'] == 'success'
assert read(FOLDER / 'owner-auth-cleanup.json')['removed']
logs_archive = ROOT / 'reviews/11-two-disk-rehearsal/artifacts/11h-inspect-1-workflow-logs.zip'
with zipfile.ZipFile(logs_archive) as logs:
    transcript = '\n'.join(logs.read(name).decode(errors='replace') for name in logs.namelist() if not name.endswith('/'))
assert re.search(r'Ran 162 tests in [0-9.]+s', transcript)
inputs = {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
          for p in [ARCHIVE, logs_archive, FOLDER / 'installer/localization-source.json']}
inputs[str(failure_path.relative_to(ROOT)).replace('\\', '/')] = hashlib.sha256(
    subprocess.check_output(['git', 'show', '2cbbe2f:' + failure_path.relative_to(ROOT).as_posix()])).hexdigest()
inputs['os/ci/installer_webui.py'] = hashlib.sha256(subprocess.check_output([
    'git', 'show', SOURCE + ':os/ci/installer_webui.py'])).hexdigest()
result = dict(status='PLAN-GAP STOP', qualified=False, inspection_run=40099746381, source=SOURCE,
    iso_sha256=ISO, sources=receipt['sources'],
    finding='convert_layouts restores layouts and keymap but never saves/restores X11 options; both SetX11Keyboard calls pass empty options',
    call_semantics='Sequential ordinary proxy calls; no asynchronous restore, polling, or completion callback in these functions',
    synchronous_mock_cases=cases, actual_full_3_cause='unproven: before/after tuples were not exported',
    actual_vm_settle_timings=None, installed_keyboard_evidence=None,
    owner_token_used=False, owner_token_api_calls=0, skipped_steps=skipped,
    native_regressions=162, part_a='not qualified', part_b='untested',
    implementation_after_source_finding='none; stop before settle/installed-target changes or probe/full dispatch', inputs=inputs)
(RECORDS / 'keyboard-source-analysis.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print('PLAN-GAP reproduced from exact ISO AST: German result, original keymap/layout restored, nonempty options lost permanently; no VM or host bus used.')
