import fs from 'node:fs';
import {instrumentLatencyBackground,instrumentLatencyReader} from './latency-instrument.mjs';
import {instrumentInputBoundary} from './input-boundary.mjs';
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
  // Each rewrite has to find its text exactly once: a rewrite that silently
  // matches nothing leaves a fixture command out of the test build.
  const exactly=(source,before,after)=>{if(typeof before!=='string'||source.split(before).length!==2)throw Error('prepare.mjs: expected exactly one '+JSON.stringify(String(before).slice(0,80)));return source.replace(before,()=>after);};
  // Brief 28, group 14's mutation check (unread-matrix.mjs). In this test build only, a page whose own address
  // carries unprotect=history is read without the history rule. The case opens one such page, which holds a
  // probe value and no password, and shows that every field then returns it: the rule is what keeps them out.
  // The shipped reader is not touched; a runtime without the rule's line (the latency pair's old one) gets nothing.
  const historyRule='const unknownHistory=element=>!watched||privacy.lateFields.has(element);',builtReader=fs.readFileSync(extension+'/reader.js','utf8');
  if(process.env.LATENCY_PROBE!=='true'&&builtReader.includes(historyRule))
    fs.writeFileSync(extension+'/reader.js',exactly(builtReader,historyRule,"const unknownHistory=element=>new URL(location.href).searchParams.get('unprotect')!=='history'&&(!watched||privacy.lateFields.has(element));"));
  // A runtime without brief 28's item 4 (an older build the qualification run
  // may load) gets no holds; the time cases don't run against it (browser.mjs).
  const timedContent='async function content(tab, frame, command, parameters={},browserDocument=null,expires=null) {';
  if(process.env.LATENCY_PROBE!=='true'&&background.includes(timedContent)){
    // Brief 28, group 14's time cases (outline-time.mjs). fixture_hold_reader
    // holds one tab's reader replies back by ms, for the next duration ms;
    // fixture_hold_reply holds the extension's own reply to the next command of
    // that name and tab by ms, as an extension that overruns its time would.
    background=exactly(background,timedContent,`const fixtureHolds={reader:new Map(),reply:null};
function fixtureSendMessage(tab,message,options){
  const reply=chrome.tabs.sendMessage(tab,message,options),hold=fixtureHolds.reader.get(tab);
  if(!hold||Date.now()>=hold.until||hold.commands&&!hold.commands.includes(message.command))return reply;
  port?.postMessage({event:'fixture_reader_held',tab,command:message.command});
  return reply.then(value=>new Promise(resolve=>setTimeout(()=>{port?.postMessage({event:'fixture_reader_released',tab,command:message.command});resolve(value);},hold.ms)));
}
async function fixtureReplyDelay(message){
  const hold=fixtureHolds.reply;
  if(!hold||message.command?.name!==hold.name||message.command?.tab!==hold.tab)return;
  fixtureHolds.reply=null;port?.postMessage({event:'fixture_reply_held',id:message.id});
  await new Promise(resolve=>setTimeout(resolve,hold.ms));
  port?.postMessage({event:'fixture_reply_released',id:message.id});
}
async function content(tab, frame, command, parameters={},browserDocument=null,expires=null) {`);
    background=exactly(background,'chrome.tabs.sendMessage(tab,{command,...parameters},','fixtureSendMessage(tab,{command,...parameters},');
    background=exactly(background,'try { respond({id:message.id,ok:true,data:await dispatch(message.command,expires)}); }','try { const data=await dispatch(message.command,expires);await fixtureReplyDelay(message);respond({id:message.id,ok:true,data}); }');
  }
  if(process.env.ACT_INPUT_BOUNDARY==='true')background=instrumentInputBoundary(background,exactly);
  // The latency pair's historical runtime (ab7aba92) gets this file too; its dispatch takes no time.
  const dispatchStart=['async function dispatch(command,expires=null) {','async function dispatch(command) {'].find(text=>background.includes(text));
  fs.writeFileSync(extension+'/background.js',exactly(background,dispatchStart, dispatchStart+`
    if(command.name==='fixture_network_restart'){
      const tab=command.tab;await stop();
      await chrome.declarativeNetRequest.updateSessionRules({addRules:[{id:2,priority:2,action:{type:'block'},condition:{tabIds:[tab],urlFilter:'|'+defaultBlock,resourceTypes:['main_frame','sub_frame','ping','other']}}]});
      const result={session,rules:await chrome.declarativeNetRequest.getSessionRules()};setTimeout(()=>chrome.runtime.reload(),100);return result;
    }
    if(command.name==='fixture_hold_reader'&&typeof fixtureHolds==='object'){fixtureHolds.reader.set(command.tab,{ms:command.ms,until:Date.now()+command.duration,commands:command.commands||null});return {held:command.tab};}
    if(command.name==='fixture_hold_reply'&&typeof fixtureHolds==='object'){fixtureHolds.reply={name:command.command,tab:command.tab,ms:command.ms};return {held:command.tab};}
    if(command.name==='fixture_mute_tab'&&typeof fixtureHolds==='object'){const tab=await chrome.tabs.update(command.tab,{muted:true});return {muted:tab.mutedInfo?.muted===true};}
  `));
}
const result=packageExtension(extension,'/workspace/.work/20-package',pair.privateKey.export({type:'pkcs8',format:'pem'}));
fs.writeFileSync('/out/extension.json',JSON.stringify({id:result.id,version:result.version}));
fs.mkdirSync('/etc/aresos/control',{recursive:true});
fs.writeFileSync('/etc/aresos/control/chrome-excluded-sites.json',JSON.stringify({format:1,hosts:['approval.test']}),{mode:0o640});
fs.chownSync('/etc/aresos/control/chrome-excluded-sites.json',0,1001);
fs.mkdirSync('/etc/opt/chrome/native-messaging-hosts',{recursive:true});
fs.writeFileSync('/etc/opt/chrome/native-messaging-hosts/org.aresos.chrome.json',JSON.stringify({name:'org.aresos.chrome',description:'Synthetic test host',path:'/usr/libexec/aresos-control/chrome/host',type:'stdio',allowed_origins:[`chrome-extension://${result.id}/`]}));
if(process.env.INSTALL_MODE === 'policy') {
  fs.mkdirSync('/etc/opt/chrome/policies/managed',{recursive:true});
  fs.writeFileSync('/etc/opt/chrome/policies/managed/aresos.json',JSON.stringify({ExtensionInstallForcelist:[result.id+';http://127.0.0.1:8765/update.xml'],ExtensionSettings:{[result.id]:{toolbar_pin:'force_pinned'}}}));
} else {
  fs.mkdirSync('/opt/google/chrome/extensions',{recursive:true});
  fs.writeFileSync(`/opt/google/chrome/extensions/${result.id}.json`,JSON.stringify({external_crx:result.file,external_version:result.version}));
}
