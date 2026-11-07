import fs from 'node:fs';
import path from 'node:path';
import net from 'node:net';
import {createHash,generateKeyPairSync} from 'node:crypto';
import {fileURLToPath} from 'node:url';
if(process.platform!=='linux'||process.env.GITHUB_ACTIONS!=='true') throw new Error('Browser runs are restricted to GitHub Linux runners');
const here=path.dirname(fileURLToPath(import.meta.url));
const work=path.resolve(here,'../../../.work/17-chrome');
const out=path.join(work,'artifacts'); fs.mkdirSync(out,{recursive:true});
const {fixtures}=await import('./fixture.mjs');
const {launch,address,key,delay,loadUnpacked,screenshot,stopChrome}=await import('./ui.mjs');
const fixture=await fixtures(out);
const profile=path.join(work,'profile');
const manifest=JSON.parse(fs.readFileSync(path.join(here,'extension/manifest.json')));
const extDir=path.join(work,'own-extension');fs.cpSync(path.join(here,'extension'),extDir,{recursive:true});
manifest.key=generateKeyPairSync('rsa',{modulusLength:2048}).publicKey.export({type:'spki',format:'der'}).toString('base64');
fs.writeFileSync(path.join(extDir,'manifest.json'),JSON.stringify(manifest));
const id=[...createHash('sha256').update(Buffer.from(manifest.key,'base64')).digest().subarray(0,16)].map(b=>String.fromCharCode(97+(b>>4),97+(b&15))).join('');
const socketPath=path.join(work,'native.sock');
process.env.CHROME_CHECK_SOCKET=socketPath;
const host={name:'org.aresos.chrome_check',description:'CI feasibility check',path:path.join(here,'native-host.py'),type:'stdio',allowed_origins:[`chrome-extension://${id}/`]};
for(const dir of [path.join(profile,'NativeMessagingHosts'),path.join(process.env.XDG_CONFIG_HOME,'google-chrome/NativeMessagingHosts')]){fs.mkdirSync(dir,{recursive:true});fs.writeFileSync(path.join(dir,host.name+'.json'),JSON.stringify(host));}
let connection;
const server=net.createServer(c=>{connection=c;c.on('data',data=>console.log('NATIVE',data.toString()));});
if(fs.existsSync(socketPath)) fs.unlinkSync(socketPath);
await new Promise(r=>server.listen(socketPath,r));fs.chmodSync(socketPath,0o600);
let chrome;
try {
  chrome=launch(profile,fixture.base+'/login',path.join(out,'chrome.log'));
  await delay(2500);await key('Return');await delay(700);
  console.log('LOGIN',JSON.stringify(fixture.arrivals));
  await screenshot(out,'signed-in-before-tool');
  await loadUnpacked(extDir,out,'own');
  await address(`chrome-extension://${id}/select.html?url=${encodeURIComponent(fixture.base+'/owner')}`);
  await screenshot(out,'select-tab');await key('Return');await delay(1500);
  await screenshot(out,'attached');
  if(!connection) throw new Error('Native host did not connect');
  connection.write(JSON.stringify({id:1,method:'Runtime.evaluate',params:{expression:'document.body.innerText',returnByValue:true}})+'\n');
  await delay(500);
  console.log('BOOTSTRAP PASS');
} finally {
  if(chrome) await stopChrome(chrome);
  connection?.destroy();server.close();fixture.close();
}
