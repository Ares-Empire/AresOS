"""Drive the pinned ISO's unmodified installer pages through a TCP relay."""
import json
import hashlib
import pathlib
import re
import time


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
    encoded = base64.b64encode(RELAY.encode()).decode()
    guest.command(stage + '-relay', f"set -e; printf '%s' '{encoded}' | base64 -d > /tmp/rehearsal-relay.py\npython3 /tmp/rehearsal-relay.py > /tmp/rehearsal-relay.log 2>&1 < /dev/null &\nsleep 1\ncurl --connect-timeout 1 --max-time 5 --fail --silent http://127.0.0.1:8080/cockpit/@localhost/anaconda-webui/index.html > /dev/null\nss -lntp")


class Pages:
    def __init__(self, browser, evidence, secrets=()):
        self.page = browser.new_page(viewport=dict(width=1440, height=1100))
        self.page.set_default_timeout(60000)
        self.evidence = pathlib.Path(evidence)
        self.events = []
        self.secrets = secrets
        self.page.on('pageerror', lambda error: self.events.append(str(error)))
        self.page.on('console', lambda message: self.events.append(message.type + ': ' + message.text))
        self.frame = self.page

    def snapshot(self, name):
        self.page.screenshot(path=str(self.evidence / (name + '.png')), full_page=True)
        frames = []
        for frame in self.page.frames:
            frames.append(dict(url=frame.url, text=frame.locator('body').inner_text(),
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
        self.snapshot('keyboard-german-selected')
        self.frame.locator('#' + modal + '-save-button').click()
        from playwright.sync_api import expect
        expect(self.frame.locator('#' + step + '-selected-keyboards')).to_have_text('de')

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
            if configure:
                if self.frame.url.endswith('/anaconda-screen-language'):
                    self.localization()
                elif self.frame.url.endswith('/anaconda-screen-date-time'):
                    self.timezone()
            self.next()
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
                self.frame.locator(prefix + '-full-name').fill('Ares recovery')
                self.frame.locator(prefix + '-user-name').fill('ares-recovery')
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
        table.locator('tr[data-mount="/boot/efi"]').wait_for()
        tables = self.frame.locator('table[id^="storage-review-table-"]').evaluate_all('''els => els.map(table => ({
            disk: table.id.replace('storage-review-table-', ''),
            text: table.innerText,
            rows: [...table.querySelectorAll('tr[data-device]')].map(row => ({
                device: row.getAttribute('data-device'),
                action: row.getAttribute('data-action'),
                mount: row.getAttribute('data-mount') || ''
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
        combined = ''
        for url in self.frame.locator('script[src]').evaluate_all('els => els.map(e => e.src)'):
            response = self.page.request.get(url)
            assert response.ok, 'Unable to inspect the actual installed UI script'
            raw = response.body()
            sources.append(dict(url=url, sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw)))
            combined += raw.decode(errors='replace')
        features = {name: name in combined for name in ('status-success', 'critical-error-bz-report-modal', 'installation-next-btn')}
        (self.evidence / 'completion-selector-source.json').write_text(json.dumps(dict(sources=sources, features=features), indent=2) + '\n')
        assert all(features.values()), 'Completion/error controls are not evidenced by the pinned UI bundle'

    def install(self, guest, stage):
        self.frame.locator('#installation-next-btn').click()
        self.snapshot('installation-started')
        deadline = time.monotonic() + 1800
        heartbeat = 0
        while time.monotonic() < deadline:
            guest.writes(stage + '-progress')
            if time.monotonic() >= heartbeat:
                guest.command(stage + '-heartbeat', 'true', timeout=30)
                heartbeat = time.monotonic() + 15
            if self.frame.locator('#critical-error-bz-report-modal').is_visible() or self.frame.locator('#anaconda-screen-progress-installation-error-dialog').is_visible():
                self.snapshot('installation-error')
                raise RuntimeError('Real Anaconda installer reported failure; STOP')
            if self.frame.locator('.anaconda-screen-progress-status-success').is_visible():
                self.snapshot('installation-complete')
                return
            time.sleep(5)
        self.snapshot('installation-deadline')
        raise TimeoutError('Installation exceeded its 30-minute bound')


def readback(guest, stage, protected, target):
    # Read the same backend state the page uses, without exporting a password
    # or changing any property. UI choices must survive Next, not just paint.
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
assert xlayouts == 'as 1 "de"' and keymap == 's "de"', 'Wrong installed keyboard'
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
            transport='host loopback:18080 -> QEMU guest:8080 -> TCP relay -> original loopback:80',
            shutdown='root serial poweroff for mandatory offline audit instead of UI reboot'), indent=2) + '\n')
        pages = Pages(browser, evidence, guest.secrets)
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
