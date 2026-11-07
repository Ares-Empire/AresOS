"""Disposable loopback WebTransport receiver for the headed GitHub check."""
import asyncio
import datetime
import hashlib
import json
import pathlib
import sys
import time
from aioquic.asyncio import QuicConnectionProtocol, serve
from aioquic.h3.connection import H3Connection, H3_ALPN
from aioquic.h3.events import HeadersReceived, DatagramReceived
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import ProtocolNegotiated
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

root = pathlib.Path(sys.argv[1])
def record(kind, **fields):
    with (root / 'artifacts/webtransport-server.jsonl').open('a') as stream:
        stream.write(json.dumps(dict(kind=kind, at=time.time()*1000, **fields))+'\n')

class Receiver(QuicConnectionProtocol):
    h3 = None
    def quic_event_received(self, event):
        if isinstance(event, ProtocolNegotiated):
            self.h3 = H3Connection(self._quic, enable_webtransport=True)
        if not self.h3:
            return
        for item in self.h3.handle_event(event):
            if isinstance(item, HeadersReceived):
                record('connect', headers={k.decode():v.decode() for k,v in item.headers})
                self.h3.send_headers(item.stream_id, [(b':status', b'200'), (b'sec-webtransport-http3-draft', b'draft02')])
                self.transmit()
            elif isinstance(item, DatagramReceived):
                record('datagram', body=item.data.decode())

async def main():
    key = ec.generate_private_key(ec.SECP256R1())
    now = datetime.datetime.now(datetime.timezone.utc)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost')])
    cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now-datetime.timedelta(minutes=1)).not_valid_after(now+datetime.timedelta(days=2))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost')]), False).sign(key, hashes.SHA256()))
    (root/'wt-cert.pem').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    (root/'wt-key.pem').write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    config = QuicConfiguration(is_client=False, alpn_protocols=H3_ALPN, max_datagram_frame_size=65536)
    config.load_cert_chain(str(root/'wt-cert.pem'), str(root/'wt-key.pem'))
    await serve('127.0.0.1', 4433, configuration=config, create_protocol=Receiver)
    (root/'webtransport.json').write_text(json.dumps(dict(url='https://localhost:4433/check', hash=list(hashlib.sha256(cert.public_bytes(serialization.Encoding.DER)).digest()))))
    await asyncio.Future()

asyncio.run(main())
