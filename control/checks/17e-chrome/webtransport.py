"""Reuse 17d's HTTP/3 receiver, retaining only synthetic IDs and payload hashes."""
import asyncio
import hashlib
import pathlib
import urllib.parse

source_path = pathlib.Path(__file__).parent.parent/'17b-chrome/webtransport.py'
source = source_path.read_text()
assert source.count('asyncio.run(main())') == 1
exec(compile(source.replace('asyncio.run(main())', ''), str(source_path), 'exec'), globals())
original_record = record


def record(kind, **fields):
    if 'body' in fields:
        body = fields.pop('body').encode()
        fields.update(length=len(body), sha256=hashlib.sha256(body).hexdigest())
    if 'headers' in fields:
        headers = fields.pop('headers')
        fields['case'] = urllib.parse.parse_qs(urllib.parse.urlsplit(headers.get(':path', '')).query).get('case', [''])[0]
    original_record(kind, **fields)


asyncio.run(main())
