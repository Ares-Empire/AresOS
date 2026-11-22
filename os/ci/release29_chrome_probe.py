"""C6 first use in the R29 guest. Submitted after release29_probes.DESKTOP_ENV."""

import hashlib
import json
import shutil
import stat
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Page(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def parse_request(self):
        parsed = super().parse_request()
        if parsed:
            self.server.arrivals.append(self.path)
        return parsed

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<title>R29 rehearsal</title>')


def cli(daily_command, verb, arguments):
    result = subprocess.run(daily_command + ['/usr/bin/aresos', 'chrome', verb, '--input', json.dumps(arguments)],
                            cwd=HOME, capture_output=True, text=True, timeout=20)
    try:
        reply = json.loads(result.stdout)
    except ValueError:
        reply = None
    return dict(status=result.returncode, reply=reply, stderr=result.stderr[-1000:])


def error_code(result):
    reply = result['reply'] or {}
    return reply.get('error', {}).get('code') if result['status'] != 0 and reply.get('ok') is False else None


def run(out, live, staged, expected, refusals, placeholder, contents):
    assert os.getuid() == 0 and active_vt() == 'tty1', 'C6 requires root and the daily desktop on tty1'
    info = live.lstat()
    assert stat.S_ISREG(info.st_mode) and (info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode)) == (0, 250, 0o640)
    assert live.read_bytes() == placeholder, 'C6 must start with the closed placeholder'
    env = supervisor()
    daily_command = daily(env)
    unit = 'app-aresos-browser-r29-probe.scope'
    definition = json.loads(pathlib.Path('/usr/share/aresos/apps/browser.json').read_bytes())
    profile = tempfile.mkdtemp(prefix='aresos-r29-chrome-', dir=RUNTIME)
    browser = None
    try:
        os.chown(profile, 1001, 1001, follow_symlinks=False)
        log = pathlib.Path('/run/aresos-r29-chrome.log')
        with log.open('wb') as stream:
            browser = subprocess.Popen(daily_command + [
                '/usr/bin/systemd-run', '--user', '--scope', '--collect', '--slice=app.slice',
                '--unit=' + unit, '--expand-environment=no', '--',
                *definition['argv'], '--no-first-run', '--no-default-browser-check', '--password-store=basic',
                '--user-data-dir=' + profile, 'about:blank'],
                cwd=HOME, stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        # Until the policy-installed native host connects, tabs reports chrome_unavailable.
        # The settings refusal is the readiness signal from the shipped service.
        deadline = time.monotonic() + 150
        while True:
            assert browser.poll() is None, 'Chrome left the daily session before connecting'
            result = cli(daily_command, 'tabs', {})
            out['connection'] = result
            code = error_code(result)
            if code == refusals['tabs']:
                break
            assert code == 'chrome_unavailable' and time.monotonic() < deadline, 'Chrome did not reach the closed settings gate'
            time.sleep(1)

        with ThreadingHTTPServer(('127.0.0.1', 0), Page) as pages:
            pages.arrivals = []
            serving = threading.Thread(target=pages.serve_forever, daemon=True)
            serving.start()
            try:
                address = f'http://127.0.0.1:{pages.server_port}'
                # A separate HTTP client proves that the counter sees requests before
                # the four Chrome calls. The page starts the gate check with zero hits.
                import urllib.request
                with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(address + '/ready', timeout=5) as response:
                    assert response.status == 200 and response.read() == b'<title>R29 rehearsal</title>'
                assert pages.arrivals == ['/ready']
                pages.arrivals.clear()
                calls = {'tabs': {}, 'read': {'tab': 1}, 'open': {'url': address + '/closed'}, 'take_tab': {'tab': 1}}
                for verb, arguments in calls.items():
                    result = cli(daily_command, verb, arguments)
                    out['calls'][verb] = result
                    out['refusals'][verb] = error_code(result)
                time.sleep(2)
                out['page_server_hits'] = len(pages.arrivals)
                assert out['refusals'] == refusals and not pages.arrivals, 'C6 closed-gate refusals or zero-request check failed'
                out['first_use'] = 'CONTROL_CHROME_SITES_FIRST_USE_PASS'

                # Check the staged bytes against the independent R28 root read before
                # feeding them to tee. The existing file retains its root-owned metadata.
                data = staged.read_bytes()
                assert data == contents and hashlib.sha256(data).hexdigest() == expected, 'staged Chrome sites changed'
                assert live.read_bytes() == placeholder, 'the closed placeholder changed during C6'
                subprocess.run(['/usr/bin/tee', str(live)], input=data, stdout=subprocess.DEVNULL,
                               stderr=subprocess.PIPE, timeout=20, check=True)
                result = cli(daily_command, 'tabs', {})
                out['after_write'] = result
                out['opened'] = result['status'] == 0 and (result['reply'] or {}).get('ok') is True
                assert out['opened'], 'Chrome tabs did not open after writing the format-1 list'
                staged.unlink()
            finally:
                pages.shutdown()
                serving.join(timeout=5)
    finally:
        try:
            if browser is not None:
                stopped = subprocess.run(daily_command + ['/usr/bin/systemctl', '--user', 'stop', unit],
                                         cwd=HOME, capture_output=True, text=True, timeout=30)
                out['cleanup'] = dict(status=stopped.returncode, stderr=stopped.stderr[-1000:])
                browser.wait(timeout=30)
                assert stopped.returncode == 0, 'failed to stop the disposable Chrome scope'
        finally:
            if browser is not None:
                out['chrome_log'] = log.read_bytes()[-4000:].decode(errors='replace')
            if browser is None or browser.poll() is not None:
                shutil.rmtree(profile)


def main(live, staged, expected, refusals, placeholder, contents):
    result = dict(calls={}, refusals={}, opened=False)
    try:
        run(result, pathlib.Path(live), pathlib.Path(staged), expected, refusals, placeholder, contents)
    except Exception as error:
        result['error'] = f'{type(error).__name__}: {error}'
    print(json.dumps(result))
