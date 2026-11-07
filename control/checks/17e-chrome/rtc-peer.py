"""Independent synthetic WebRTC receiver; signaling is runner-only, not Chrome."""
import asyncio
import hashlib
import json
import pathlib
import sys
import time
from aiortc import RTCPeerConnection, RTCSessionDescription

out = pathlib.Path(sys.argv[1])
peers = []


async def handle(reader, writer):
    offer = json.loads(await reader.readline())
    peer = RTCPeerConnection()
    peers.append(peer)

    @peer.on('datachannel')
    def channel_open(channel):
        @channel.on('message')
        def received(data):
            body = data.encode() if isinstance(data, str) else data
            with (out/'rtc-receiver.jsonl').open('a') as stream:
                stream.write(json.dumps(dict(kind='data', case=data if isinstance(data,str) and data.startswith('e-') else 'binary', length=len(body), sha256=hashlib.sha256(body).hexdigest(), at=time.time()*1000))+'\n')
            channel.send('received')

    await peer.setRemoteDescription(RTCSessionDescription(sdp=offer['sdp'], type='offer'))
    await peer.setLocalDescription(await peer.createAnswer())
    writer.write(json.dumps(dict(sdp=peer.localDescription.sdp, type='answer')).encode()+b'\n')
    await writer.drain()
    writer.close()


async def main():
    server = await asyncio.start_server(handle, '127.0.0.1', 18888)
    async with server:
        await server.serve_forever()

asyncio.run(main())
