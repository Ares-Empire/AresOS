"""Run the review's real reader replies through Engine.request, without a browser."""
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

from aresos_control.common import canonical
from test_outline_action import Outlines, engine_with


def run(data):
    browser = Outlines()
    scratch = Path('.work/x1/tmp')
    scratch.mkdir(parents=True, exist_ok=True)
    with patch('aresos_control.engine.Boundary'), tempfile.TemporaryDirectory(dir=scratch) as tmp:
        engine = engine_with(Path(tmp), browser)
        try:
            def snapshot(item):
                frame = {**item['outline'], 'frame': 0}
                browser.outlines[1] = {'session': browser.session, 'tab': 1, 'url': frame['url'],
                                       'title': frame['title'], 'frames': [frame]}
                browser.tokens[1] = canonical(item.get('state', {}))

            def call(**args):
                return engine.request({'v': 1, 'method': 'call', 'action': 'chrome_read',
                                       'arguments': {'tab': 1, **args}})

            if data['mode'] == 'reads':
                snapshot(data)
                return [call(**query) for query in ({}, {'full': True}, {'find': data['needle']})]
            snapshot(data['before'])
            first = call(full=True, max=1000)
            cursor = first['data']['reads'][0]['cursor']
            snapshot(data['after'])
            continued = call(full=True, max=1000, cursor=cursor)
            snapshot(data['before'])
            browser.calls.clear()
            browser.on_state = lambda count: snapshot(data['after']) if count >= 2 else None
            waited = call(until={'text': data['needle']}, timeout_ms=300)
            return {'cursor': cursor, 'continued': continued, 'waited': waited, 'calls': browser.calls}
        finally:
            engine.close()


if __name__ == '__main__':
    print(canonical(run(json.load(sys.stdin))))
