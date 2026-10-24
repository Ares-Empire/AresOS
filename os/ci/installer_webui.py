"""Drive the pinned ISO's unmodified installer pages through a TCP relay."""
import json
import hashlib
import pathlib
import re
import shlex
import time

UI_BUNDLE_SHA256 = '9e456995a4be3d09b2b81b7e55f363d09577e688b8361d90081e1484cfb4f449'
UI_SOURCE_MAP_SHA256 = 'de301b46d770b5ce75ee3b00be8416c5b8de1a5348dfe0c4ab282f8e8b3ef36a'


def completion_selectors(sources):
    progress = sources['components/installation/InstallationProgress.jsx']
    error = sources['components/Error.jsx']
    footer = sources['components/AnacondaWizardFooter.jsx']
    assert 'const SCREEN_ID = "anaconda-screen-progress";' in progress
    assert 'className={SCREEN_ID + "-status " + SCREEN_ID + "-status-" + status}' in progress
    assert 'setStatus("success")' in progress and 'setStatus("danger")' in progress
    assert 'const idPrefix = "critical-error";' in error
    assert 'id={idPrefix + "-bz-report-modal"}' in error
    assert 'id="installation-next-btn"' in footer
    return dict(success='.anaconda-screen-progress-status-success',
                failure='.anaconda-screen-progress-status-danger',
                critical='#critical-error-bz-report-modal', next='#installation-next-btn')


# This runs only in the disposable live guest. It preserves HTTP and WebSocket
# bytes and leaves Anaconda's own loopback listener/configuration untouched.
RELAY = '''import socket, socketserver, select
class Forward(socketserver.BaseRequestHandler):
    def handle(self):
        with socket.create_connection(('127.0.0.1', 80)) as remote:
            peers = [self.request, remote]
            while True:
                ready, _, _ = select.select(peers, [], [], 60)
                for source in ready:
                    data = source.recv(65536)
                    if not data:
                        return
                    (remote if source is self.request else self.request).sendall(data)
class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
Server(('0.0.0.0', 8080), Forward).serve_forever()
'''


def validate_review(tables, protected, target):
    assert [table['disk'] for table in tables] == [target], 'PRODUCT FAILURE: review includes a wrong/shared disk'
    rows = tables[0]['rows']
    assert rows, 'Missing storage review rows'
    for row in rows:
        assert not re.search(rf'(?<![a-z0-9]){re.escape(protected)}(?:\d+)?(?![a-z0-9])', row['device']), 'PRODUCT FAILURE: protected device in review'
        devices = re.findall(r'\bvd[a-z]\d*\b', row['device'])
        assert devices and all(re.fullmatch(re.escape(target) + r'\d*', device) for device in devices), 'Unresolved review device'
    esp, = [row for row in rows if row['mount'] == '/boot/efi']
    assert re.fullmatch(re.escape(target) + r'\d+', esp['device']), 'PRODUCT FAILURE: EFI is not on a new target partition'
    assert esp['action'] in ('format as efi', 'format as vfat'), 'PRODUCT FAILURE: existing/shared EFI reuse in review'
    assert any(row['mount'] == '/' for row in rows), 'Missing root storage in review'
    assert any(row['mount'] == '/boot' for row in rows), 'Missing boot storage in review'
    return dict(target=target, protected=protected, new_target_efi=esp, tables=tables)


def validate_keyboard_selection(text):
    assert text.split() == ['de'], 'German must be the only selected keyboard'


def validate_keyboard_proof(proof):
    assert proof['xlayouts'] == ['de'] and proof['model_keymap'] in ('', 'de')
    assert proof['read_only'] and proof['same_installation_resolver']
    assert proof['module_configuration_unchanged'] and proof['module_before'] == proof['module_after']
    assert proof['layout_switching_options'] == proof['module_before']['LayoutSwitchingOptions']


def read_keyboard(guest):
    from switch_vm import framed
    receipt = json.loads(pathlib.Path('evidence/installer/localization-source.json').read_text())
    live = next(i for i in json.loads(pathlib.Path('os/manifest/installer-isos.json').read_text()) if i['kind'] == 'live')
    assert receipt['iso_sha256'] == live['sha256']
    expected, = [item['sha256'] for item in receipt['sources'] if item['path'].endswith('/installation.py')]
    script = pathlib.Path('os/ci/keyboard_proof.py').read_text()
    script += '\nprint(json.dumps(read_only_proof(' + repr(expected) + ')))\n'
    proof = guest.capture_json('webui-keyboard-proof', framed('python3 -c ' + shlex.quote(script)))
    validate_keyboard_proof(proof)
    assert proof['installation_source_sha256'] == expected
    return proof


def start(guest, stage):
    import base64
    guest.command(stage + '-launcher', '''set -e
for n in {1..120}; do
    uid=$(id -u liveuser)
    if runuser -u liveuser -- env XDG_RUNTIME_DIR="/run/user/$uid" DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$uid/bus" systemctl --user show-environment | grep -Eq '^(WAYLAND_DISPLAY|DISPLAY)='; then break; fi
    sleep 1
done
runuser -u liveuser -- env XDG_RUNTIME_DIR="/run/user/$uid" DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$uid/bus" bash -c '
while IFS= read -r entry; do export "$entry"; done < <(systemctl --user show-environment)
exec liveinst' > /tmp/rehearsal-webui-launch.log 2>&1 < /dev/null &
echo LIVEUSER_LIVEINST_LAUNCHED
''')
    guest.command(stage + '-server', '''set -e
readiness_deadline=$((SECONDS + 180))
while test "$SECONDS" -lt "$readiness_deadline"; do
    if test -e /run/anaconda/backend_ready && curl --connect-timeout 1 --max-time 2 --fail --silent http://127.0.0.1/cockpit/@localhost/anaconda-webui/index.html > /tmp/rehearsal-index.html; then break; fi
    sleep 1
done
test -s /tmp/rehearsal-index.html
test -e /run/anaconda/backend_ready
echo PINNED_WEBUI_HTTP_READY
cat /usr/libexec/anaconda/webui-desktop
systemctl --no-pager cat webui-cockpit-ws
cat /usr/libexec/anaconda/cockpit-coproc-wrapper.sh
ss -lntp
cat /tmp/rehearsal-webui-launch.log
''', timeout=240)
    guest.command(stage + '-single-browser', '''set -e
python3 - <<'PY'
import os, pathlib, pwd, signal, time
uid = pwd.getpwnam('liveuser').pw_uid
profile = '/run/user/' + str(uid) + '/anaconda/firefox-profile'
def browsers():
    matches = []
    for path in pathlib.Path('/proc').glob('[0-9]*/cmdline'):
        try:
            args = path.read_bytes().split(b'\\0')
            if path.stat().st_uid == uid and b'--profile' in args and profile.encode() in args and b'firefox' in args[0]:
                matches.append(int(path.parent.name))
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            pass
    return matches
deadline = time.monotonic() + 60
while not browsers() and time.monotonic() < deadline:
    time.sleep(1)
pids = browsers()
assert len(pids) == 1, 'Expected exactly the liveinst Firefox profile: ' + repr(pids)
print('PAUSING_LIVEINST_FIREFOX_TREE', pids, profile, flush=True)
# Anaconda watches browser exit and tears down its runtime configuration.
# Pause this browser's entire process tree instead, including JS renderers.
paused = set(pids)
os.kill(pids[0], signal.SIGSTOP)
for attempt in range(5):
    found = set(paused)
    for status in pathlib.Path('/proc').glob('[0-9]*/status'):
        try:
            fields = dict(line.split(':', 1) for line in status.read_text().splitlines() if ':' in line)
            if int(fields['PPid']) in paused and int(fields['Uid'].split()[0]) == uid:
                found.add(int(status.parent.name))
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            pass
    for pid in found:
        os.kill(pid, signal.SIGSTOP)
    if found == paused:
        break
    paused = found
else:
    raise AssertionError('Firefox process tree did not stabilize')
time.sleep(0.2)
for pid in paused:
    status = pathlib.Path('/proc/' + str(pid) + '/status').read_text()
    assert any(line.startswith('State:') and 'T (stopped)' in line for line in status.splitlines()), 'Browser process not paused'
print('PAUSED_BROWSER_PROCESSES', sorted(paused))
PY
test -e /run/anaconda/backend_ready
curl --connect-timeout 1 --max-time 5 --fail --silent http://127.0.0.1/cockpit/@localhost/anaconda-webui/index.html > /dev/null
echo SINGLE_HOST_UI_CLIENT_BACKEND_STILL_READY
''', timeout=90)
    encoded = base64.b64encode(RELAY.encode()).decode()
    guest.command(stage + '-relay', f"set -e; printf '%s' '{encoded}' | base64 -d > /tmp/rehearsal-relay.py\npython3 /tmp/rehearsal-relay.py > /tmp/rehearsal-relay.log 2>&1 < /dev/null &\nsleep 1\ncurl --connect-timeout 1 --max-time 5 --fail --silent http://127.0.0.1:8080/cockpit/@localhost/anaconda-webui/index.html > /dev/null\nss -lntp")
    guest.command(stage + '-bootloader-console-source', '''set -e
cat /proc/cmdline
python3 - <<'PY'
import configparser, hashlib, importlib.util, pathlib, re
spec = importlib.util.find_spec('pyanaconda')
root = pathlib.Path(next(iter(spec.submodule_search_locations)))
paths = list((root / 'modules/storage/bootloader').rglob('*.py'))
assert paths, 'Pinned installer bootloader source unavailable'
for path in paths:
    text = path.read_text()
    lines = text.splitlines()
    selected = {i for i, line in enumerate(lines) if re.search(r'console|preserv.*arg|cmdline', line, re.I)}
    if selected:
        print(str(path), 'SHA256', hashlib.sha256(path.read_bytes()).hexdigest())
        indexes = sorted({j for i in selected for j in range(max(0, i-3), min(len(lines), i+5))})
        for i in indexes:
            print(str(i+1) + ': ' + lines[i])
config = configparser.ConfigParser(interpolation=None, strict=False)
config.read('/run/anaconda/anaconda.conf')
print('ACTUAL BOOTLOADER CONFIG', {key: value for key, value in config['Bootloader'].items() if 'password' not in key})
PY
''')


class Pages:
    def __init__(self, browser, evidence, secrets=(), guest=None):
        self.page = browser.new_page(viewport=dict(width=1440, height=1100))
        self.page.set_default_timeout(60000)
        self.evidence = pathlib.Path(evidence)
        self.events = []
        self.secrets = secrets
        self.guest = guest
        self.page.on('pageerror', lambda error: self.events.append(str(error)))
        self.page.on('console', lambda message: self.events.append(message.type + ': ' + message.text))
        self.frame = self.page

    def snapshot(self, name):
        self.page.screenshot(path=str(self.evidence / (name + '.png')), full_page=True)
        frames = []
        for frame in self.page.frames:
            frames.append(dict(url=frame.url, text=frame.locator('body').inner_text(),
                ids=frame.locator('[id]').evaluate_all('els => els.map(e => ({tag:e.tagName,id:e.id,role:e.getAttribute("role")}))'),
                controls=frame.locator('input,button,select,[role=button]').evaluate_all(
                    "els => els.map(e => ({tag:e.tagName,id:e.id,type:e.type,text:e.textContent,name:e.name,checked:e.checked,disabled:e.disabled,ariaDisabled:e.getAttribute('aria-disabled')}))")))
        (self.evidence / (name + '.json')).write_text(json.dumps(frames, indent=2) + '\n')
        (self.evidence / (name + '.txt')).write_text('\n\n'.join(f['text'] for f in frames))
        from switch_vm import redact
        (self.evidence / 'browser-console.json').write_text(json.dumps([redact(event, self.secrets) for event in self.events], indent=2) + '\n')

    def open(self):
        self.page.goto('http://127.0.0.1:18080/cockpit/@localhost/anaconda-webui/index.html#/anaconda-screen-language', wait_until='domcontentloaded')
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            for frame in self.page.frames:
                if frame.locator('#installation-next-btn').count():
                    self.frame = frame
                    return
            time.sleep(1)
        self.snapshot('webui-not-ready')
        raise RuntimeError('Actual Anaconda Web UI never exposed its navigation control')

    def next(self):
        button = self.frame.locator('#installation-next-btn')
        assert 'install' not in button.inner_text().lower(), 'Probe cannot invoke installation'
        old = self.frame.url
        button.click()
        self.frame.wait_for_function('(old) => location.href !== old', arg=old)

    def localization(self):
        step = 'anaconda-screen-language'
        modal = step + '-change-system-keyboard-layout-modal'
        self.frame.locator('#' + modal + '-open-button').click()
        self.snapshot('keyboard-modal-before')
        self.frame.locator('.' + step + '-keyboard-search input').fill('German')
        self.frame.locator('[id*="-keyboard-option-"][id$="-de"]:visible').first.click()
        # Newer versions can retain several layouts. Remove the initial US
        # entry if that actual control exists, so German is the sole layout.
        listing = self.frame.locator('#' + modal + '-list')
        if listing.count() and re.search(r'\bus\b', listing.inner_text()):
            self.frame.locator('#' + modal + '-remove-0').click()
        from playwright.sync_api import expect
        expect(listing).to_have_text('de')
        validate_keyboard_selection(listing.inner_text())
        self.snapshot('keyboard-german-selected')
        self.frame.locator('#' + modal + '-save-button').click()
        expect(self.frame.locator('#' + modal)).not_to_be_visible()
        # The shipped dialog closes without awaiting handleSaved. Wait for
        # the real async backend commit before leaving this page.
        self.guest.command('keyboard-save-committed', '''set -e
python3 - <<'PY'
import pathlib, subprocess, time
address = pathlib.Path('/run/anaconda/bus.address').read_text().strip()
service = 'org.fedoraproject.Anaconda.Modules.Localization'
deadline = time.monotonic() + 60
stable = 0
while time.monotonic() < deadline:
    value = subprocess.check_output(['busctl', '--address=' + address, 'get-property', service,
        '/org/fedoraproject/Anaconda/Modules/Localization', service, 'XLayouts'], text=True).strip()
    stable = stable + 1 if value == 'as 1 "de"' else 0
    if stable >= 5:
        print('UI_SAVE_COMMITTED', value)
        break
    time.sleep(1)
else:
    raise AssertionError('UI keyboard save did not stabilize at German: ' + repr(value))
PY
''', timeout=90)
        self.snapshot('keyboard-save-committed')

    def timezone(self):
        step = 'anaconda-screen-date-time'
        automatic = self.frame.locator('#' + step + '-auto-timezone')
        if automatic.count():
            automatic.set_checked(False)
        for field, value in [('region', 'Europe'), ('city', 'Berlin')]:
            self.frame.locator('#' + step + '-' + field + '-toggle').click()
            self.frame.locator('#' + step + '-' + field).get_by_text(value, exact=True).click()

    def destination(self, protected, target, configure=False):
        self.open()
        for index in range(8):
            self.snapshot(f'page-{index:02d}')
            if self.frame.locator('#anaconda-screen-method-change-destination-button').is_visible():
                break
            language = self.frame.url.endswith('/anaconda-screen-language')
            if configure:
                if language:
                    self.localization()
                elif self.frame.url.endswith('/anaconda-screen-date-time'):
                    self.timezone()
            self.next()
            if configure and language:
                read_keyboard(self.guest)
        else:
            raise RuntimeError('Destination was not reached through the real pages')
        self.frame.locator('#anaconda-screen-method-change-destination-button').click()
        self.snapshot('destination-all-disks')
        for disk, selected in ((protected, False), (target, True)):
            self.frame.locator(f'#anaconda-screen-method-disk-selection-menu-item-{disk} input[type=checkbox]').set_checked(selected)
        self.snapshot('destination-selection-before-confirming')
        self.frame.locator('#anaconda-screen-method-change-destination-modal').get_by_role('button', name='Select', exact=True).click()
        from playwright.sync_api import expect
        expect(self.frame.locator(f'#anaconda-screen-method-target-disk-{protected}')).to_have_count(0)
        self.frame.locator(f'#anaconda-screen-method-target-disk-{target}').wait_for()
        # First probe records the exact pinned UI controls before choosing a scenario.
        self.snapshot('destination-target-only')

    def review(self, protected, target, password):
        self.destination(protected, target, configure=True)
        scenario = self.frame.locator('#anaconda-screen-method-scenario-erase-all')
        scenario.wait_for(timeout=180000)
        scenario.check()
        self.snapshot('destination-entire-target')
        self.next()
        for index in range(8):
            self.snapshot(f'configuration-{index:02d}')
            if self.frame.url.endswith('/anaconda-screen-review'):
                break
            if self.frame.url.endswith('/anaconda-screen-storage-configuration'):
                self.frame.locator('#disk-encryption-encrypt-devices').set_checked(False)
            elif self.frame.url.endswith('/anaconda-screen-accounts'):
                prefix = '#anaconda-screen-accounts-create-account'
                # Full-name blur asynchronously guesses a username only when
                # that field is empty. Set the explicit recovery name first.
                self.frame.locator(prefix + '-user-name').fill('ares-recovery')
                self.frame.locator(prefix + '-full-name').fill('Ares recovery')
                self.frame.locator(prefix + '-password-field').fill(password)
                self.frame.locator(prefix + '-password-confirm-field').fill(password)
                root = self.frame.locator('#anaconda-screen-accounts-root-account-enable-root-account')
                if root.count():
                    root.set_checked(False)
            else:
                raise RuntimeError('Unqualified pre-install page: ' + self.frame.url)
            self.snapshot(f'configuration-{index:02d}-answered')
            self.next()
        else:
            raise RuntimeError('Review not reached')
        table = self.frame.locator(f'#storage-review-table-{target}')
        table.wait_for()
        self.frame.wait_for_function('''selector => [...document.querySelectorAll(selector + ' tbody tr')]
            .some(row => row.cells[4]?.innerText.trim() === '/boot/efi')''', arg=f'#storage-review-table-{target}')
        tables = self.frame.locator('table[id^="storage-review-table-"]').evaluate_all('''els => els.map(table => ({
            disk: table.id.replace('storage-review-table-', ''),
            text: table.innerText,
            rows: [...table.querySelectorAll('tbody tr')].map(row => ({
                device: row.cells[0]?.innerText.trim() || '',
                action: row.cells[2]?.innerText.trim() || '',
                mount: row.cells[4]?.innerText.trim() || ''
            }))
        }))''')
        self.snapshot('review-full')
        proof = validate_review(tables, protected, target)
        table.screenshot(path=str(self.evidence / 'review-storage-table.png'))
        self.snapshot('review-storage-and-efi')
        text = self.frame.locator('body').inner_text()
        assert 'ares-recovery' in text and 'Use entire disk' in text
        confirmation = self.frame.locator('#anaconda-screen-review-next-confirmation-checkbox')
        if confirmation.count():
            confirmation.check()
        button = self.frame.locator('#installation-next-btn')
        assert button.inner_text().strip() == 'Erase data and install'
        button.click(trial=True)
        self.snapshot('review-ready-without-installing')
        (self.evidence / 'review-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
        return proof

    def completion_source(self):
        sources = []
        selectors = None
        for url in self.frame.locator('script[src]').evaluate_all('els => els.map(e => e.src)'):
            response = self.page.request.get(url)
            assert response.ok, 'Unable to inspect the actual installed UI script'
            raw = response.body()
            sources.append(dict(url=url, sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw)))
            if url.endswith('/index.js'):
                assert hashlib.sha256(raw).hexdigest() == UI_BUNDLE_SHA256, 'Served installer bundle changed'
                mapped = self.page.request.get(url + '.map')
                assert mapped.ok, 'Pinned UI source map is unavailable'
                mapping_raw = mapped.body()
                assert hashlib.sha256(mapping_raw).hexdigest() == UI_SOURCE_MAP_SHA256, 'Served UI source map changed'
                mapping = json.loads(mapping_raw)
                application = {name.split('/src/', 1)[1]: content
                               for name, content in zip(mapping['sources'], mapping['sourcesContent'])
                               if '/src/' in name and '/node_modules/' not in name and content is not None}
                selectors = completion_selectors(application)
                sources.append(dict(url=url + '.map', sha256=UI_SOURCE_MAP_SHA256, bytes=len(mapping_raw)))
        assert selectors is not None, 'Actual installer bundle was not inspected'
        self.completion = selectors
        (self.evidence / 'completion-selector-source.json').write_text(json.dumps(dict(sources=sources, selectors=selectors,
            derivation='Exact pinned source map: progress SCREEN_ID + status; critical-error idPrefix + modal suffix'), indent=2) + '\n')

    def install(self, guest, stage):
        assert self.completion, 'Completion controls must be qualified before installation'
        self.frame.locator('#installation-next-btn').click()
        self.snapshot('installation-started')
        deadline = time.monotonic() + 1800
        heartbeat = 0
        while time.monotonic() < deadline:
            guest.writes(stage + '-progress')
            if time.monotonic() >= heartbeat:
                guest.command(stage + '-heartbeat', 'true', timeout=30)
                heartbeat = time.monotonic() + 15
            if self.frame.locator(self.completion['critical']).is_visible() or self.frame.locator(self.completion['failure']).is_visible():
                self.snapshot('installation-error')
                raise RuntimeError('Real Anaconda installer reported failure; STOP')
            if self.frame.locator(self.completion['success']).is_visible():
                self.snapshot('installation-complete')
                return
            time.sleep(5)
        self.snapshot('installation-deadline')
        raise TimeoutError('Installation exceeded its 30-minute bound')


def readback(guest, stage, protected, target):
    # Read the same backend state the page uses, without exporting a password
    # or changing any property. UI choices must survive Next, not just paint.
    read_keyboard(guest)
    script = '''set -e
python3 - <<'PY'
import json, pathlib, subprocess
address = pathlib.Path('/run/anaconda/bus.address').read_text().strip()
prefix = 'org.fedoraproject.Anaconda.Modules.'
def prop(module, object_suffix, interface_suffix, name):
    service = prefix + module
    return subprocess.check_output(['busctl', '--address=' + address, 'get-property', service,
        '/org/fedoraproject/Anaconda/Modules/' + module + object_suffix,
        service + interface_suffix, name], text=True).strip()
selected = prop('Storage', '/DiskSelection', '.DiskSelection', 'SelectedDisks')
assert selected == 'as 1 "@TARGET@"', 'Wrong backend disk selection'
xlayouts = prop('Localization', '', '', 'XLayouts')
keymap = prop('Localization', '', '', 'VirtualConsoleKeymap')
timezone = prop('Timezone', '', '', 'Timezone')
assert xlayouts == 'as 1 "de"' and keymap in ('s ""', 's "de"'), 'Wrong keyboard choices; installed console check follows installation'
assert timezone == 's "Europe/Berlin"', 'Wrong timezone'
users = prop('Users', '', '', 'Users')
assert '"name" s "ares-recovery"' in users and '"wheel"' in users, 'Recovery administrator missing'
assert '"password" s "$' in users and '"is-crypted" b true' in users, 'Recovery account lacks a protected password'
assert prop('Users', '', '', 'IsRootAccountLocked') == 'b true', 'Root is not locked'
print(json.dumps(dict(selected=selected, xlayouts=xlayouts, keymap=keymap,
    timezone=timezone, recovery_admin='ares-recovery', wheel=True, password_set=True, root_locked=True)))
PY
'''.replace('@TARGET@', target)
    return guest.command(stage + '-backend-readback', script)


def run(guest, evidence, protected, target, password, install=False, stage='webui-probe'):
    from playwright.sync_api import sync_playwright
    start(guest, stage)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=['--no-sandbox'])
        (pathlib.Path(evidence) / 'browser-transport.json').write_text(json.dumps(dict(
            browser='Chromium', version=browser.version, headless=True, viewport=dict(width=1440, height=1100),
            launch='liveuser liveinst; no LIVECMD or kickstart',
            guest_browser='Liveinst Firefox starts normally; its exact liveuser installer profile process tree is SIGSTOP-paused because browser exit tears down Anaconda. Only host Chromium drives the pages',
            transport='host loopback:18080 -> QEMU guest:8080 -> TCP relay -> original loopback:80',
            shutdown='root serial poweroff for mandatory offline audit instead of UI reboot'), indent=2) + '\n')
        pages = Pages(browser, evidence, guest.secrets, guest)
        try:
            proof = pages.review(protected, target, password)
            pages.completion_source()
            readback(guest, stage, protected, target)
            guest.command(stage + '-heartbeat', 'true', timeout=30)
            if install:
                pages.install(guest, stage)
            return proof
        finally:
            pages.snapshot('probe-final-page')
            browser.close()


def probe(guest, evidence, protected, target):
    import secrets
    password = secrets.token_hex(24)
    print(f'::add-mask::{password}', flush=True)
    guest.secrets.append(password)
    return run(guest, evidence, protected, target, password)
