import net from 'node:net';
export default async function(c){
 const {ev,rpc,guard,delivered,zero,pending,approve,log,delay,assert,work,out,fs,spawn,probe}=c;
 // TLS validation is performed by mitmproxy, with no ssl_insecure or browser
 // certificate exception. Only this disposable fixture CA joins system roots.
 for(const [label,url,expected]of [['valid','https://fixture.test:18443/receive?case=e-tls-valid',true],['invalid','https://127.0.0.1:18444/receive?case=e-tls-invalid',false]]){
  await guard(false);const result=await ev(`fetch('${url}',{method:'POST',body:'tls'}).then(r=>({status:r.status}),e=>({error:e.name}))`);if(expected)await delivered('e-tls-'+label);else await zero('e-tls-invalid');log('Q9_TLS',{label,result,receiver:c.rows('e-tls-'+label)});
 }
 await c.nav('https://fixture.test:18443/hsts');await delay(300);await c.nav('http://fixture.test:18443/hsts');log('Q9_HSTS',{page:await ev('({url:location.href,title:document.title})')});await c.nav();
 // Start 17d's working HTTP/3 receiver; its own log is the oracle.
 fs.mkdirSync(work+'/artifacts',{recursive:true});
 const wt=spawn(c.path.resolve('.work/17b-chrome/venv/bin/python'),[c.here+'/webtransport.py',work],{stdio:'ignore'});
 const turn=spawn('turnserver',['-n','--listening-ip=127.0.0.1','--relay-ip=127.0.0.1','--listening-port=13478','--tls-listening-port=15349','--realm=synthetic17e','--user=synthetic:synthetic-password','--lt-cred-mech','--allow-loopback-peers','--no-multicast-peers','--no-cli','--no-udp','--no-dtls','--cert='+work+'/fixture.pem','--pkey='+work+'/fixture.key','--log-file='+work+'/turn-private.log'],{stdio:'ignore'});
 const peer=spawn(work+'/venv/bin/python',[c.here+'/rtc-peer.py',out],{stdio:'ignore'});
 try{
  await c.eventually(()=>fs.existsSync(work+'/webtransport.json'),'WebTransport peer');const info=JSON.parse(fs.readFileSync(work+'/webtransport.json'));
  await guard(false);await c.close();await c.boot('transport-direct',false);
  const directWT=await ev(`transports(${JSON.stringify(info)})`);await delay(400);assert.ok(fs.readFileSync(out+'/webtransport-server.jsonl','utf8').includes('datagram'),'direct WebTransport positive control must deliver');log('Q8_WEBTRANSPORT_DIRECT',{result:directWT});
  async function rtc(label,tls){
   const config={iceTransportPolicy:'relay',iceServers:[{urls:`${tls?'turns':'turn'}:localhost:${tls?15349:13478}?transport=tcp`,username:'synthetic',credential:'synthetic-password'}]};
   const sdp=await ev(`rtc(${JSON.stringify(config)})`);
   const answer=await new Promise((resolve,reject)=>{const socket=net.connect(18888,'127.0.0.1',()=>socket.write(JSON.stringify({sdp})+'\n'));let buffer='';socket.on('data',b=>{buffer+=b;if(buffer.includes('\n')){resolve(JSON.parse(buffer));socket.end()}});socket.on('error',reject);socket.setTimeout(10000,()=>{socket.destroy();reject(Error('signaling timeout'))})});
   await ev(`(async()=>{const p=peer;globalThis.rtcResult='connecting';p.onconnectionstatechange=()=>rtcResult=p.connectionState;await p.setRemoteDescription(${JSON.stringify(answer)});return true})()`);
   // The first datachannel object is retained via createDataChannel wrapper.
   await ev(`globalThis.rtcSendLabel=${JSON.stringify(label)};globalThis.rtcTimer=setInterval(()=>{if(globalThis.data17?.readyState==='open'){data17.send(rtcSendLabel);clearInterval(rtcTimer)}},50);true`);
   await delay(6000);const state=await ev('({state:peer.connectionState,ice:peer.iceConnectionState,channel:data17?.readyState,errors:rtcErrors,gathering:peer.iceGatheringState})');
   const receiver=fs.existsSync(out+'/rtc-receiver.jsonl')?fs.readFileSync(out+'/rtc-receiver.jsonl','utf8').trim().split('\n').map(JSON.parse).filter(r=>r.case===label):[];
   await ev('clearInterval(rtcTimer);peer.close();true');log('Q8_WEBRTC',{label,tls,state,receiver});return receiver;
  }
  async function retainChannel(){await ev("globalThis.originalDC=RTCPeerConnection.prototype.createDataChannel;RTCPeerConnection.prototype.createDataChannel=function(...a){return globalThis.data17=originalDC.apply(this,a)};true")}
  await retainChannel();
  const directTCP=await rtc('e-rtc-tcp-control',false);assert.equal(directTCP.length,1,'TURN TCP positive control');
  const directTLS=await rtc('e-rtc-tls-control',true);assert.equal(directTLS.length,1,'TURN TLS positive control');
  await c.close();await c.boot('transport-checkpoint');await c.context();await guard();
  const blockedWT=await ev(`transports(${JSON.stringify(info)})`);const wtRows=fs.readFileSync(out+'/webtransport-server.jsonl','utf8').trim().split('\n').map(JSON.parse);assert.equal(wtRows.filter(r=>r.kind==='datagram').length,1);log('Q8_WEBTRANSPORT_BLOCKED',{result:blockedWT,receiver:wtRows});
  await retainChannel();assert.equal((await rtc('e-rtc-tcp-held',false)).length,0);assert.equal((await rtc('e-rtc-tls-held',true)).length,0);
  // Pre-existing WebSocket binary fragmentation from an independent raw client
  // is tested separately from browser TLS policy and attribution.
  await guard(false);await c.nav();
  for(const url of ['https://www.google.com/','https://safebrowsing.googleapis.com/','https://clients2.google.com/service/update2/crx','https://update.googleapis.com/service/update2']){
   await c.nav(url);await delay(1000);log('Q9_SERVICE_PAGE',{host:new URL(url).hostname,page:await ev('({url:location.origin,title:document.title,certificateError:document.body?.innerText.includes("Your connection is not private")})')});
  }
  // A page send to a service hostname is never exempted, irrespective of Origin.
  await c.nav();await c.positive('e-service-page-control','synthetic',{headers:{'x-synthetic-service-name':'safebrowsing.googleapis.com'}});await guard();await c.send('e-service-page-send','synthetic',{headers:{'x-synthetic-service-name':'safebrowsing.googleapis.com'}});const held=await pending('e-service-page-send');await zero('e-service-page-send');await controlCancel(held);log('Q9_NO_SERVICE_EXCEPTION',{held,fixtureOnly:true,receiver:c.rows('e-service-page-send')});
  async function controlCancel(op){await c.control('cancel',{id:op.id})}
  log('Q9_SERVICE_LIMIT',{notChecked:['account-backed sync','authenticated push'],reason:'No accounts or real submissions allowed. Page loads are not browser-service qualification.'});
 }finally{wt.kill();turn.kill();peer.kill();}
}
