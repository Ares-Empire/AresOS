// F7: the details page and the extension's wait for a polkit password. Plain
// in-memory DOM and timers; no browser or process.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

class Element{
  constructor(){this.children=[];this.listeners={};this.textContent='';}
  append(...items){this.children.push(...items);}
  replaceChildren(...items){this.children=items;}
  querySelector(){return null;}
  addEventListener(name,callback){this.listeners[name]=callback;}
  click(){return this.listeners.click();}
}
async function settle(){for(let n=0;n<20;n++)await Promise.resolve();}
async function page(){
  const elements={'#entries':new Element(),'#status':new Element()},calls=[],answers=[];
  const sendMessage=message=>{
    calls.push(message.arguments);
    if(message.arguments.command==='list')return Promise.resolve({ok:true,data:{items:[
      {kind:'recent',operation_id:'op-1',question:'Send the draft to recipient@example.invalid?',eligible:true},
      {kind:'readonly',id:'locked.test',value:true},{kind:'readonly',id:'open.test',value:false}],cursor:null}});
    return new Promise(resolve=>answers.push(resolve));
  };
  vm.runInNewContext(fs.readFileSync('control/chrome/extension/details.js','utf8'),{document:{querySelector:id=>elements[id],createElement:()=>new Element()},chrome:{runtime:{sendMessage}}});
  await settle();
  return {elements,calls,answers,rows:elements['#entries'].children};
}

test('final F7 the details page names the pending change while the password dialog is up',async()=>{
  const {elements,calls,answers,rows}=await page(),status=elements['#status'];
  const allow=rows[0].children.find(item=>item.textContent==="Don't ask again for this kind");
  const done=allow.click();await settle();
  assert.deepEqual(JSON.parse(JSON.stringify(calls.at(-1))),{command:'allow',operation_id:'op-1'});
  assert.equal(status.textContent,"Waiting for your password in the system dialog: don't ask again for Send the draft to recipient@example.invalid?");
  answers.shift()({ok:false,error:{message:'Nothing changed: the password dialog was dismissed.'}});await done;
  assert.equal(status.textContent,'Nothing changed: the password dialog was dismissed.');
  const editing=elements['#entries'].children[1].children.find(item=>item.textContent==='Allow editing');
  const unlocked=editing.click();await settle();
  assert.equal(status.textContent,'Waiting for your password in the system dialog: read-only off for locked.test');
  answers.shift()({ok:true,data:{readonly:'locked.test',enabled:false}});await unlocked;
  assert.equal(status.textContent,'Changed: read-only off for locked.test');
  const lock=elements['#entries'].children[2].children.find(item=>item.textContent==='Make read-only');
  const locked=lock.click();await settle();
  assert.equal(status.textContent,'');
  answers.shift()({ok:true,data:{readonly:'open.test',enabled:true}});await locked;
  assert.equal(status.textContent,'');
});

test('final F7 the details page says that loosening asks for the password',()=>{
  const text=fs.readFileSync('control/chrome/extension/details.html','utf8');
  assert.match(text,/"Don't ask again" and "Allow editing" ask for your password in a system dialog, once for each change\./);
  assert.match(text,/<p id="status" role="status"><\/p>/);
});

test('final F7 the extension waits past the service polkit timeout only for loosening',()=>{
  const source=fs.readFileSync('control/chrome/extension/background.js','utf8');
  const wait=Number(source.match(/const LOOSEN_WAIT_MS=(\d+);/)[1]);
  const service=Number(fs.readFileSync('control/aresos_control/chrome/confirm.py','utf8').match(/^TIMEOUT = ([\d.]+)$/m)[1])*1000;
  assert.ok(wait>service+10000,`${wait} must exceed ${service}`);
  const timers=[],posted=[];
  const context=vm.createContext({LOOSEN_WAIT_MS:wait,ownerRequests:new Map(),port:{postMessage:value=>posted.push(value)},crypto:{randomUUID:()=>'request-'+posted.length},
    setTimeout:(callback,delay)=>{timers.push(delay);return 0},Object,
    chrome:{runtime:{id:'fixture',getURL:path=>'chrome-extension://fixture/'+path,onMessage:{addListener:listener=>{context.receive=listener}}}}});
  vm.runInContext(source.slice(source.indexOf('chrome.runtime.onMessage.addListener('),source.indexOf('chrome.tabs.onUpdated.addListener(')),context);
  const sender={id:'fixture',url:'chrome-extension://fixture/details.html',tab:{id:3},frameId:0};
  const cases=[[{command:'list'},10000],[{command:'revoke',id:'x'},10000],[{command:'readonly',site:'https://x.test/',enabled:true},10000],
    [{command:'readonly',site:'https://x.test/'},10000],[{command:'allow',operation_id:'op'},wait],[{command:'readonly',site:'https://x.test/',enabled:false},wait],
    [{command:'readonly',site:'https://x.test/',enabled:null},wait]];
  for(const [args,expected] of cases){
    assert.equal(context.receive({command:'sites',arguments:args},sender,()=>{}),true);
    assert.equal(timers.at(-1),expected,JSON.stringify(args));
    assert.deepEqual(JSON.parse(JSON.stringify(posted.at(-1).arguments)),args);
  }
});
