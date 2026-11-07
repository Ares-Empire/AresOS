// Raw operation controls exercise encodings the Fetch API cannot choose.
// This is a fixture client, never a substitute for the headed Chrome cases.
import net from 'node:net';
import http from 'node:http';
import WebSocket from '../17-chrome/node_modules/ws/wrapper.mjs';
export default async function(c){
 const {guard,pending,approve,control,zero,delivered,log,assert,delay}=c;
 function chunked(id,complete=true){
  const r=http.request({host:'127.0.0.1',port:18080,path:c.f.base+'/receive?case='+id,method:'POST',headers:{'transfer-encoding':'chunked','content-type':'application/octet-stream'}},res=>res.resume());r.on('error',()=>{});r.write(Buffer.from([0,1,2]));r.write(Buffer.from([128,255]));if(complete)r.end();return r;
 }
 for(const held of [false,true]){const id='e-chunked-'+(held?'held':'control');await guard(held);chunked(id);if(held){await pending(id);await zero(id);await approve(id);}await delivered(id);assert.equal(c.arrivals(id)[0].sha256,c.hash(Buffer.from([0,1,2,128,255])));log('Q4_CHUNKED',{held,receiver:c.rows(id)});}
 await guard();const incomplete=chunked('e-incomplete',false);await delay(500);await zero('e-incomplete');incomplete.destroy();await delay(200);await zero('e-incomplete');log('Q4_INCOMPLETE',{receiver:c.rows('e-incomplete'),result:'connection closed without upstream request headers'});
 const agent=new http.Agent();agent.createConnection=(opts,callback)=>{
  const socket=net.connect(18080,'127.0.0.1',()=>socket.write('CONNECT 127.0.0.1:18081 HTTP/1.1\r\nHost: 127.0.0.1:18081\r\n\r\n'));
  let text='';const data=b=>{text+=b.toString();if(text.includes('\r\n\r\n')){socket.off('data',data);callback(null,socket)}};socket.on('data',data);socket.on('error',e=>callback(e));return undefined;
 };
 for(const held of [false,true]){
  const id='e-fragment-'+(held?'held':'control');await guard(false);const socket=new WebSocket(c.f.base.replace('http:','ws:')+'/socket?case='+id,{agent});await new Promise((r,j)=>{socket.once('open',r);socket.once('error',j)});await delivered(id,'ws-open');await guard(held);
  socket.send('e-fragment-',{fin:false});await delay(250);assert.equal(c.arrivals(id,'ws-message').length,0,'partial fragment bytes must not reach receiver');socket.send(held?'held':'control',{fin:true});if(held){const p=await pending(id,'ws-message');assert.equal(c.arrivals(id,'ws-message').length,0);await control('approve',{id:p.id});}await delivered(id,'ws-message');await guard(false);socket.close();log('Q4_FRAGMENTED',{held,receiver:c.rows(id)});
 }
 agent.destroy();
 // A fixed resource refusal must not become an allow on ENOSPC.
 await guard();await control('fault',{point:'ledger-full'});chunked('e-ledger-full');await delay(500);await zero('e-ledger-full');await control('fault',{point:null});const full=c.sudo('cat',c.work+'/private/events.jsonl').trim().split('\n').map(JSON.parse).find(r=>r.case==='e-ledger-full'&&r.sqliteError==='SQLITE_FULL');assert.ok(full,'real SQLite quota failure');log('Q11_LEDGER_EXHAUSTION',{receiver:c.rows('e-ledger-full'),refusal:full});
 chunked('e-memory-full');await pending('e-memory-full');await control('exhaust-memory').catch(()=>{});await delay(300);await zero('e-memory-full');await c.startProxy();await zero('e-memory-full');log('Q11_MEMORY_EXHAUSTION',{receiver:c.rows('e-memory-full'),state:await control('state')});
}
