// Brief 28a, groups 14 and 15 without a browser: the act fixture pages as fixture.mjs
// serves them, each page's script run against a stand-in DOM (with its handlers, its
// timers and the fixture's mutations), and act-matrix.mjs's outline helpers.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {fixtures} from '../chrome/ci/fixture.mjs';
import {actPage,actUrl,ACT_MARK,LONG_NOTE,LARGE_FIELDS,STAGE_MS,longNote} from '../chrome/ci/act-fixtures.mjs';
import {HOSTILE} from '../chrome/ci/efficiency-fixtures.mjs';
import {lineOf,refOf} from '../chrome/ci/act-matrix.mjs';

const PAGES=[['steps',''],['f4',''],['large','&mode=fields'],['large','&mode=text'],['far',''],['far','&mode=scroll'],['fingerprint',''],
  ...HOSTILE.map((_,index)=>['hostile','&index='+index]),['look',''],['look','&mode=landed'],['loaded',''],['loaded','&mode=busy'],['address',''],
  ['links',''],['fold',''],['stage',''],['stage','&mode=boundary'],['plain',''],['plain','&mode=empty'],['typed',''],
  ['owner-draft',''],['input-dialog',''],['media',''],['popup',''],['popup','&mode=child']];
const lastScript=html=>html.slice(html.lastIndexOf('<script>')+8,html.lastIndexOf('</script>'));

// A stand-in DOM: every property is another stand-in, every call returns one, and what a
// page registers (on… handlers, addEventListener, timers, EventSource) is kept to be run.
// A list holds NODES stand-ins, each (and what hangs off it) reading as its own index, so
// a handler that picks its work by a node's data runs every branch.
const NODES=10;
function standIn(){
  const handlers=[],timers=[];
  const make=(path,index='')=>{
    const target=function(){};
    return new Proxy(target,{
      get(_,key){
        if(key===Symbol.toPrimitive)return ()=>index;
        if(key===Symbol.iterator)return function*(){for(let item=0;item<NODES;item++)yield make(path+'['+item+']',String(item));};
        if(key==='then')return undefined;
        if(key==='length')return NODES;
        return make(path+'.'+String(key),index);
      },
      set(_,key,value){if(typeof value==='function'&&String(key).startsWith('on'))handlers.push({path:path+'.'+String(key),fn:value});return true;},
      apply(_,__,args){
        if(path.endsWith('.addEventListener'))handlers.push({path,fn:args[1]});
        return make(path+'()',index);
      },
      construct(){return make(path+'(new)',index);},
    });
  };
  const location={href:'http://fixture.test:8765/?case=act-x&id=one',search:'?case=act-x&id=one',pathname:'/'};
  const context={document:make('document'),window:make('window'),history:make('history'),navigator:make('navigator'),location,
    fetch:make('fetch'),alert:make('alert'),EventSource:make('EventSource'),HTMLFormElement:make('HTMLFormElement'),
    confirm:make('confirm'),prompt:make('prompt'),
    setTimeout:fn=>{timers.push(fn);return timers.length;},setInterval:fn=>{timers.push(fn);return timers.length;},
    addEventListener:(_,fn)=>handlers.push({path:'addEventListener',fn}),URL,JSON,Math,Date,Number,String,Object,Array,encodeURIComponent,Error,console:{log(){}}};
  context.globalThis=context;
  return {context:vm.createContext(context),handlers,timers};
}
function exercise(script,changes=[]){
  const {context,handlers,timers}=standIn();
  vm.runInContext(script,context);
  const event={data:'{}',target:context.document,key:'Enter',detail:1,preventDefault(){},isTrusted:true};
  for(const change of changes)if(typeof context.actChange==='function')context.actChange(change);
  for(let round=0;round<3;round++){
    for(const {fn} of handlers.splice(0))fn({...event,data:JSON.stringify({change:changes[0]||'act-none',nonce:'1'})});
    for(const fn of timers.splice(0))fn();
  }
  return context;
}

test('every act page is served with a script that runs, with its handlers, timers and changes',async()=>{
  const fixture=await fixtures({port:0,secondPort:0});const base='http://127.0.0.1:'+fixture.port;
  try{
    for(const [name,query] of PAGES){
      const response=await fetch(base+'/?case=act-'+name+'&id=t1'+query);assert.equal(response.status,200,name+query);
      const html=await response.text(),script=lastScript(html);
      assert.doesNotMatch(script,/<\/script|<!--/i,name+query);
      const changes={f4:['act-rename','act-revalue','act-swap','act-chosen'],address:['act-session'],stage:['act-start']}[name]||[];
      exercise(script,changes);
      // The pages a case changes while an approval waits take the fixture's mutations.
      assert.equal(script.includes("new EventSource('/events?id='"),['f4','address','stage'].includes(name),name);
    }
    assert.equal((await fetch(base+'/?case=act-unknown&id=t1')).status,404);
  }finally{fixture.close();}
});

test('the act pages carry what their cases count on',()=>{
  const page=(name,query='')=>actPage(new URL(actUrl(name,'t2',query)));
  const steps=page('steps').body;
  for(const part of ['<input name="alpha">','action="/receive?case=act-send-t2"','<option value="c" disabled>Cherry</option>','Banana  split','id="draft">Load draft','id="later">Notice later'])assert.ok(steps.includes(part),part);
  assert.equal((steps.match(/>Twin</g)||[]).length,2,'two options share a label');
  const f4=page('f4');assert.match(f4.body,/action="\/receive\?case=efficiency-f4-t2"/);assert.equal((f4.body.match(/<option value="c\d+"/g)||[]).length,200);
  assert.match(page('plain').body,/<textarea name="note">/);
  assert.doesNotMatch(page('plain','&mode=empty').body,/<input|<textarea|<select|contenteditable/);
  assert.match(page('plain','&mode=empty').body,/>Press me<\/button>/);
  assert.equal((page('large','&mode=fields').body.match(/<input name="item\d+"/g)||[]).length,LARGE_FIELDS);
  assert.ok(page('large','&mode=text').body.includes('>'+longNote()+'</textarea>'));assert.equal(longNote().length,LONG_NOTE);
  assert.match(page('far').body,/height:10000px.*Far button.*overflow:auto.*Inner button/);
  const print=page('fingerprint');assert.ok(print.body.includes('>'+longNote()+'</textarea>'));
  for(const name of ['Change path','Change query','Change options','Tick it','Expand menu','Change end','Enable','Require','Move','Swap row'])assert.ok(print.body.includes('>'+name+'</button>'),name);
  // Hostile text comes by its index, never through an address: lone surrogates can't travel there.
  HOSTILE.forEach((text,index)=>assert.ok(page('hostile','&index='+index).script.includes(JSON.stringify(text).replaceAll('<','\\u003c')),'string '+index));
  const address=page('address').body.replaceAll('&amp;','&');
  for(const part of ['/receive?case=act-addrlink-t2&q=red+shoes&page=2&code='+ACT_MARK,'/receive?case=act-addrsend-t2&q=red+shoes&page=2&session='+ACT_MARK])assert.ok(address.includes(part),part);
  assert.ok(page('address').script.includes('report("addrseen",{href:location.href})'));
  assert.equal((page('fold').body.match(/<li>/g)||[]).length,120);assert.match(page('fold').body,/Archived note 100 <button type="button" id="delete">Delete<\/button>/);
  assert.ok(page('stage').script.includes(','+STAGE_MS+');'));assert.doesNotMatch(page('stage').script,/^let stage=0;setInterval/m,'the clock starts at act-start');
  assert.match(page('links').body,/href="\/receive\?case=act-linkdelete-t2">Delete<.*href="\/receive\?case=act-linkunsub-t2">Unsubscribe<.*href="\/receive\?case=act-linkplain-t2">Read more</);
  assert.equal(actPage(new URL('http://fixture.test/?case=act-nothing')),null);
});

test('an outline line and its reference are found by the words the line starts with',()=>{
  const outline='h1 "Steps"\nform → POST fixture.test kqtvm1\n  textbox "Alpha" = "x" kqtvm2\n  textbox "Alpha two" kqtvm3\n  button "Send" kqtvm40';
  assert.equal(refOf(outline,'textbox "Alpha"'),'kqtvm2');assert.equal(refOf(outline,'button "Send"'),'kqtvm40');
  assert.equal(lineOf(outline,'form'),'form → POST fixture.test kqtvm1');
  assert.equal(refOf('button "Delete" kqtvm41 · in list "Archive"','button "Delete"'),'kqtvm41');
  assert.equal(refOf('button "Send" kqtvm42 · in form','button "Send"'),'kqtvm42');
  assert.throws(()=>refOf(outline,'h1 "Steps"'),/a reference on/);assert.throws(()=>lineOf(outline,'link'),/a line starting with link/);
});

test('every act case name is written once and each sits in the group its evidence proves',()=>{
  const source=fs.readFileSync(new URL('../chrome/ci/act-matrix.mjs',import.meta.url),'utf8');
  const names=[...source.matchAll(/await check\('([^']+)'/g)].map(match=>match[1]);
  assert.equal(new Set(names).size,names.length);assert.ok(names.length>=20);
  for(const name of names)assert.match(name,/^(GROUP [137] BRIEF28A|ACT BRIEF28A) /,name);
  // Run first, reported afterwards, in order; a case's own lines never read as a reported PASS.
  assert.ok(source.includes("for(const row of results)await report(row.name,async()=>{if(row.error)throw row.error;});"));
  assert.doesNotMatch(source,/console\.log\([^)]*'PASS'/);
  // The restarts come last.
  assert.match(names.at(-1),/before a restart/);
});
