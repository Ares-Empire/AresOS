export default async function(c){
 const {ev,rpc,guard,log,delay,work,fs,save,control,pending,approve,delivered}=c;
 // Same anonymous reading visits as 17c/17d; no selectors are clicked, no text
 // typed, forms submitted or real accounts used. Safety applies to BOTH arms.
 const sites=[['github','https://github.com/microsoft/playwright'],['wikipedia','https://en.wikipedia.org/wiki/Web_browser'],['youtube','https://www.youtube.com/watch?v=jNQXAC9IVRw'],['news','https://www.bbc.com/news'],['amazon','https://www.amazon.com/dp/B0BDJ279KF'],['reddit','https://www.reddit.com/r/programming/'],['stackoverflow','https://stackoverflow.com/questions/11227809/why-is-processing-a-sorted-array-faster-than-processing-an-unsorted-array'],['notion','https://help-support.notion.site/0db4500bd3e74c1884b7e83f7c9de6f3'],['docs','https://docs.google.com/document/d/1aQRPDX9RjWHE48rAHntsV64VU1-4uZO_nkL6A7ohr2k/edit'],['search','https://www.google.com/search?q=web+browser']];
 const results=[];
 async function visit(name,url,mode){
  const start=Date.now();await rpc('Page.navigate',{url});await delay(5500);
  const result=await ev(`(()=>{const text=document.body?.innerText||'',n=performance.getEntriesByType('navigation')[0];return {host:location.hostname,title:document.title,bytes:text.length,robot:/captcha|verify you are human|unusual traffic|checking your browser|robot check|not a robot|not a bot|security verification|just a moment/i.test(document.title+text),blocked:/access denied|request blocked|temporarily blocked|blocked by network security|ERR_|can't be reached/i.test(text),certificateError:/Your connection is not private/.test(text),loadMs:n?.loadEventEnd||null,domMs:n?.domContentLoadedEventEnd||null,protocol:n?.nextHopProtocol||null,readingText:text.slice(0,160)}})()`);
  // Save classifications/timing, never cookies, credentials, storage or bodies.
  delete result.readingText;const row={site:name,mode,elapsedMs:Date.now()-start,...result};results.push(row);log('Q11_PUBLIC',row);if(name!=='fingerprint')await c.screenshot(c.out,mode+'-'+name);
 }
 await guard(false);
 for(const mode of ['direct','checkpoint']){
  await c.close();await c.boot('public-'+mode,mode==='checkpoint');await rpc('Check.safety');
  // Local content-script safeguards are policy-installed BEFORE public visits.
  for(const [name,url]of sites)await visit(name,url,mode);
  await visit('fingerprint','https://tls.peet.ws/api/all',mode);
  // This public echo reports transport fields. Select just the fingerprint;
  // omit its IP address and echoed HTTP headers from retained evidence.
  try{const fp=await ev(`(()=>{const p=JSON.parse(document.body.innerText);return {tls:{ja3:p.tls?.ja3,ja3_hash:p.tls?.ja3_hash,ja4:p.tls?.ja4},http2:{akamai_fingerprint:p.http2?.akamai_fingerprint,akamai_fingerprint_hash:p.http2?.akamai_fingerprint_hash},http_version:p.http_version}})()`);log('Q11_FINGERPRINT',{mode,...fp})}catch(e){log('Q11_FINGERPRINT',{mode,error:e.message})}
  if(mode==='checkpoint'){
   const usage=c.sudo('ps','-u','aresproxy','-o','pid,%cpu,rss,vsz,time');log('Q11_RESOURCES',{usage});save('resources',{usage});
  }
 }
 save('public-sites',results);
 // Synthetic signed-in traffic is separate from the public no-send visits.
 await guard(false);await c.nav();await rpc('Check.safety',{clear:true});
 const session=await ev("fetch('/whoami').then(r=>r.json())");c.assert.equal(session.account,'synthetic-A');
 await ev("ws('e-signed-live');true");await delivered('e-signed-live','ws-open');
 await ev("sockets['e-signed-live'].send('e-signed-live-control');true");await delivered('e-signed-live-control','ws-message');
 await c.positive('e-background-control');await guard();
 await ev("for(let i=0;i<12;i++)send('e-background-'+i);for(let i=0;i<6;i++)sockets['e-signed-live'].send('e-live-background-'+i);true");
 await c.eventually(async()=>(await control('state')).rows.some(r=>r.case.startsWith('e-background-')&&r.status==='held'),'synthetic background operations held');
 for(let turn=0;turn<20;turn++){const pending=(await control('state')).rows.filter(r=>(r.case.startsWith('e-background-')||r.case==='e-signed-live')&&r.status==='held');for(const op of pending)await control('cancel',{id:op.id});await delay(60);}
 const held=(await control('state')).rows.filter(r=>r.case.startsWith('e-background-')||r.case==='e-signed-live');
 c.assert.equal(held.length,18,'each background request and live message has its own operation');
 for(let i=0;i<12;i++)await c.zero('e-background-'+i);for(let i=0;i<6;i++)await c.zero('e-live-background-'+i);
 log('Q11_PROMPT_PRESSURE',{session,backgroundRequests:12,liveMessages:6,approvalsRequired:held.length,policy:'all uncertain traffic is held; each operation would need its own decision'});
 await c.positive('e-owner-notification-control');await guard();await c.send('e-owner-notification');const ownerOperation=await pending('e-owner-notification');await c.zero('e-owner-notification');const action=await (await import('./notification.mjs')).default(c,ownerOperation);await delivered('e-owner-notification');log('Q11_OWNER_NOTIFICATION',{operationId:ownerOperation.id,action,receiver:c.rows('e-owner-notification')});
 log('Q11_PRIVACY',{bodyLogs:false,cookieLogs:false,payloadStorage:'RAM only',ledger:'hashes, lengths and states',perBodyBytes:32*1024*1024,pendingBodyBytes:64*1024*1024,maxOperations:256});
}
