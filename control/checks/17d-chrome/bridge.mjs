import net from 'node:net';
import fs from 'node:fs';
import {Protocol} from '../17-chrome/protocol.mjs';
// Same native framing as 17c; socket errors are expected during destructive lifecycle probes.
export async function nativeBridge(socketPath){
 const client=new Protocol();let peer;
 if(fs.existsSync(socketPath))fs.unlinkSync(socketPath);
 const server=net.createServer(c=>{
  if(peer){c.destroy();return;}peer=c;let buffer='';
  c.on('data',data=>{buffer+=data;let i;while((i=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,i);buffer=buffer.slice(i+1);client.accept(JSON.parse(line));}});
  c.on('error',()=>client.rejectAll());c.on('close',()=>{if(peer===c)peer=undefined;client.rejectAll();});
 });
 await new Promise(r=>server.listen(socketPath,r));fs.chmodSync(socketPath,0o600);
 client.write=m=>{if(!peer||peer.destroyed)throw Error('No extension connected');peer.write(JSON.stringify(m)+'\n');};
 client.close=()=>{peer?.destroy();server.close();client.rejectAll();};return client;
}
