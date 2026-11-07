// Simulates the owner on CI's X display. Never imported on macOS.
import {execFileSync,spawn} from 'node:child_process';
import fs from 'node:fs';
import {setTimeout as delay} from 'node:timers/promises';
export {delay};
export function x(...args){return execFileSync('xdotool',args.map(String),{encoding:'utf8'}).trim();}
export async function key(...keys){x('key','--clearmodifiers',...keys);await delay(150);}
export async function address(url){await key('ctrl+l');x('type','--clearmodifiers','--delay','1',url);await key('Return');await delay(1200);}
export async function activateChrome(){
  let windowId;
  for(let attempt=0;attempt<100;attempt++){
    try{windowId=x('search','--onlyvisible','--class','google-chrome').split('\n').at(-1);if(windowId)break;}catch{}
    await delay(100);
  }
  if(!windowId)throw Error('Chrome did not map a visible window');
  x('windowactivate','--sync',windowId);x('windowfocus','--sync',windowId);await delay(200);
}
export async function screenshot(out,name){execFileSync('import',['-window','root',`${out}/${name}.png`]);}
let developerEnabled=false;
export async function loadUnpacked(dir,out,label){
  await address('chrome://extensions');
  await screenshot(out,`extensions-before-${label}`);
  // Fixed 1440x1000 CI display, maximized Chrome. Evidence images record this UI.
  if(!developerEnabled){x('mousemove',1415,134,'click',1);await delay(500);developerEnabled=true;}
  await screenshot(out,`extensions-dev-${label}`);
  x('mousemove',80,190,'click',1);await delay(1800);
  await screenshot(out,`extensions-dialog-${label}`);
  await key('ctrl+l');x('type','--delay','1',dir+'/');await delay(300);await key('Return');await delay(1500);
  await screenshot(out,`extensions-folder-${label}`);
  await key('alt+o');await delay(1800);
  await screenshot(out,`install-${label}`);
}
export function launch(profile,url,log,extra=[]){
  const args=[`--user-data-dir=${profile}`,'--no-first-run','--no-default-browser-check','--password-store=basic','--start-maximized','--gtk-version=3','--disable-background-mode','--disable-background-networking','--disable-component-update',...extra,url];
  if(args.some(a=>a==='--no-sandbox'||a.startsWith('--remote-debugging'))) throw new Error('Forbidden launch flag');
  fs.writeFileSync(`${log}.args.json`,JSON.stringify(args,null,2));
  const fd=fs.openSync(log,'a');
  return spawn('/usr/bin/google-chrome-stable',args,{stdio:['ignore',fd,fd]});
}
export async function stopChrome(child){
  await key('ctrl+shift+w');await delay(1500);
  if(child.exitCode===null) child.kill('SIGTERM');
  await delay(1000);
}
