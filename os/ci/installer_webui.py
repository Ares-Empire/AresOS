"""Drive the pinned ISO's unmodified installer pages through a TCP relay."""
import json
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
for n in {1..180}; do
    if test -e /run/anaconda/backend_ready && curl --fail --silent http://127.0.0.1/cockpit/@localhost/anaconda-webui/index.html > /tmp/rehearsal-index.html; then break; fi
    sleep 1
done
test -s /tmp/rehearsal-index.html
test -e /run/anaconda/backend_ready
cat /usr/libexec/anaconda/webui-desktop
systemctl cat webui-cockpit-ws
ss -lntp
cat /tmp/rehearsal-webui-launch.log
''', timeout=240)
    encoded = base64.b64encode(RELAY.encode()).decode()
    guest.command(stage + '-relay', f"set -e; printf '%s' '{encoded}' | base64 -d > /tmp/rehearsal-relay.py\npython3 /tmp/rehearsal-relay.py > /tmp/rehearsal-relay.log 2>&1 < /dev/null &\nsleep 1\ncurl --fail --silent http://127.0.0.1:8080/cockpit/@localhost/anaconda-webui/index.html > /dev/null\nss -lntp")


class Pages:
    def __init__(self, browser, evidence):
        self.page = browser.new_page(viewport=dict(width=1440, height=1100))
        self.page.set_default_timeout(60000)
        self.evidence = pathlib.Path(evidence)
        self.events = []
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
        (self.evidence / 'browser-console.json').write_text(json.dumps(self.events, indent=2) + '\n')

    def open(self):
        self.page.goto('http://127.0.0.1:18080/cockpit/@localhost/anaconda-webui/index.html', wait_until='domcontentloaded')
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

    def destination(self, protected, target):
        self.open()
        for index in range(8):
            self.snapshot(f'page-{index:02d}')
            if self.frame.locator('#anaconda-screen-method-change-destination-button').is_visible():
                break
            self.next()
        else:
            raise RuntimeError('Destination was not reached through the real pages')
        self.frame.locator('#anaconda-screen-method-change-destination-button').click()
        self.snapshot('destination-all-disks')
        for disk, selected in ((protected, False), (target, True)):
            self.frame.locator(f'#anaconda-screen-method-disk-selection-menu-item-{disk} input[type=checkbox]').set_checked(selected)
        self.frame.locator('#anaconda-screen-method-change-destination-modal').get_by_role('button', name='Select', exact=True).click()
        assert not self.frame.locator(f'#anaconda-screen-method-target-disk-{protected}').count()
        self.frame.locator(f'#anaconda-screen-method-target-disk-{target}').wait_for()
        # First probe records the exact pinned UI controls before choosing a scenario.
        self.snapshot('destination-target-only')


def probe(guest, evidence, protected, target):
    from playwright.sync_api import sync_playwright
    start(guest, 'webui-probe')
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=['--no-sandbox'])
        pages = Pages(browser, evidence)
        try:
            pages.destination(protected, target)
        finally:
            pages.snapshot('probe-final-page')
            browser.close()
