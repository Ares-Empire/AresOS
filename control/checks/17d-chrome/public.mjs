export default async function(c){
 const {rpc,ev,nav,log,state,count,delay,f,assert}=c;
 await nav();await rpc('Check.floor',{domains:['127.0.0.1']});await rpc('Check.mode',{mode:'fail',owner:true});await ev('__floor.enabled=true;true');
 await c.click('#owner');await delay(500);const p=(await state()).pending.find(p=>p.description.url.includes('owner-notification'));assert.ok(p);await count('owner-notification',0);await c.screenshot(c.out,'owner-waiting');
 // Real notification action menu, inherited from 17c; no RPC decision substitutes for it.
 c.execFileSync('dunstctl',['context']);await delay(250);await c.screenshot(c.out,'notification-menu');await c.key('Return');await delay(1000);
 log('Q7_OWNER_NOTIFICATION',{held:p,rows:c.discovery('owner-notification','real desktop notification decision'),events:(await state()).history});
 await ev("__floor.enabled=false;attempt('background-own');true");await count('background-own',0);log('Q7_BACKGROUND',{events:(await state()).history.slice(-15)});
 await rpc('Check.rules',{addRules:[{id:8002,priority:100,action:{type:'allow'},condition:{tabIds:[c.selected],resourceTypes:['websocket']}}]});await ev("attempt('reached-ws','ws')");await count('reached-ws',1);
 // Use 17c's qualified cooperative message hold, on this newly opened socket.
 await rpc('Runtime.evaluate',{expression:c.fs.readFileSync(c.here.replace('17d-chrome','17c-chrome')+'/extension/wrap.js','utf8')});
 await ev("lastSocket.send(JSON.stringify({case:'held-ws-message',text:'synthetic queued'}));true");await count('held-ws-message',0);log('Q7_LIVE_HELD',{events:(await state()).history.slice(-15),page:await ev('({held:__hold17.pending.size,events})')});
 await ev("window.s=new SharedWorker('/worker.js?shared&case=public-shared');s.port.start();navigator.serviceWorker.register('/sw.js?case=public-service');true");await delay(1400);await count('public-shared-v1-first',0);await count('public-service-v1-first',0);
 // Public visits: no inputs/forms, no accounts. Global method/live block is stricter than a site guard
 // and retained in addition to site-initiator rules so every possible outgoing send is refused.
 await rpc('Check.floor',{clear:true});await rpc('Check.rules',{addRules:[{id:501,priority:1000,action:{type:'block'},condition:{excludedRequestMethods:['get','head']}},{id:502,priority:1000,action:{type:'block'},condition:{resourceTypes:['websocket','webtransport']}}]});await rpc('Check.mode',{mode:'fail'});
 const sites=[['github','https://github.com/microsoft/playwright','a[href="/microsoft/playwright/issues"]'],['wikipedia','https://en.wikipedia.org/wiki/Web_browser','a[href="#History"]'],['youtube','https://www.youtube.com/watch?v=jNQXAC9IVRw','#expand'],['news','https://www.bbc.com/news','a[href*="/news/world"],a[href*="/news/articles/"]'],['amazon','https://www.amazon.com/dp/B0BDJ279KF','a[href="#customerReviews"]'],['reddit','https://www.reddit.com/r/programming/','button[aria-label="Expand navigation"]'],['stackoverflow','https://stackoverflow.com/questions/11227809/why-is-processing-a-sorted-array-faster-than-processing-an-unsorted-array','a[href="#answers"]'],['notion','https://help-support.notion.site/0db4500bd3e74c1884b7e83f7c9de6f3','button[aria-label="Open sidebar"]'],['docs','https://docs.google.com/document/d/1aQRPDX9RjWHE48rAHntsV64VU1-4uZO_nkL6A7ohr2k/edit','#docs-view-menu'],['search','https://www.google.com/search?q=web+browser','a[href*="tbm=nws"]']];
 for(const [name,url,selector]of sites){
  await rpc('Check.clear');await rpc('Check.floor',{domains:[new URL(url).hostname]});await nav(url);await delay(4500);
  const snapshot=()=>ev('({url:location.href,title:document.title,text:document.body?.innerText.slice(0,1500),forms:document.forms.length,controller:navigator.serviceWorker?.controller?.scriptURL||null})');const rest=await snapshot(),clicks=[];
  for(let i=0;i<3;i++){clicks.push(await ev(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e)return {found:false};const text=e.innerText||e.getAttribute('aria-label');e.click();return {found:true,text}})()`));await delay(800);}
  const after=await snapshot(),events=(await state()).history;const row={name,url,rest,clicks,after,events};c.save('public-'+name,row);await c.screenshot(c.out,'public-'+name);log('Q7_PUBLIC',{name,rest,clicks,after,blocked:events.filter(e=>e.method==='check.webError').length});
 }
}
