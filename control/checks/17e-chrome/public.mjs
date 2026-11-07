export default async function(c){
 const {ev,rpc,guard,log,delay,work,fs,save,control,pending,approve,delivered}=c;
 // Same anonymous reading visits as 17c/17d; no selectors are clicked, no text
 // typed, forms submitted or real accounts used. Safety applies to BOTH arms.
 const sites=[['github','https://github.com/microsoft/playwright'],['wikipedia','https://en.wikipedia.org/wiki/Web_browser'],['youtube','https://www.youtube.com/watch?v=jNQXAC9IVRw'],['news','https://www.bbc.com/news'],['amazon','https://www.amazon.com/dp/B0BDJ279KF'],['reddit','https://www.reddit.com/r/programming/'],['stackoverflow','https://stackoverflow.com/questions/11227809/why-is-processing-a-sorted-array-faster-than-processing-an-unsorted-array'],['notion','https://help-support.notion.site/0db4500bd3e74c1884b7e83f7c9de6f3'],['docs','https://docs.google.com/document/d/1aQRPDX9RjWHE48rAHntsV64VU1-4uZO_nkL6A7ohr2k/edit'],['search','https://www.google.com/search?q=web+browser']];
 const results=[];
 async function visit(name,url,mode){
  const start=Date.now();await rpc('Page.navigate',{url});await delay(5500);
  const result=await ev(`(()=>{const text=document.body?.innerText||'',n=performance.getEntriesByType('navigation')[0];return {host:location.hostname,title:document.title,bytes:text.length,robot:/captcha|verify you are human|unusual traffic|checking your browser|robot check|not a robot/i.test(text),blocked:/access denied|request blocked|temporarily blocked|ERR_|can't be reached/i.test(text),certificateError:/Your connection is not private/.test(text),loadMs:n?.loadEventEnd||null,domMs:n?.domContentLoadedEventEnd||null,protocol:n?.nextHopProtocol||null,readingText:text.slice(0,160)}})()`);
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
 // A synthetic signed-in app exposes actual prompt pressure under a broad
 // guard. Background autosaves, heartbeat and owner sends are all operations.
 // Remove safety dynamic rules by reinstalling a fresh diagnostic extension
 // session via a new Chrome profile is unnecessary: use GET for the fixture
 // and pre-open its live connection in a separate core run (reported there).
 await guard(false);await c.nav();await guard();
 const start=(await control('state')).rows.length;
 await ev("for(let i=0;i<12;i++)fetch('/receive?case=e-background-'+i).catch(()=>{});true");
 await c.eventually(async()=>(await control('state')).rows.filter(r=>r.case.startsWith('e-background-')&&r.status==='held').length===12,'synthetic background operations held');
 const held=(await control('state')).rows.filter(r=>r.case.startsWith('e-background-')&&r.status==='held');log('Q11_PROMPT_PRESSURE',{durationSeconds:6,backgroundRequests:12,approvalsRequired:held.length,account:'synthetic-A',policy:'all uncertain traffic is held'});
 for(const op of held)await control('cancel',{id:op.id});
 log('Q11_PRIVACY',{bodyLogs:false,cookieLogs:false,payloadStorage:'RAM only',ledger:'hashes, lengths and states',perBodyBytes:32*1024*1024,pendingBodyBytes:64*1024*1024,maxOperations:256});
}
