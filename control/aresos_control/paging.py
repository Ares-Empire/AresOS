"""Bound every cursor to the exact ordered set it was issued for."""
import base64
import hashlib
import heapq
import json
import math

from .common import Refused, canonical, digest

CHANGED = 'Page changed; restarted from the first page.'


def sequence_token(scope, values):
    hashed = hashlib.sha256(canonical(scope).encode())
    for value in values:
        hashed.update(canonical(value).encode())
        hashed.update(b'\n')
    return hashed.hexdigest()


def position(token, cursor, decode=int):
    if cursor is None:
        return None, {}
    try:
        version, raw = cursor.split(':')
        after = decode(raw)
    except (ValueError, TypeError, AttributeError) as exc:
        raise Refused('stale_reference', 'Invalid page cursor; read again without it.') from exc
    if version != token:
        return None, {'page_changed': CHANGED}
    return after, {}


def ordered_page(rows, args=None, scope='', limit=5, newest=False):
    """Rows is a repeatable iterator of (creation/id ordering key, value).

    A commutative digest binds both ordering and contents without holding the
    catalogue in memory. Selection holds at most limit+1 rows, even at 10k.
    """
    args = args or {}
    total, checksum = 0, 0
    for key, value in rows():
        total += 1
        checksum = (checksum + int(hashlib.sha256(canonical([key, value]).encode()).hexdigest(), 16)) % (1 << 256)
    token = digest([scope, total, checksum])
    def decode(raw):
        value = json.loads(base64.urlsafe_b64decode(raw))
        if (not isinstance(value, list) or len(value) != 2 or
                type(value[0]) not in (int, float) or type(value[0]) is float and not math.isfinite(value[0]) or
                type(value[1]) not in (str, int)):
            raise ValueError()
        return tuple(value)
    after, status = position(token, args.get('cursor'), decode)
    limit = args.get('limit', limit)
    def candidates():
        for key, value in rows():
            try:
                include = after is None or (key < after if newest else key > after)
            except TypeError as exc:
                raise Refused('stale_reference', 'Invalid page cursor; read again without it.') from exc
            if include:
                yield key, value
    select = heapq.nlargest if newest else heapq.nsmallest
    selected = select(limit + 1, candidates(), key=lambda row: row[0])
    if total and not selected and after is not None:
        # A syntactically valid forged/out-of-range position cannot hide a set.
        return ordered_page(rows, {k: v for k, v in args.items() if k != 'cursor'}, scope, limit, newest) | {'page_changed': CHANGED}
    cursor = None
    if len(selected) > limit:
        cursor = token + ':' + base64.urlsafe_b64encode(canonical(selected[limit - 1][0]).encode()).decode()
    return {'items': [value for _, value in selected[:limit]], 'total': total, 'cursor': cursor, **status}


def fragment_window(token, total, cursor=None, limit=6000):
    after, status = position(token, cursor)
    offset = after if after is not None else 0
    if not 0 <= offset < total:
        offset, status = 0, {'page_changed': CHANGED}
    end = min(offset + limit, total)
    return offset, end, (f'{token}:{end}' if end < total else None), status
