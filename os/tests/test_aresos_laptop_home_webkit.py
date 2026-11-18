"""Bridge, renderer pin and resource policy in the real WebKitGTK view under headless labwc."""

import os
from pathlib import Path
import socketserver
import threading
import time
import unittest

from laptop_home_headless import Headless, VENDORS, engines, headless_available, load_program, scratch, wait_for
from laptop_home_helper import StandIn, png


class Listener(socketserver.BaseRequestHandler):
    def handle(self):
        self.server.connections.append(True)
        self.request.sendall(b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nOK')


@unittest.skipUnless(headless_available(), 'headless labwc, Mesa pins and GTK 4/WebKitGTK 6.0')
class WebKitTest(unittest.TestCase):
    def setUp(self):
        workspace = scratch()
        self.addCleanup(workspace.cleanup)
        self.root = Path(workspace.name)
        icon = self.root / 'icon.png'
        icon.write_bytes(png())
        self.helper = StandIn(self.root / 'shell.sock', icon=icon, count=45,
                             holes=['test-web-2'], unpinned=['test-tool-1'])
        self.chrome = Headless(self.root, self.helper.path)

    def test_bridge_resources_boundary_startup_and_vendor_pin(self):
        self.helper.running = ['test-web-1']
        local_file = self.root / 'private.json'
        local_file.write_text('{"private":true}')
        with socketserver.TCPServer(('127.0.0.1', 0), Listener) as listener, self.helper, self.chrome as gui:
            listener.connections = []
            thread = threading.Thread(target=listener.serve_forever, args=(0.01,), daemon=True)
            thread.start()
            try:
                self.check_bridge(gui, listener.server_address[1], local_file)
                self.assertEqual(listener.connections, [])
            finally:
                listener.shutdown()
                thread.join()

    def check_bridge(self, gui, port, local_file):
        gui.until('window.probe?.events.some(e => e.name === "helper" && e.detail)')
        parent = gui.parent()
        self.assertEqual(parent['before'], [False, False])
        self.assertEqual(parent['after'], [True, True])
        self.assertEqual(parent['pins'], list(VENDORS.values()))
        self.assertTrue(parent['ephemeral'])
        self.assertEqual(parent['app_id'], 'aresos.laptop-home')
        geometry = gui.evaluate('@window')
        self.assertTrue(geometry['visible'])
        if gui.expect_layer:
            self.assertEqual(parent.get('layer'),
                             dict(background=True, on_demand=True, anchored=True, output='HEADLESS-1'))
        else:
            self.assertNotIn('layer', parent)
            self.assertTrue(geometry['fullscreen'])
        processes = wait_for(lambda: (p if {'WebKitWebProcess', 'WebKitNetworkProcess'} <= set(
            (p := engines(parent['pid'])).values()) else None))
        for pid in (parent['pid'], *processes):
            maps = Path(f'/proc/{pid}/maps').read_text()
            self.assertFalse(any('nvidia' in line.lower() for line in maps.splitlines() if '/' in line))
            if pid != parent['pid']:
                environment = Path(f'/proc/{pid}/environ').read_bytes().split(b'\0')
                names = [entry.partition(b'=')[0] for entry in environment]
                self.assertNotIn(b'LD_PRELOAD', names)
                self.assertNotIn(b'ARESOS_VIEW_TOKEN', names)
                self.assertNotIn(b'ARESOS_SHELL_SOCKET', names)
                for name, value in VENDORS.items():
                    self.assertIn(os.fsencode(f'{name}={value}'), environment)

        first = gui.evaluate('return probe.events.slice(0, 5);')
        self.assertEqual([event['name'] for event in first], ['home', 'programs', 'running', 'status', 'helper'])
        self.assertIsNone(first[0]['detail'])
        self.assertEqual(first[2]['detail'], ['test-web-1'])
        self.assertEqual(first[3]['detail'], {'battery': {'level': 68, 'charging': True}})
        self.assertIs(first[4]['detail'], True)

        payloads = gui.evaluate('return [aresosHome.home(), aresosHome.programs(), aresosHome.status()];')
        town, programs, status = payloads
        self.assertEqual(set(town), {'apps', 'palette'})
        self.assertEqual(town['palette'], StandIn.palette)
        self.assertEqual(len(town['apps']), 43)
        self.assertEqual(len(programs), 44)
        web = next(app for app in town['apps'] if app['id'] == 'test-web-1')
        self.assertEqual(set(web), {'id', 'name', 'short', 'group', 'place', 'cells', 'slot'})
        self.assertEqual(web['name'], 'Test Web 1')
        self.assertTrue(all(set(row) == {'id', 'name', 'generic_name', 'keywords', 'has_icon'} for row in programs))
        self.assertEqual(first[1]['detail'], programs)
        self.assertEqual(status, first[3]['detail'])

        self.assertEqual(gui.evaluate('return await probe.load();'),
                         {'item': 'module loaded', 'data': {'loaded': True}, 'type': 'application/json',
                          'image': [12, 12], 'style': 'rgb(34, 51, 68)'})
        if os.environ.get('LAPTOP_HOME_TEST_PSS'):
            time.sleep(8)  # The packaged bridge page is idle during the measurement.
            pss = {}
            for pid, name in [(parent['pid'], 'program'), *processes.items()]:
                lines = Path(f'/proc/{pid}/smaps_rollup').read_text().splitlines()
                pss[name] = int(next(line.split()[1] for line in lines if line.startswith('Pss:')))
            print(f'Pinned bridge fixture PSS in KiB: {pss}, total {sum(pss.values())}')
        self.helper.set_running(['test-work-2'])
        gui.until('probe.events.some(e => e.name === "running" && e.detail.includes("test-work-2"))')
        self.assertEqual(gui.evaluate('return await aresosHome.open("test-web-1");'), {'state': 'starting'})
        self.helper.results['test-web-1'] = dict(ok=False, state='failed', error='unavailable', message='not_installed')
        self.assertEqual(gui.evaluate('return await aresosHome.open("test-web-1");'),
                         {'state': 'failed', 'message': 'not_installed'})
        self.helper.drop()
        gui.until('probe.events.at(-1).name === "helper" && !probe.events.at(-1).detail')
        self.assertEqual(gui.evaluate('return await aresosHome.open("test-web-1");'),
                         {'state': 'failed', 'message': 'Opening is back in a moment'})
        self.helper.revision = None
        self.helper.running = ['test-work-1']
        self.helper.start()
        gui.until('probe.events.at(-1).name === "helper" && probe.events.at(-1).detail')
        self.assertEqual(gui.evaluate('return aresosHome.home();'), town)
        self.assertEqual(gui.evaluate('return probe.events.filter(e => e.name === "running").at(-1).detail;'),
                         ['test-work-1'])

        denied = gui.evaluate(f'''
            const http = "http://127.0.0.1:{port}/";
            const https = "https://127.0.0.1:{port}/";
            const file = "{local_file.as_uri()}";
            const fails = promise => promise.then(() => false, () => true);
            const image = new Image();
            image.src = http + "image";
            const frame = document.createElement("iframe");
            document.body.append(frame);
            const frameHasBridge = typeof frame.contentWindow.aresosHome !== "undefined";
            frame.src = "aresos-home://page/foreign.html";
            return {{
              fetch: await fails(fetch(http)), https: await fails(fetch(https)),
              file: await fails(fetch(file)), image: await fails(image.decode()),
              unknownIcon: await fails(fetch("aresos-home://icon/no-such-app")),
              popup: window.open(http) === null, frame: !frameHasBridge
            }};
        ''')
        self.assertTrue(all(denied.values()), denied)

        for uri in (f'http://127.0.0.1:{port}/', f'https://127.0.0.1:{port}/', local_file.as_uri(),
                    'data:text/html,foreign', 'aresos-home://page/foreign.html'):
            gui.evaluate(f'location.href = {uri!r}; return true;')
            self.assertEqual(gui.evaluate('return location.href;'), 'aresos-home://page/index.html')

        # Allow an unrelated document to commit in the harness, then try both the public and raw bridge.
        gui.evaluate('@foreign')
        gui.until('document.title === "Foreign test document"')
        self.assertEqual(gui.evaluate('''
            const raw = window.webkit.messageHandlers.laptopHome;
            return [
              typeof window.aresosHome,
              await raw.postMessage({op: 'open', id: 'test-web-1'}).then(() => false, () => true)
            ];
        '''), ['undefined', True])
        self.assertEqual(self.helper.opens, ['test-web-1', 'test-web-1'])

    def test_cached_town_comes_up_with_opening_disabled(self):
        program = load_program()
        cached = program.page_home(StandIn.palette, self.helper.houses,
                                   {row['id']: row['name'] for row in self.helper.programs})
        program.save_home(self.chrome.home_path, cached)
        with self.chrome as gui:
            gui.until('window.probe?.events.length >= 5')
            self.assertEqual(gui.evaluate('return aresosHome.home();'), cached)
            self.assertEqual(gui.evaluate('return probe.events.find(e => e.name === "helper").detail;'), False)
            self.assertEqual(gui.evaluate('return await aresosHome.open("test-web-1");'),
                             {'state': 'failed', 'message': 'Opening is back in a moment'})
            self.assertEqual(self.helper.opens, [])
