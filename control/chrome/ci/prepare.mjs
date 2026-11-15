import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {instrumentLatencyBackground,instrumentLatencyReader} from './latency-instrument.mjs';
import {instrumentOwnerGuard} from './owner-evidence.mjs';
import {generateKeyPairSync} from 'node:crypto';
import {packageExtension} from '../packaging/pack.mjs';
if(process.platform !== 'linux' || process.env.GITHUB_ACTIONS !== 'true' || !fs.existsSync('/.dockerenv'))throw Error('CI Linux container only');
const pair=generateKeyPairSync('rsa',{modulusLength:2048});
let extension='/workspace/control/chrome/extension';
if(process.env.INJECTION_PROBE==='true'){
  extension='/workspace/.work/20-probe-extension';fs.mkdirSync(extension,{recursive:true});
  fs.writeFileSync(extension+'/manifest.json',JSON.stringify({manifest_version:3,name:'Controlled injection experiment',version:'1.0.0',permissions:['debugger','tabs','scripting','dom'],host_permissions:['http://*.test/*'],background:{service_worker:'background.js'}}));
  fs.copyFileSync('/workspace/control/chrome/ci/probe-background.js',extension+'/background.js');
  fs.writeFileSync(extension+'/context.js','// Inert isolated-world bootstrap. No page access or listeners.\n(() => {})();\n');
  fs.writeFileSync(extension+'/isolated.js',"globalThis.probePrivate=true;window.addEventListener('probe-event',event=>{event.preventDefault();event.stopImmediatePropagation();},true);");
}
if(process.env.INJECTION_PROBE!=='true'){
  const instrumented='/workspace/.work/20-instrumented-extension';fs.cpSync(extension,instrumented,{recursive:true});extension=instrumented;
  if(process.env.LATENCY_PROBE!=='true'||process.env.LATENCY_PRIVACY==='audit')fs.writeFileSync(extension+'/guard.js',fs.readFileSync('/workspace/control/chrome/ci/password-ingress.js','utf8')+'\n'+instrumentOwnerGuard(fs.readFileSync(extension+'/guard.js','utf8')));
  if(process.env.LATENCY_PROBE==='true')fs.writeFileSync(extension+'/reader.js',instrumentLatencyReader(fs.readFileSync(extension+'/reader.js','utf8')));
  let background=fs.readFileSync(extension+'/background.js','utf8').replace("const defaultBlock='https://aresos-hold.invalid/';","const defaultBlock='http://fixture.test:8765/receive?case=recheck2-network-fence';").replace("chrome.runtime.onMessage.addListener((message,sender,reply)=>{", "chrome.runtime.onMessage.addListener((message,sender,reply)=>{if(sender.id===chrome.runtime.id&&['reader_ingress','owner_trace'].includes(message?.event)){audit({[message.event]:message});reply({received:true});return;}");
  if(process.env.LATENCY_PROBE==='true')background=instrumentLatencyBackground(background).replace("chrome.runtime.onMessage.addListener((message,sender,reply)=>{","chrome.runtime.onMessage.addListener((message,sender,reply)=>{if(sender.id===chrome.runtime.id&&message?.event==='latency_reader'){port?.postMessage(message);reply({received:true});return;}");
  fs.writeFileSync(extension+'/background.js',background.replace('async function dispatch(command) {', `async function dispatch(command) {
    if(command.name==='fixture_network_restart'){
      const tab=command.tab;await stop();
      await chrome.declarativeNetRequest.updateSessionRules({addRules:[{id:2,priority:2,action:{type:'block'},condition:{tabIds:[tab],urlFilter:'|'+defaultBlock,resourceTypes:['main_frame','sub_frame','ping','other']}}]});
      const result={session,rules:await chrome.declarativeNetRequest.getSessionRules()};setTimeout(()=>chrome.runtime.reload(),100);return result;
    }
  `));
}
const result=packageExtension(extension,'/workspace/.work/20-package',pair.privateKey.export({type:'pkcs8',format:'pem'}));
fs.writeFileSync('/out/extension.json',JSON.stringify({id:result.id,version:result.version}));
// The list goes where the runtime under test reads it, asked of its own exclusions.py: the latency pair runs this
// harness over an older runtime too, which read the list from /etc before 18c-b moved it to /var/lib.
const excludedSites=execFileSync('python3',['-B','-c','from aresos_control.chrome.exclusions import SETTING;print(SETTING)'],{cwd:'/workspace',env:{...process.env,PYTHONPATH:'/workspace/control'},encoding:'utf8'}).trim();
if(!/^\/[a-z0-9/._-]+\/chrome-excluded-sites\.json$/.test(excludedSites))throw Error('unexpected excluded-sites path: '+excludedSites);
fs.mkdirSync(path.dirname(excludedSites),{recursive:true});
fs.writeFileSync(excludedSites,JSON.stringify({format:1,hosts:['approval.test']}),{mode:0o640});
fs.chownSync(excludedSites,0,1001);
fs.mkdirSync('/etc/opt/chrome/native-messaging-hosts',{recursive:true});
fs.writeFileSync('/etc/opt/chrome/native-messaging-hosts/org.aresos.chrome.json',JSON.stringify({name:'org.aresos.chrome',description:'Synthetic test host',path:'/usr/libexec/aresos-control/chrome/host',type:'stdio',allowed_origins:[`chrome-extension://${result.id}/`]}));
if(process.env.INSTALL_MODE === 'policy') {
  fs.mkdirSync('/etc/opt/chrome/policies/managed',{recursive:true});
  fs.writeFileSync('/etc/opt/chrome/policies/managed/aresos.json',JSON.stringify({ExtensionInstallForcelist:[result.id+';http://127.0.0.1:8765/update.xml'],ExtensionSettings:{[result.id]:{toolbar_pin:'force_pinned'}}}));
} else {
  fs.mkdirSync('/opt/google/chrome/extensions',{recursive:true});
  fs.writeFileSync(`/opt/google/chrome/extensions/${result.id}.json`,JSON.stringify({external_crx:result.file,external_version:result.version}));
}
