// Execute only extension UI code against a plain in-memory DOM; no browser or process.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

class Element{
  constructor(){this.children=[];this.listeners={};this.hidden=false;this.textContent='';this.attributes={};}
  append(...items){this.children.push(...items);}
  replaceChildren(...items){this.children=items;}
  setAttribute(name,value){this.attributes[name]=value;}
  addEventListener(name,callback){this.listeners[name]=callback;}
  async click(){return this.listeners.click();}
}
async function fixture(){
  const elements=Object.fromEntries(['popups','popup-controls','status','stop'].map(id=>['#'+id,new Element()]));
  const state={popups:[{tab:8,control:'first',title:'Popup <fixture>',url:'http://popup.test/first'},{tab:9,control:'second',title:'Second popup',url:'http://popup.test/second'}],calls:[],interval:null,closed:false};
  const sendMessage=async message=>{
    state.calls.push(message);
    if(message.command==='popup_status')return {popups:state.popups.slice()};
    if(message.command==='stop_popup'){if(state.staleOnce){state.staleOnce=false;return {stopped:false,stale:true};}state.popups=state.popups.filter(row=>row.tab!==message.tab||row.control!==message.control);return {stopped:true};}
    if(message.command==='stop'){state.popups=[];return {stopped:true};}
    throw Error('Unexpected UI command');
  };
  vm.runInNewContext(fs.readFileSync('control/chrome/extension/popup.js','utf8'),{document:{querySelector:id=>elements[id],createElement:()=>new Element()},chrome:{runtime:{sendMessage}},window:{close:()=>{state.closed=true}},setInterval:callback=>{state.interval=callback;}});
  for(let n=0;n<10;n++)await Promise.resolve();
  return {elements,state};
}
test('action popup lists every controlled popup using text and sends an individual epoch-bound Stop',async()=>{
  const {elements,state}=await fixture(),list=elements['#popups'];
  assert.equal(list.children.length,2);assert.equal(list.children[0].children[0].textContent,'Popup <fixture>');
  assert.equal(list.children[0].children[1].textContent,'http://popup.test/first');
  assert.equal(list.children[0].children[2].attributes['aria-label'],'Stop control of Popup <fixture>');
  await list.children[0].children[2].click();
  assert.deepEqual(JSON.parse(JSON.stringify(state.calls.find(row=>row.command==='stop_popup'))),{command:'stop_popup',tab:8,control:'first'});
  assert.equal(list.children.length,1);assert.equal(list.children[0].children[0].textContent,'Second popup');
  assert.match(elements['#status'].textContent,/stays open/);assert.equal(state.closed,false);
  await list.children[0].children[2].click();assert.equal(list.children.length,0);assert.equal(elements['#popup-controls'].hidden,true);
});
test('unchanged polling preserves the focused Stop node and the global Stop remains available',async()=>{
  const {elements,state}=await fixture(),row=elements['#popups'].children[0];
  await state.interval();assert.equal(elements['#popups'].children[0],row);
  await elements['#stop'].click();assert.equal(elements['#popups'].children.length,0);assert.equal(elements['#popup-controls'].hidden,true);assert.match(elements['#status'].textContent,/Control ended/);
});


test('a stale individual Stop reports changed control and refreshes an enabled current Stop',async()=>{
  const {elements,state}=await fixture(),oldStop=elements['#popups'].children[0].children[2];
  state.popups[0]={...state.popups[0],control:'replacement'};state.staleOnce=true;
  await oldStop.click();assert.equal(state.popups.length,2);assert.match(elements['#status'].textContent,/Control changed/);assert.doesNotMatch(elements['#status'].textContent,/control ended/);
  const currentStop=elements['#popups'].children[0].children[2];assert.notEqual(currentStop,oldStop);assert.ok(!currentStop.disabled);
  await currentStop.click();assert.equal(state.popups.length,1);assert.equal(state.calls.filter(row=>row.command==='stop_popup').at(-1).control,'replacement');
});
