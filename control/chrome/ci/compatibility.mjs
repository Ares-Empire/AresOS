// Synthetic compatibility fixture and headed Linux-runner measurements.
import fs from 'node:fs';
import {spawn,execFileSync} from 'node:child_process';
import {setTimeout as delay} from 'node:timers/promises';
import assert from 'node:assert/strict';

export function compatibilityScript(id){return `
const fixtureId=${JSON.stringify(id)};
const send=value=>fetch('/compat-report',{method:'POST',body:JSON.stringify({id:fixtureId,...value})});
send({phase:'ready'});
document.querySelector('#continue').onclick=()=>{
  const result={};
  result.functions=[HTMLFormElement.prototype.submit,HTMLFormElement.prototype.requestSubmit,HTMLElement.prototype.click,EventTarget.prototype.dispatchEvent].map(fn=>Function.prototype.toString.call(fn));
  const bus=new EventTarget();let busCount=0;bus.addEventListener('bus',event=>{busCount++;result.preventReturn=typeof event.preventDefault();});
  result.busReturn=bus.dispatchEvent(new Event('bus',{cancelable:true}));result.busCount=busCount;
  let windows=0;window.addEventListener('compat-window',()=>windows++);result.windowReturn=window.dispatchEvent(new Event('compat-window'));result.windows=windows;
  result.shadows=[];
  for(const mode of ['open','closed']){
    customElements.define('compat-'+mode,class extends HTMLElement{constructor(){super();const root=this.attachShadow({mode}),node=document.createElement('button');node.textContent='Ordinary control';root.append(node);let count=0,data=null;node.addEventListener('compat-shadow',event=>{count++;data=event.detail;event.preventDefault();});const dispatched=node.dispatchEvent(new CustomEvent('compat-shadow',{cancelable:true,detail:7}));result.shadows.push({mode,count,data,dispatched});}});
    document.body.append(document.createElement('compat-'+mode));
  }
  result.inert=[];
  for(const source of [new DOMParser().parseFromString('<button>Ordinary control</button>','text/html'),document.implementation.createHTMLDocument(),document.createElement('template').content]){
    const node=source.querySelector('button')||(source.body||source).appendChild(document.createElement('button'));let count=0;node.addEventListener('click',event=>{count++;event.preventDefault();});const dispatched=node.dispatchEvent(new MouseEvent('click',{cancelable:true}));const clicked=typeof node.click();result.inert.push({count,dispatched,clicked});
  }
  const original=HTMLElement.prototype.click;let replacements=0;Object.defineProperty(HTMLElement.prototype,'click',{configurable:true,writable:true,value:function(){replacements++;return Reflect.apply(original,this,arguments);}});
  const detached=document.createElement('button');detached.click();result.replacements=replacements;Object.defineProperty(HTMLElement.prototype,'click',{configurable:true,writable:true,value:original});
  const link=document.createElement('a');link.href='/download?id='+fixtureId;link.download=fixtureId+'.txt';result.downloadReturn=typeof link.click();
  const file=document.createElement('input');file.type='file';result.fileReturn=typeof file.click();
  send({phase:'result',result});
};`;
}

const key=(...keys)=>execFileSync('xdotool',['key','--clearmodifiers',...keys]);
export function nativeCompatibilityClick(){
  const windows=execFileSync('xdotool',['search','--onlyvisible','--class','[Gg]oogle-chrome'],{encoding:'utf8'}).trim().split('\n');
  const window=windows.at(-1);execFileSync('xdotool',['windowactivate','--sync',window]);
  const geometry=execFileSync('xdotool',['getwindowgeometry','--shell',window],{encoding:'utf8'});
  const width=Number(geometry.match(/^WIDTH=(\d+)/m)[1]),height=Number(geometry.match(/^HEIGHT=(\d+)/m)[1]);
  execFileSync('xdotool',['mousemove','--window',window,String(Math.floor(width/2)),String(Math.floor(height/2)),'click','1']);
}
export function nativeNavigate(url){key('ctrl+l');execFileSync('xdotool',['type','--clearmodifiers','--delay','1',url]);key('Return');}
export async function measureCompatibility({id,fixture,eventually,start}){
  await eventually(()=>fixture.compatibility.some(value=>value.id===id&&value.phase==='ready'),'native compatibility page ready');
  const pending=start();
  const title=await eventually(()=>{
    const active=execFileSync('xdotool',['getactivewindow'],{encoding:'utf8'}).trim();
    const title=execFileSync('xdotool',['getwindowname',active],{encoding:'utf8'}).trim();
    return /^(?:Open|Choose|Select)(?:\s|$)/.test(title)?title:false;
  },'native detached file picker opens');
  key('Escape');await pending;
  const record=await eventually(()=>fixture.compatibility.find(value=>value.id===id&&value.phase==='result'),'compatibility result');
  await eventually(()=>fixture.compatibilityDownloads.filter(value=>value===id).length===1,'detached anchor downloaded exactly once');
  return {...record.result,filePicker:title};
}

export async function withoutExtension({fixture,eventually,descriptor}){
  if(process.platform!=='linux'||process.env.GITHUB_ACTIONS!=='true'||!fs.existsSync('/.dockerenv'))throw Error('Browser baseline runs only in GitHub Linux containers');
  const profile=fs.mkdtempSync('/tmp/aresos-native-baseline-');
  const browser=spawn('qualification-chrome',[`--user-data-dir=${profile}`,'--disable-extensions','--no-first-run','--no-default-browser-check','--password-store=basic','--gtk-version=3','--host-resolver-rules=MAP *.test 127.0.0.1','http://fixture.test:8765/?case=native-compat&id=baseline'],{stdio:['ignore',descriptor,descriptor]});
  try{
    const measured=await measureCompatibility({id:'baseline',fixture,eventually,start:nativeCompatibilityClick});
    fs.writeFileSync('/out/native-baseline.json',JSON.stringify(measured,null,2));return measured;
  }catch(error){try{execFileSync('import',['-window','root','/out/native-failure.png']);}catch{}throw error;
  }finally{browser.kill('SIGTERM');await delay(500);if(browser.exitCode===null)browser.kill('SIGKILL');fs.rmSync(profile,{recursive:true,force:true});}
}

export function compareCompatibility(actual,expected){assert.deepEqual(actual,expected,'only held asking controls may differ from Chrome without the extension');}
