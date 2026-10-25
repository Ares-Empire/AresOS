"""Read committed installer choices; validate the actual installed keyboard files."""
import hashlib
import inspect
import json
import pathlib
import shlex
import subprocess


def module_settings(address):
    service = 'org.fedoraproject.Anaconda.Modules.Localization'
    result = {}
    for name, kind in [('XLayouts', 'as'), ('VirtualConsoleKeymap', 's'),
                       ('LayoutSwitchOptions', 'as')]:
        raw = subprocess.check_output(['busctl', '--address=' + address, 'get-property', service,
            '/org/fedoraproject/Anaconda/Modules/Localization', service, name], text=True).strip()
        parts = shlex.split(raw)
        assert parts[0] == kind, 'Unexpected keyboard property type: ' + name
        if kind == 's':
            assert len(parts) == 2
            result[name] = parts[1]
        else:
            assert int(parts[1]) == len(parts[2:])
            result[name] = parts[2:]
    return result


def read_only_proof(expected_source_sha256, expected_interface_sha256, untrusted_console=False):
    address = pathlib.Path('/run/anaconda/bus.address').read_text().strip()
    before = module_settings(address)
    assert before['XLayouts'] == ['de'], 'Wrong committed German X layout'
    if not untrusted_console:
        assert before['VirtualConsoleKeymap'] in ('', 'de'), 'Wrong explicit console keymap'
    from pyanaconda.modules.localization.installation import KeyboardInstallationTask
    from pyanaconda.modules.localization.localed import LocaledWrapper
    from pyanaconda.modules.localization.localization_interface import LocalizationInterface
    interface_sha = hashlib.sha256(pathlib.Path(inspect.getfile(LocalizationInterface)).read_bytes()).hexdigest()
    assert interface_sha == expected_interface_sha256, 'Localization interface differs from extracted ISO'
    getter = inspect.getsource(LocalizationInterface.LayoutSwitchOptions.fget)
    assert 'return self.implementation.switch_options' in getter, 'Switch-options property no longer names module settings'
    source = inspect.getsource(KeyboardInstallationTask.run)
    source_sha = hashlib.sha256(pathlib.Path(inspect.getfile(KeyboardInstallationTask)).read_bytes()).hexdigest()
    assert source_sha == expected_source_sha256, 'Keyboard installation source differs from extracted ISO'
    same_resolver = 'get_missing_keyboard_configuration(' in source and 'write_vc_configuration(' in source
    assert same_resolver, 'Pinned keyboard installation task changed'
    wrapper = LocaledWrapper()
    live = dict(keymap=wrapper.keymap, layouts_variants=wrapper.get_layouts_variants(), options=wrapper.options)
    after = module_settings(address)
    assert before == after, 'Proof changed the installer choices'
    return dict(xlayouts=before['XLayouts'], model_keymap=before['VirtualConsoleKeymap'],
        layout_switching_options=before['LayoutSwitchOptions'], live_localed=live,
        module_before=before, module_after=after, module_configuration_unchanged=True,
        read_only=True, same_installation_resolver=same_resolver,
        installation_task_source=source, installation_source_sha256=source_sha,
        switch_options_property='LayoutSwitchOptions', interface_source_sha256=interface_sha,
        switch_options_getter_source=getter)


def read_files(root):
    directory = pathlib.Path(root)
    files = {}
    for name in ('etc/vconsole.conf', 'etc/X11/xorg.conf.d/00-keyboard.conf'):
        path = directory / name
        files[name] = path.read_text() if path.is_file() else None
    return dict(root=str(directory), files=files)


def validate_installed_keyboard(record, expected_options):
    files = record['files']
    console = files.get('etc/vconsole.conf')
    x11 = files.get('etc/X11/xorg.conf.d/00-keyboard.conf')
    assert console is not None and x11 is not None, 'PRODUCT FAILURE: installed keyboard file missing'
    assignments = [shlex.split(line, comments=True) for line in console.splitlines()
                   if line.strip().startswith('KEYMAP=')]
    assert assignments == [['KEYMAP=de']], 'PRODUCT FAILURE: installed console is not KEYMAP=de'
    options, layouts = [], []
    for line in x11.splitlines():
        words = shlex.split(line, comments=True)
        if len(words) >= 2 and words[0].lower() == 'option' and words[1].lower() in ('xkblayout', 'xkboptions'):
            assert len(words) == 3, 'PRODUCT FAILURE: malformed installed X11 keyboard option'
            (layouts if words[1].lower() == 'xkblayout' else options).append(words[2])
    assert layouts == ['de'], 'PRODUCT FAILURE: installed X11 layout is not German'
    assert len(options) <= 1, 'PRODUCT FAILURE: ambiguous installed X11 keyboard options'
    observed = options[0].split(',') if options and options[0] else []
    assert observed == expected_options, 'PRODUCT FAILURE: installed X11 options differ from installer module'
    return dict(status='passed', console_keymap='de', x11_layout='de',
                expected_options=expected_options, observed_options=observed)
