"""Disposable aresos-shell/1.2 server shared by the laptop-home tests."""

import json
import math
import socket
import socketserver
import struct
import threading
import time
import zlib


PROTOCOL = 'aresos-shell/1.2'
TOKEN = 'T' * 43
INSTANCE = 'test-instance'
CAPABILITIES = ['views', 'home_state', 'apps_running', 'app_details', 'apps_changed', 'list_apps',
                'list_paging', 'open_app']


def png(width=12, height=12):
    def chunk(name, data):
        return struct.pack('>I', len(data)) + name + data + struct.pack('>I', zlib.crc32(name + data))

    header = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    pixels = (b'\0' + b'\x99\x73\xc2' * width) * height
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header) + chunk(b'IDAT', zlib.compress(pixels))
            + chunk(b'IEND', b''))


def town(count, *, holes=(), unpinned=(), icon=None, streets=None):
    """Generate catalogue and house rows. Removing a house leaves its original place free."""
    groups = ('internet', 'games', 'work_media', 'system_tools')
    kinds = ('Web', 'Game', 'Work', 'Tool')
    directions = 'NEWS'
    houses, programs = [], []
    addresses = ((index % 4, index // 4) for index in range(count)) if streets is None else (
        (street, slot) for street, length in enumerate(streets) for slot in range(length))
    for index, (street, slot) in enumerate(addresses):
        number = slot + 1
        column = slot // 2
        row_index = (math.isqrt(8 * column + 1) - 1) // 2
        side = 'L' if slot % 2 == 0 else 'R'
        place = f'{directions[street]}{row_index}{side}{column - row_index * (row_index + 1) // 2}'
        app_id = f'test-{kinds[street].lower()}-{number}'
        if app_id in holes:
            continue
        row = dict(id=app_id, name=f'Test {kinds[street]} {number}', generic_name='Test Program',
                   keywords=[f'keyword-{index}'], exec_name='native-only', available=True,
                   desktop_id=f'{app_id}.desktop')
        if icon is not None:
            row['icon'] = str(icon)
        programs.append(row)
        if app_id not in unpinned:
            house = dict(id=app_id, short=app_id.removeprefix('test-'), group=groups[street],
                         place=place,
                         cells='.' * 12 + 'abba' * 33)
            if index < 9:
                house['slot'] = index
            houses.append(house)
    return sorted(houses, key=lambda row: row['id']), sorted(programs, key=lambda row: row['id'])


class ViewHandler(socketserver.StreamRequestHandler):
    def handle(self):
        helper = self.server.helper
        with helper.lock:
            helper.peers.add(self)
            helper.connections.append(time.monotonic())
        try:
            for line in self.rfile:
                request = json.loads(line)
                with helper.lock:
                    helper.requests.append(request)
                    helper.answer(self, request)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            with helper.lock:
                helper.peers.discard(self)

    def send(self, **message):
        self.wfile.write(json.dumps(dict(protocol=PROTOCOL, **message)).encode() + b'\n')


class StandIn:
    palette = {'a': '#aabbcc', 'b': '#9933aa'}

    def __init__(self, path, *, count=12, page_size=3, holes=(), unpinned=(), icon=None, streets=None):
        self.path = path
        self.houses, self.programs = town(count, holes=holes, unpinned=unpinned, icon=icon, streets=streets)
        self.revision = '1'
        self.catalogue_revision = 'first'
        self.running = []
        self.page_size = page_size
        self.results = {}
        self.opens, self.requests, self.connections = [], [], []
        self.lock = threading.RLock()
        self.peers = set()
        self.serial = 0
        self.server = None
        self.before_page = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *_):
        self.drop()

    def start(self):
        self.server = socketserver.ThreadingUnixStreamServer(str(self.path), ViewHandler)
        self.server.helper = self
        self.thread = threading.Thread(target=self.server.serve_forever, args=(0.01,), daemon=True)
        self.thread.start()

    def drop(self):
        if self.server is not None:
            self.server.shutdown()
            with self.lock:
                for peer in self.peers:
                    peer.connection.shutdown(socket.SHUT_RDWR)
            self.server.server_close()
            self.thread.join()
            self.path.unlink()
            self.server = None

    def answer(self, peer, request):
        def reply(ok=True, **fields):
            peer.send(id=request['id'], ok=ok, **fields)

        op = request['op']
        if op == 'hello':
            accepted = {'instance': INSTANCE, 'token': TOKEN, 'role': 'view', 'view': 'laptop-home',
                        'protocol': PROTOCOL, 'major': 1, 'minor': 2}
            if not all(request.get(key) == value for key, value in accepted.items()):
                reply(False, error='not_authorized')
                return
            reply(major=1, minor=2, capabilities=CAPABILITIES)
            self.event('apps_running', (peer,), apps=self.running)
        elif op in ('get_home', 'list_apps'):
            if self.before_page is not None:
                self.before_page(request)
            if op == 'get_home':
                rows = self.houses if self.revision is not None else []
                fields = dict(revision=self.revision, palette=self.palette if self.revision is not None else {})
            else:
                rows, fields = self.programs, dict(revision=self.catalogue_revision)
            start = int(request.get('cursor', '0'))
            end = start + self.page_size
            if end < len(rows):
                fields['next'] = str(end)
            reply(apps=rows[start:end], **fields)
        elif op == 'open_app':
            app_id = request['app_id']
            self.opens.append(app_id)
            result = self.results.get(app_id)
            if result is None and not any(row['id'] == app_id for row in self.programs):
                result = dict(ok=False, state='failed', error='unknown_app', message='no reviewed launch definition')
            reply(app_id=app_id, launch_id='test-launch', request_id=request['id'],
                  **(result or {'state': 'starting'}))
        else:
            reply(False, error='invalid_state')

    def event(self, name, peers=None, **fields):
        self.serial += 1
        for peer in self.peers if peers is None else peers:
            try:
                peer.send(id=f'e-{self.serial}', event=name, **fields)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def publish(self, revision, houses):
        with self.lock:
            self.revision, self.houses = revision, houses
            self.event('home_changed', revision=revision)

    def change_catalogue(self, revision, programs, houses):
        with self.lock:
            self.catalogue_revision, self.programs, self.houses = revision, programs, houses
            self.event('apps_changed', revision=revision)

    def set_running(self, ids):
        with self.lock:
            self.running = sorted(ids)
            self.event('apps_running', apps=self.running)
