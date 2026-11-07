// Simulates the owner on CI's X display. Never imported on macOS.
import {execFileSync,spawn} from 'node:child_process';
import fs from 'node:fs';
import {setTimeout as delay} from 'node:timers/promises';
export {delay};
export function x(...args){return execFileSync('xdotool',args.map(String),{encoding:'utf8'}).trim();}
export async function key(...keys){x('key','--clearmodifiers',...keys);await delay(150);}
export async function address(url){await key('ctrl+l');x('type','--clearmodifiers','--delay','1',url);await key('Return');await delay(1200);}
export async function screenshot(out,name){execFileSync('import',['-window','root',`${out}/${name}.png`]);}
export async function loadUnpacked(dir,out,label){
  await address('chrome://extensions');
  await screenshot(out,`extensions-before-${label}`);
  // Fixed 1440x1000 CI display, maximized Chrome. Evidence images record this UI.
  x('mousemove',1390,132,'click',1);await delay(500);
  await screenshot(out,`extensions-dev-${label}`);
  x('mousemove',145,174,'click',1);await delay(600);
  await screenshot(out,`extensions-dialog-${label}`);
  await key('ctrl+l');x('type','--delay','1',dir);await key('Return');await delay(500);await key('Return');await delay(1200);
  await screenshot(out,`install-${label}`);
}
export function launch(profile,url,log,extra=[]){
  const args=[`--user-data-dir=${profile}`,'--no-first-run','--no-default-browser-check','--password-store=basic','--start-maximized','--disable-background-networking','--disable-component-update',...extra,url];
  if(args.some(a=>a==='--no-sandbox'||a.startsWith('--remote-debugging'))) throw new Error('Forbidden launch flag');
  fs.writeFileSync(`${log}.args.json`,JSON.stringify(args,null,2));
  const fd=fs.openSync(log,'a');
  return spawn('/usr/bin/google-chrome-stable',args,{stdio:['ignore',fd,fd]});
}
export async function stopChrome(child){
  await key('ctrl+shift+q');await delay(1500);
  if(child.exitCode===null) child.kill('SIGTERM');
  await delay(1000);
}
