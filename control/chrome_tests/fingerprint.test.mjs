// Brief 28a, item 2: the reader's one fingerprint function, through the three
// commands that return it (`outline` for every node, `facts` for the target,
// `observe` for the element acted on), and item 5's `reveal`. Run in a VM
// against outline-dom's DOM doubles; a protected value's getter throws, so a
// test fails when the fingerprint reads one.
import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import vm from 'node:vm';

import {page} from './outline-dom.mjs';

// The raw outline (outline-dom's helper drops the fingerprints for brief 28's shape tests).
function nodes(f){const result=f.run({command:'outline'});assert.equal(result.ok,true,JSON.stringify(result));return result.data.nodes;}
function node(f,match){const found=nodes(f).filter(match);assert.equal(found.length,1,JSON.stringify(found));return found[0];}
// One element's digest from all three commands; they must agree.
function digest(f,match){
  const outlined=node(f,match),key='e'+outlined.id;
  const facts=f.run({command:'facts',element:key}),observed=f.run({command:'observe',element:key});
  assert.equal(facts.ok,true,JSON.stringify(facts));assert.equal(observed.ok,true,JSON.stringify(observed));
  assert.match(outlined.fingerprint,/^[0-9a-f]{32}$/);
  assert.equal(facts.data.fingerprint,outlined.fingerprint,'facts and outline agree');
  assert.equal(observed.data.change.fingerprint,outlined.fingerprint,'observe and outline agree');
  assert.equal(facts.data.reader,observed.data.change.reader,'the reader instance comes with facts and observe');
  assert.equal(observed.data.change.document,facts.data.document);assert.equal(observed.data.change.element,key);
  return outlined.fingerprint;
}
const named=name=>item=>item.name===name;
const sha=text=>createHash('sha256').update(text).digest('hex').slice(0,32);

test('28a fingerprint: outline, facts and observe give one digest for each kind of element',()=>{
  const f=page(h=>[h('main',{},
    h('a',{href:'/docs?q=red+shoes#top',title:'Opens here'},'Docs'),
    h('label',{},'Note ',h('input',{name:'note',value:'hello'})),
    h('label',{},h('input',{type:'checkbox',name:'news',checked:''}),' News'),
    h('label',{},'Country ',h('select',{name:'country'},h('option',{value:'de',selected:''},'Germany'),h('option',{value:'fr'},'France'))),
    h('div',{role:'dialog','aria-label':'Confirm'},h('button',{},'OK')),
    h('div',{contenteditable:'true','aria-label':'Editor'},'Draft text'),
    h('label',{},'Password ',h('input',{type:'password',value:'never'})),
    h('button',{'aria-expanded':'false'},'Menu'))]);
  for(const name of ['Docs','Note','News','Country','OK','Editor','Password','Menu'])digest(f,named(name));
});

test('28a fingerprint: a value the line cuts and a link address the line leaves out count whole',()=>{
  const f=page(h=>[h('label',{},'Notes ',h('textarea',{value:'n'.repeat(500)})),h('a',{href:'/reset/abc?code=sesame'},'Docs')]);
  const field=f.body.childNodes[0].childNodes[1],link=f.body.childNodes[1];
  const notes=digest(f,named('Notes')),docs=digest(f,named('Docs'));
  field.attrs.value='n'.repeat(400)+'X'+'n'.repeat(99);                  // past the 200 characters a line shows
  assert.notEqual(digest(f,named('Notes')),notes);
  for(const href of ['/reset/abc?code=other','/reset/abd?code=sesame','/reset/abc?code=sesame#x']){
    link.attrs.href=href;assert.notEqual(digest(f,named('Docs')),docs,href);
  }
  link.attrs.href='/reset/abc?code=sesame';assert.equal(digest(f,named('Docs')),docs,'the same address gives the same digest');
  link.attrs.target='_blank';assert.notEqual(digest(f,named('Docs')),docs,'where the link opens is part of where it leads');
});

test('28a fingerprint: what an element means moves it',()=>{
  const f=page(h=>[h('form',{'aria-label':'F'},
    h('label',{},'Note ',h('input',{name:'note',value:'v'})),
    h('label',{},h('input',{type:'checkbox',name:'news'}),' News'),
    h('label',{},'Country ',h('select',{},h('option',{value:'de',selected:''},'Germany'),h('option',{value:'fr'},'France'))),
    h('button',{'aria-expanded':'false',title:'Hint'},'Menu'),
    h('div',{role:'tab','aria-selected':'false'},'Tab'),
    h('input',{type:'submit',value:'Save'}))]);
  const form=f.body.childNodes[0],[note,news,country,menu,tab]=[0,1,2].map(index=>form.childNodes[index].childNodes.find(child=>child.nodeType===1)).concat([form.childNodes[3],form.childNodes[4]]);
  const cases=[
    ['Note',()=>{note.attrs.value='w';}],
    ['Note',()=>{note.attrs['aria-label']='Other';},'Other'],
    ['News',()=>{news.attrs.checked='';}],
    ['Country',()=>{country.childNodes[1].attrs.selected='';delete country.childNodes[0].attrs.selected;}],
    ['Country',()=>{country.childNodes[1].attrs.value='fx';}],
    ['Country',()=>{country.childNodes[1].childNodes[0].textContent='Frankreich';}],
    ['Country',()=>{country.append(f.h('option',{value:'it'},'Italy'));}],
    ['Menu',()=>{menu.attrs['aria-expanded']='true';}],
    ['Menu',()=>{menu.attrs.title='Other hint';}],
    ['Menu',()=>{menu.attrs.role='link';}],
    ['Tab',()=>{tab.attrs['aria-selected']='true';}],
  ];
  for(const [name,change,after=name] of cases){
    const before=digest(f,named(name));change();
    assert.notEqual(digest(f,named(after)),before,name+' '+change);
  }
});

test('28a fingerprint: position, enabled, required and invalid leave it, and so does a neighbour',()=>{
  const f=page(h=>[h('main',{},h('p',{},'Around the field'),h('label',{},'Note ',h('input',{name:'note',value:'v'})),h('button',{},'Save'))]);
  const main=f.body.childNodes[0],field=main.childNodes[1].childNodes[1],button=main.childNodes[2];
  const note=digest(f,named('Note')),save=digest(f,named('Save'));
  field.box={x:5,y:900,width:40,height:12};button.box={x:-300,y:-300,width:1,height:1};   // moved, off screen
  for(const attribute of ['disabled','required'])field.attrs[attribute]='',button.attrs[attribute]='';
  field.attrs['aria-invalid']='true';button.attrs['aria-invalid']='true';
  main.childNodes[0].childNodes[0].textContent='Other text around it';                      // a neighbour changed
  main.childNodes[0].append(f.h('a',{href:'/elsewhere'},'New link'));
  assert.equal(digest(f,named('Note')),note);assert.equal(digest(f,named('Save')),save);
});

test('28a fingerprint: outline looks up each form\'s implicit submitter once, and finds what facts finds',()=>{
  const f=page(h=>[h('form',{'aria-label':'A'},h('input',{'aria-label':'Q',value:'v'}),h('input',{type:'submit',value:'Go'})),
    h('form',{'aria-label':'B'},h('input',{'aria-label':'Q',value:'v'}))]);
  const [first,second]=f.body.childNodes;
  for(const form of [first,second])for(const control of form.childNodes)control.form=form;
  const digests=nodes(f).filter(named('Q')).map(item=>{
    const facts=f.run({command:'facts',element:'e'+item.id}).data;
    assert.equal(facts.fingerprint,item.fingerprint,'outline (looked up once) and facts (looked up for the element) agree');
    return item.fingerprint;
  });
  assert.notEqual(digests[0],digests[1],'Enter submits the first form through its button, and not the second');
});

test('28a fingerprint: the page dialog it sits in is part of it',()=>{
  const f=page(h=>[h('div',{role:'dialog','aria-label':'First'},h('button',{},'OK')),h('div',{role:'dialog','aria-label':'Second'},h('button',{},'OK')),h('button',{},'OK')]);
  const all=nodes(f).filter(named('OK'));assert.equal(all.length,3);
  assert.equal(new Set(all.map(item=>item.fingerprint)).size,3,'the same button in another dialog, or in none, means something else');
});

test('28a fingerprint: a password-kind field is fingerprinted only by its kind, and nothing of it is read',()=>{
  const f=page(h=>[h('label',{},'Password ',h('input',{type:'password',value:'never'})),
    h('label',{},'One-time code ',h('input',{name:'one_time',autocomplete:'one-time-code',value:'123456',$secret:true})),
    h('label',{},'Secret ',h('textarea',{value:'key',$secret:true,'aria-label':'Recovery phrase'}))]);
  const kept=nodes(f).filter(item=>item.role==='password');
  assert.equal(kept.length,3);
  for(const item of kept){
    assert.equal(item.fingerprint,sha('["password"]'),'the kind alone');
    assert.equal(f.run({command:'facts',element:'e'+item.id}).data.fingerprint,item.fingerprint);
    assert.equal(f.run({command:'observe',element:'e'+item.id}).data.change?.fingerprint??item.fingerprint,item.fingerprint);
  }
  f.body.childNodes[0].childNodes[1].attrs.value='changed';f.body.childNodes[0].childNodes[0].textContent='Passwort ';
  assert.equal(node(f,item=>item.role==='password'&&item.name==='Passwort').fingerprint,sha('["password"]'));
});

test('28a fingerprint: an unread field is fingerprinted as unread, and its digest does not change with its value',()=>{
  const f=page(h=>[h('label',{},'Draft ',h('textarea',{value:'first',$secret:true})),h('label',{},'Note ',h('input',{value:'',$secret:true}))],{watched:false});
  const draft=f.body.childNodes[0].childNodes[1],note=f.body.childNodes[1].childNodes[1];
  const before=[digest(f,named('Draft')),digest(f,named('Note'))];
  assert.ok(nodes(f).filter(item=>['Draft','Note'].includes(item.name)).every(item=>item.unread));
  draft.attrs.value='second, longer';note.attrs.value='now filled';                   // the getters throw if read
  assert.deepEqual([digest(f,named('Draft')),digest(f,named('Note'))],before);
});

test('28a fingerprint: it hashes the repaired text; a changed repaired fact still moves it',()=>{
  const digestOf=(label,value='v')=>{const f=page(h=>[h('input',{'aria-label':label,value})]);return digest(f,item=>item.role==='textbox');};
  const lone=digestOf('Note \ud800'),other=digestOf('Note \udc00'),repaired=digestOf('Note �');
  assert.equal(lone,repaired,'a lone surrogate hashes as U+FFFD, in outline, facts and observe alike');
  assert.equal(other,repaired);
  assert.notEqual(digestOf('Note 😀'),digestOf('Note ��'),'a valid pair stays itself');
  assert.notEqual(digestOf('Mote \ud800'),lone,'a visible change moves it');
  assert.equal(digestOf('Note','a\udbff'),digestOf('Note','a�'),'values are repaired too');
  assert.notEqual(digestOf('Note','b\udbff'),digestOf('Note','a\udbff'));
});

test('28a reveal: a target whose centre is off screen is scrolled to the centre at once, inside control',()=>{
  const f=page(h=>[h('button',{},'Far'),h('button',{},'Near'),h('label',{},'Password ',h('input',{type:'password'}))]);
  nodes(f);
  const [far,near]=f.body.childNodes;far.box={x:10,y:400,width:20,height:10};near.box={x:10,y:10,width:20,height:10};
  assert.match(f.run({command:'reveal',element:'e1',generation:'g'}).error,/^stale_reference: control ended/,'no reveal outside control');
  assert.equal(f.run({command:'set_control',generation:'g'}).ok,true);
  assert.deepEqual(f.run({command:'reveal',element:'e1',generation:'g'}),{ok:true,data:{revealed:true}});
  assert.equal(JSON.stringify(far.scrolled),JSON.stringify([{block:'center',inline:'center',behavior:'instant'}]));
  assert.deepEqual(f.run({command:'reveal',element:'e2',generation:'g'}),{ok:true,data:{revealed:false}});
  assert.equal(near.scrolled,undefined,'a target on screen is left where it is');
  near.box={x:10,y:95,width:20,height:20};                                               // its centre is below the screen
  assert.equal(f.run({command:'reveal',element:'e2',generation:'g'}).data.revealed,true);
  const secret=node(f,item=>item.role==='password');
  assert.match(f.run({command:'reveal',element:'e'+secret.id,generation:'g'}).error,/^owner_signin:/);
  assert.match(f.run({command:'reveal',element:'e99',generation:'g'}).error,/^stale_reference:/);
});

// background.js `input`: where the reveal runs, and for which inputs.
function inputFixture(){
  let code=fs.readFileSync('control/chrome/extension/background.js','utf8').replace("import {POLICY} from './policy.js';",'');
  code=code.slice(0,code.indexOf('async function connect()'));
  const context=vm.createContext({POLICY:{holdMs:100},chrome:{},URL,TextEncoder,performance,crypto:{randomUUID:()=> 'fixture-session'},setTimeout,clearTimeout});
  vm.runInContext(code,context);
  const run=source=>vm.runInContext(source,context);
  run(`excludedHosts=[];controlled.set(7,{epoch:'epoch'});dispatchEpoch='epoch';globalThis.log=[];
    requireTab=async()=>({url:'https://fixture.test/',title:'Page'});
    safeDestination=()=>{};holdDefaults=async()=>{};armedDocument=()=>{};expireDefaults=()=>{};
    finishFrames=async()=>false;collectSteps=async()=>[];observation=async()=>({});readyDialog=async()=>null;
    chrome.tabs={get:async()=>({active:true})};
    chrome.webNavigation={getAllFrames:async()=>[{frameId:0,parentFrameId:-1,documentId:'native',url:'https://fixture.test/'}]};
    globalThis.target={element:'e1',role:'button',name:'Go',states:{checked:false},box:{x:1,y:1,width:10,height:10}};
    facts=async()=>{log.push('facts');return {session,tab:7,control:'epoch',url:'https://fixture.test/',title:'Page',dialog:null,
      frames:[{frame:0,parent:-1,document:'doc',browser_document:'native',url:'https://fixture.test/',title:'Frame',target,form:null,selected_files:[],editable:[],embeds:[]}]};};
    // background.js' own content(): what it sends the readers, and its effect flag.
    chrome.tabs.sendMessage=async(tab,{command,...parameters})=>{log.push(command==='reveal'?'reveal '+JSON.stringify(parameters):command);return {ok:true,data:command==='hit'?{hit:true}:{}};};
    pointer=async()=>{log.push('hit');return {x:2,y:2};};cdp=async(tab,method)=>{log.push(method);return {};};`);
  return {run,dispatch:input=>run(`dispatch({name:'input',tab:7,reference:{session,tab:7,frame:0,document:'doc',element:'e1'},input:${JSON.stringify(input)}})`)};
}

test('28a reveal in input: after the frames are armed, before the last facts read and brief 20\'s hit test',async()=>{
  for(const input of [{verb:'click'},{verb:'scroll',x:0,y:200},{verb:'check',checked:true}]){
    const f=inputFixture();await f.dispatch(input);
    const log=JSON.parse(f.run('JSON.stringify(log)'));
    const reveal=log.indexOf('reveal {"element":"e1","generation":"epoch"}');
    assert.ok(reveal>log.lastIndexOf('arm')&&log.lastIndexOf('arm')>=0,JSON.stringify(log));
    assert.ok(reveal<log.lastIndexOf('facts')&&log.lastIndexOf('facts')<log.indexOf('hit'),JSON.stringify(log));
    assert.equal(log.filter(entry=>entry.startsWith('reveal')).length,1);
    assert.ok(log.indexOf('Input.dispatchMouseEvent')>log.indexOf('hit'),'the input follows, as before');
  }
  for(const input of [{verb:'fill',text:'x'},{verb:'press',key:'Enter'},{verb:'check',checked:false}]){
    const f=inputFixture();await f.dispatch(input);
    assert.ok(!JSON.parse(f.run('JSON.stringify(log)')).some(entry=>entry.startsWith('reveal')),JSON.stringify(input));
  }
  const f=inputFixture();f.run("target.password=true");
  await assert.rejects(f.dispatch({verb:'click'}),/^Error: owner_signin:/);
  assert.ok(!JSON.parse(f.run('JSON.stringify(log)')).some(entry=>entry.startsWith('reveal')),'a password field is never scrolled to');
});

test('28a reveal in input: a refusal after the reveal still says nothing was dispatched',async()=>{
  const f=inputFixture();
  // The last facts read finds the element gone, as facts() says it.
  f.run("let reads=0;const first=facts;facts=async()=>{const value=await first();if(++reads===2)throw Error('stale_reference: element is gone; read again');return value;};");
  await assert.rejects(f.dispatch({verb:'click'}),/^Error: stale_reference: element is gone/);
  assert.ok(JSON.parse(f.run('JSON.stringify(log)')).some(entry=>entry.startsWith('reveal')));
  assert.equal(f.run('effectStarted'),false,'the scroll is not the input: no effect flag');
  assert.ok(!JSON.parse(f.run('JSON.stringify(log)')).includes('Input.dispatchMouseEvent'));
});
