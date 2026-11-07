// Separate same-UID process. All endpoints and content belong to the synthetic check.
import net from 'node:net';
const [kind,endpoint,url]=process.argv.slice(2);
const deadline=setTimeout(()=>{console.log('PEER_TIMEOUT');process.exit(2);},4000);
if(kind==='native'){
  const socket=net.connect(endpoint,()=>{
    socket.write(JSON.stringify({method:'check.connected',params:{tabId:-1,version:'same-user-spoof'}})+'\n');
    socket.end();
  });
  socket.on('close',()=>{clearTimeout(deadline);process.exit(0);});
  socket.on('error',e=>{console.log(e.code);process.exit(1);});
}else if(kind==='playwright'){
  const {chromium}=await import('playwright');
  const browser=await chromium.connect(endpoint,{timeout:3000});
  const page=browser.contexts().flatMap(c=>c.pages()).find(p=>p.url()===url);
  if(!page)throw Error('Peer did not see selected tab');
  console.log('PEER_READ',await page.locator('h1').innerText());
  // Exit disconnects the peer without issuing Browser.close to the shared browser.
  process.exit(0);
}
