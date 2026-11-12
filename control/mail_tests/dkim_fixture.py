"""Independent simple/simple DKIM fixture signer. Keys exist only in test memory."""
import base64
import hashlib
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import padding,rsa


def signed(raw):
    private = rsa.generate_private_key(public_exponent=65537,key_size=2048)
    header,body = raw.split(b'\r\n\r\n',1)
    fields = []
    for line in header.split(b'\r\n'):
        if line.startswith((b' ',b'\t')):
            fields[-1] += b'\r\n' + line
        else:
            fields.append(line)
    names = [b'from',b'to',b'subject',b'list-unsubscribe',b'list-unsubscribe-post']
    selected = [next(f for f in fields if f.split(b':',1)[0].lower() == name) + b'\r\n' for name in names]
    bh = base64.b64encode(hashlib.sha256(body.rstrip(b'\r\n') + b'\r\n').digest())
    signature = b'DKIM-Signature: v=1; a=rsa-sha256; c=simple/simple; d=mail.invalid; s=fixture; h=' + b':'.join(names) + b'; bh=' + bh + b'; b='
    value = private.sign(b''.join(selected) + signature,padding.PKCS1v15(),hashes.SHA256())
    key = private.public_key().public_bytes(serialization.Encoding.DER,serialization.PublicFormat.SubjectPublicKeyInfo)
    return signature + base64.b64encode(value) + b'\r\n' + raw,b'v=DKIM1; k=rsa; p=' + base64.b64encode(key)
