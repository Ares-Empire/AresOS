import {EventEmitter} from 'node:events';
import net from 'node:net';
import fs from 'node:fs';
import WebSocket from 'ws';

// The check deliberately exposes raw CDP. A product must keep this behind its broker.
export class Protocol extends EventEmitter {
  sequence=0; pending=new Map();
  accept(message){
    if(message.id){
      const p=this.pending.get(message.id);if(!p)return;
      clearTimeout(p.timer);this.pending.delete(message.id);
      if(message.error)p.reject(new Error(JSON.stringify(message.error)));else p.resolve(message.result||{});
    }else{this.emit(message.method,message.params||{},message.sessionId);this.emit('event',message);}
  }
  send(method,params={},sessionId){
    const id=++this.sequence;
    return new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>{this.pending.delete(id);reject(new Error(`CDP timeout: ${method}`));},20000);
      this.pending.set(id,{resolve,reject,timer});
      this.write({id,method,params,...(sessionId?{sessionId}:{})});
    });
  }
  rejectAll(){for(const p of this.pending.values()){clearTimeout(p.timer);p.reject(new Error('Transport closed'));}this.pending.clear();}
}
export async function nativeBridge(socketPath){
  const client=new Protocol();let peer;
  if(fs.existsSync(socketPath))fs.unlinkSync(socketPath);
  const server=net.createServer(c=>{
    if(peer){c.destroy();return;}peer=c;
    let buffer='';c.on('data',data=>{buffer+=data;let i;while((i=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,i);buffer=buffer.slice(i+1);client.accept(JSON.parse(line));}});
    c.on('close',()=>{peer=undefined;client.rejectAll();});
  });
  await new Promise(r=>server.listen(socketPath,r));fs.chmodSync(socketPath,0o600);
  client.write=m=>{if(!peer)throw new Error('No extension connected');peer.write(JSON.stringify(m)+'\n');};
  client.close=()=>{peer?.destroy();server.close();client.rejectAll();};
  return client;
}
export async function websocket(endpoint){
  const client=new Protocol();
  const ws=new WebSocket(endpoint,{origin:'http://localhost'});
  ws.on('message',data=>client.accept(JSON.parse(data.toString())));
  ws.on('close',()=>client.rejectAll());
  client.write=m=>ws.send(JSON.stringify(m));
  client.close=()=>ws.close();
  await new Promise((r,j)=>{ws.once('open',r);ws.once('error',j);});
  return client;
}
export function session(client,sessionId){
  const s=new EventEmitter();
  s.send=(m,p={})=>client.send(m,p,sessionId);
  const handler=e=>{if(e.sessionId===sessionId){s.emit(e.method,e.params);s.emit('event',e);}};
  client.on('event',handler);s.close=()=>client.off('event',handler);
  return s;
}
export async function evaluate(cdp,expression){
  const result=await cdp.send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
  if(result.exceptionDetails)throw new Error(JSON.stringify(result.exceptionDetails));
  return result.result?.value;
}
export async function eventually(check,label,ms=10000){
  const start=Date.now();let last;
  while(Date.now()-start<ms){try{const r=await check();if(r)return r;}catch(e){last=e;}await new Promise(r=>setTimeout(r,100));}
  throw new Error(`Timed out: ${label}${last?' '+last.message:''}`);
}
