"""Conservative RFC 8058 DKIM gate, using the base's already pinned cryptography.

Only complete SHA-256 signatures, simple/relaxed canonicalization, DNS TXT RSA
(>=1024 bits) or Ed25519 keys. Unsupported/ambiguous signatures fail closed.
DNS is queried only after approval, never while reading incoming mail.
"""
import base64
import hashlib
from pathlib import Path
import re
import secrets
import socket
import struct
import time

from ..common import Refused


def name_at(packet, offset):
    labels, seen, end = [], set(), None
    for _ in range(128):
        if offset in seen or offset >= len(packet):
            raise ValueError('Invalid DNS name')
        seen.add(offset)
        size = packet[offset]
        if size & 0xc0 == 0xc0:
            if end is None:
                end = offset + 2
            offset = ((size & 0x3f) << 8) | packet[offset + 1]
            continue
        if size == 0:
            return b'.'.join(labels).decode('ascii').lower(), end or offset + 1
        if size > 63 or offset + 1 + size > len(packet):
            raise ValueError('Invalid DNS label')
        labels.append(packet[offset + 1:offset + 1 + size])
        offset += size + 1
    raise ValueError('DNS name too deep')


def txt_answer(packet, transaction, query_name):
    ident, flags, questions, answers, authority, extra = struct.unpack('!6H',packet[:12])
    if ident != transaction or flags & 0x8000 == 0 or flags & 0x000f or flags & 0x0200 or questions != 1:
        raise ValueError('DNS response refused/truncated')
    actual,offset = name_at(packet,12)
    kind,klass = struct.unpack('!HH',packet[offset:offset+4])
    if actual != query_name.lower() or (kind,klass) != (16,1):
        raise ValueError('DNS question mismatch')
    offset += 4
    records,aliases = [], {}
    for _ in range(answers):
        name,offset = name_at(packet,offset)
        kind,klass,ttl,length = struct.unpack('!HHIH',packet[offset:offset+10])
        start = offset + 10
        offset = start + length
        if offset > len(packet):
            raise ValueError('Incomplete DNS data')
        if klass != 1:
            continue
        if kind == 5:
            aliases[name] = name_at(packet,start)[0]
        if kind == 16:
            data, index = b'', start
            while index < offset:
                size = packet[index]
                index += 1
                if index + size > offset:
                    raise ValueError('Incomplete TXT')
                data += packet[index:index+size]
                index += size
            records.append((name,data))
    valid = {query_name.lower()}
    for _ in range(8):
        valid |= {v for k,v in aliases.items() if k in valid}
    return [v for k,v in records if k in valid]


def dns_txt(name):
    if len(name) > 253 or not re.fullmatch(r'[A-Za-z0-9_.-]+',name):
        raise ValueError('Invalid DKIM lookup name')
    transaction = secrets.randbelow(65536)
    labels = name.encode('ascii').split(b'.')
    if any(not 0 < len(label) <= 63 for label in labels):
        raise ValueError('Invalid DNS label')
    query = struct.pack('!6H',transaction,0x0100,1,0,0,0) + b''.join(bytes([len(label)]) + label for label in labels) + b'\0' + struct.pack('!HH',16,1)
    resolvers = [line.split()[1] for line in Path('/etc/resolv.conf').read_text().splitlines() if line.startswith('nameserver ')]
    if not resolvers:
        raise ValueError('No system DNS resolver')
    resolver = resolvers[0]
    family = socket.AF_INET6 if ':' in resolver else socket.AF_INET
    with socket.socket(family,socket.SOCK_DGRAM) as sock:
        sock.settimeout(5)
        sock.connect((resolver,53))
        sock.send(query)
        response = sock.recv(65536)
    if len(response) >= 4 and struct.unpack('!H',response[2:4])[0] & 0x0200:
        with socket.socket(family,socket.SOCK_STREAM) as sock:
            sock.settimeout(5)
            sock.connect((resolver,53))
            sock.sendall(struct.pack('!H',len(query)) + query)
            def exact(size):
                data = b''
                while len(data) < size:
                    chunk = sock.recv(size-len(data))
                    if not chunk:
                        raise ValueError('Incomplete DNS TCP response')
                    data += chunk
                return data
            response = exact(struct.unpack('!H',exact(2))[0])
    return txt_answer(response,transaction,name)


def tags(value):
    result = {}
    for item in value.split(b';'):
        if not item.strip():
            continue
        key,body = item.split(b'=',1)
        key = key.strip().lower()
        if key in result:
            raise ValueError('Duplicate DKIM tag')
        result[key] = re.sub(rb'\s+',b'',body)
    return result


def split(raw):
    header,body = raw.split(b'\r\n\r\n',1)
    headers = []
    for line in header.split(b'\r\n'):
        if line.startswith((b' ',b'\t')):
            headers[-1] += b'\r\n' + line
        else:
            headers.append(line)
    return headers,body


def canonical_header(header,mode):
    if mode == b'simple':
        return header + b'\r\n'
    if mode != b'relaxed':
        raise ValueError('Unsupported DKIM header canonicalization')
    name,value = header.split(b':',1)
    value = re.sub(rb'\r\n[ \t]+',b' ',value)
    value = re.sub(rb'[ \t]+',b' ',value).strip(b' \t')
    return name.lower() + b':' + value + b'\r\n'


def canonical_body(body,mode):
    if mode == b'relaxed':
        body = b'\r\n'.join(re.sub(rb'[ \t]+',b' ',line).rstrip(b' \t') for line in body.split(b'\r\n'))
    elif mode != b'simple':
        raise ValueError('Unsupported DKIM body canonicalization')
    result = body.rstrip(b'\r\n')
    # RFC 6376 relaxed empty body is zero bytes, simple is one CRLF.
    return result + b'\r\n' if result or mode == b'simple' else b''


def verify_one_click(raw, lookup=None):
    lookup = lookup or dns_txt
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa, ed25519
    try:
        headers,body = split(raw)
        names = [h.split(b':',1)[0].lower() for h in headers]
        if any(names.count(h) != 1 for h in (b'from',b'list-unsubscribe',b'list-unsubscribe-post')):
            raise ValueError('Missing/ambiguous signed unsubscribe headers')
        for index,header in enumerate(headers):
            if names[index] != b'dkim-signature':
                continue
            try:
                fields = tags(header.split(b':',1)[1])
                if fields.get(b'v') != b'1' or b'l' in fields or fields.get(b'a') not in {b'rsa-sha256',b'ed25519-sha256'}:
                    continue
                signed = fields[b'h'].lower().split(b':')
                if not {b'from',b'list-unsubscribe',b'list-unsubscribe-post'} <= set(signed):
                    continue
                if b'x' in fields and int(fields[b'x']) <= time.time():
                    continue
                domain = fields[b'd'].decode('ascii')
                selector = fields[b's'].decode('ascii')
                canonicalization = fields.get(b'c',b'simple/simple').split(b'/')
                hmode,bmode = canonicalization if len(canonicalization) == 2 else (canonicalization[0],b'simple')
                if base64.b64decode(fields[b'bh'],validate=True) != hashlib.sha256(canonical_body(body,bmode)).digest():
                    continue
                selected,used = [], set()
                for name in signed:
                    chosen = next((j for j in reversed(range(len(headers))) if names[j] == name and j not in used and j != index),None)
                    if chosen is not None:
                        used.add(chosen)
                        selected.append(canonical_header(headers[chosen],hmode))
                unsigned = re.sub(rb'(?i)(\bb[ \t]*=)[^;]*',rb'\1',header)
                data = b''.join(selected) + canonical_header(unsigned,hmode).removesuffix(b'\r\n')
                records = [tags(value) for value in lookup(selector + '._domainkey.' + domain) if b'p=' in value]
                if len(records) != 1:
                    continue
                key = records[0]
                if key.get(b'v',b'DKIM1') != b'DKIM1' or b'sha256' not in key.get(b'h',b'sha256').split(b':'):
                    continue
                if not set(key.get(b's',b'*').split(b':')) & {b'*',b'email'}:
                    continue
                key_bytes = base64.b64decode(key[b'p'],validate=True)
                signature = base64.b64decode(fields[b'b'],validate=True)
                if fields[b'a'] == b'rsa-sha256' and key.get(b'k',b'rsa') == b'rsa':
                    public = serialization.load_der_public_key(key_bytes)
                    if not isinstance(public,rsa.RSAPublicKey) or public.key_size < 1024:
                        continue
                    public.verify(signature,data,padding.PKCS1v15(),hashes.SHA256())
                elif fields[b'a'] == b'ed25519-sha256' and key.get(b'k') == b'ed25519':
                    ed25519.Ed25519PublicKey.from_public_bytes(key_bytes).verify(signature,hashlib.sha256(data).digest())
                else:
                    continue
                return {'domain':domain,'selector':selector,'algorithm':fields[b'a'].decode()}
            except (ValueError,KeyError,IndexError,InvalidSignature,OSError):
                continue
    except (ValueError,IndexError):
        pass
    raise Refused('unsubscribe_authentication','One-click requires a valid full DKIM signature covering both unsubscribe headers; unsupported/invalid/DNS failure. Use the header mailto choice or owner mail program.')
