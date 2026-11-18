// Brief 28, group 14's password fixtures without a browser: each page as the
// fixture server serves it, with its script compiled, and the plain page's
// script run against a small document, so every field is seen losing what
// protected it. The browser cases are control/chrome/ci/unread-matrix.mjs.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {fixtures} from '../chrome/ci/fixture.mjs';
import {unreadPage,PASSWORD,PROBE,PLAIN_KINDS,PLAIN_ROOTS,NAMED,TYPED_KINDS,LIMIT,LATE_DRAFT} from '../chrome/ci/unread-fixtures.mjs';
import {REQUIRED} from '../chrome/ci/verdicts.mjs';

const pageOf=query=>unreadPage(new URL('http://fixture.test:8765/?case=password-unread&'+query));
const count=(text,part)=>text.split(part).length-1;

test('the fixture server serves the unread pages, the late one with its change channel',async()=>{
  const fixture=await fixtures({port:0,secondPort:0}),base='http://127.0.0.1:'+fixture.port;
  const served=async query=>{const response=await fetch(base+'/?case=password-unread&'+query);return {status:response.status,html:await response.text()};};
  try{
    const plain=await served('mode=plain&id=one');
    assert.equal(plain.status,200);assert.ok(plain.html.includes('http://second.test:8766/?case=password-unread&mode=plain-child&id=one'));
    assert.ok(!plain.html.includes('EventSource'),'the plain page needs no change channel');
    const child=await served('mode=plain-child&id=one');assert.equal(child.status,200);assert.ok(!child.html.includes('<iframe'));
    for(const variant of ['password','form','moved','known']){
      const late=await served('mode=late&id=two&variant='+variant);assert.equal(late.status,200,variant);
      assert.ok(late.html.includes("new EventSource('/events?id='+\"two\")"),'the driver upgrades the component through the change channel: '+variant);
      assert.ok(late.html.includes('<late-box></late-box>'));
    }
    for(const query of ['mode=late&id=two','mode=late&id=two&variant=other','mode=other&id=two'])assert.equal((await served(query)).status,404,query);
  }finally{fixture.close();}
});

test('every unread page\'s script compiles',()=>{
  for(const query of ['mode=plain&id=a','mode=plain-child&id=a','mode=late&id=a&variant=password','mode=late&id=a&variant=form','mode=late&id=a&variant=moved','mode=late&id=a&variant=known']){
    const {body,script}=pageOf(query);assert.ok(body.length>0,query);
    assert.doesNotThrow(()=>new vm.Script(script),query);
    assert.ok(!script.includes('</script'),'the script stays inside its element: '+query);
  }
});

test('the plain page makes each of its nine kinds plain a task after it wrote them, in three roots',()=>{
  const {body,script}=pageOf('mode=plain&id=a');
  // A document that keeps what the script does: three roots, the forms written into them, and one delayed task.
  const written=[],tasks=[],reports=[];
  const fieldsOf=markup=>[...markup.matchAll(/<(input|textarea|div)\b([^>]*)>/g)].filter(match=>match[2].includes('data-plain')).map(match=>{
    const attributes=new Map([...match[2].matchAll(/([a-z-]+)="([^"]*)"/g)].map(part=>[part[1],part[2]]));
    return {tag:match[1],attributes,removed:[],getAttribute:key=>attributes.get(key)??null,removeAttribute(key){this.removed.push(key);attributes.delete(key);},
      get type(){return attributes.get('type')||'text';},set type(value){attributes.set('type',value);}};
  });
  const root=markup=>{const state={fields:markup?fieldsOf(markup):[]};
    return {append(form){state.fields.push(...fieldsOf(form.innerHTML));written.push(form.innerHTML);},querySelectorAll:()=>state.fields,attachShadow(){return root('');},state};};
  const light=root(''),open=root(''),closed=root(''),page=root(body);
  const document={querySelector:key=>({'#light':light,'#open':open,'#closed':closed}[key]),createElement:()=>({innerHTML:'',textContent:''}),body:{append(){}},
    querySelectorAll:()=>[...light.state.fields,...page.state.fields]};
  vm.runInNewContext(script,{document,setTimeout:fn=>tasks.push(fn),fetch:(url,options)=>reports.push(JSON.parse(options.body)),JSON});
  assert.equal(written.length,PLAIN_ROOTS);assert.equal(tasks.length,1,'the fields are made plain in a later task');
  for(const markup of written){
    assert.equal(count(markup,'aria-label="Code"'),PLAIN_KINDS);assert.equal(count(markup,PASSWORD),PLAIN_KINDS,'each holds the known password');
    assert.equal(count(markup,'type="password"'),4);assert.equal(count(markup,'-webkit-text-security:disc'),3,'two inline masks and the class rule');
  }
  const before=light.state.fields.map(field=>field.type);assert.equal(before.filter(type=>type==='password').length,4);
  assert.deepEqual(reports,[]);tasks[0]();
  assert.deepEqual(reports,[{id:'a',phase:'plain-ready',frame:'top'}]);
  for(const fields of [light.state.fields,page.state.fields])for(const field of fields){
    const how=field.getAttribute('data-plain');
    if(['autocomplete','style','class'].includes(how)){assert.deepEqual(field.removed,[how]);assert.equal(field.getAttribute(how),null);}
    else assert.equal(field.type,how);
    assert.notEqual(field.type,'password');
  }
  assert.deepEqual(light.state.fields.map(field=>field.getAttribute('data-plain')),['text','search','email','url','autocomplete','style','class','style','class']);
  // The page's own part: the named fields, the kinds an unwatched document shows, and the limit's two fields labelled "Value".
  for(const label of NAMED)assert.ok(body.includes('>'+label+'<')||body.includes('aria-label="'+label+'"'),label);
  assert.ok(body.includes('name="otp"')&&body.includes('name="secret_value"')&&!body.includes('autocomplete='));
  for(const [type,value] of Object.entries(TYPED_KINDS))assert.ok(body.includes('<input type="'+type+'" aria-label="Kind '+type+'" value="'+value+'">'),type);
  assert.equal(count(body,'aria-label="Value"'),2);assert.equal(count(body,LIMIT),1);
  assert.equal(page.state.fields.length,2,'the limit\'s two fields are unmasked with the others');
  // The mutation check's page: the same nine fields with the probe value, no frame, and the password nowhere.
  const probe=pageOf('mode=plain&id=a&probe=1');
  assert.ok(!probe.body.includes(PASSWORD)&&!probe.script.includes(PASSWORD)&&!probe.body.includes('<iframe'));
  assert.equal(count(probe.script,PROBE),PLAIN_KINDS);assert.equal(count(probe.body,PROBE),1,'the named field');assert.ok(probe.body.includes('name="otp"')&&probe.body.includes('aria-label="Note"'));assert.equal(count(probe.script,'aria-label=\\"Code\\"'),PLAIN_KINDS);
});

test('the late pages hold what their cases need, and nothing typed before the owner comes',()=>{
  const password=pageOf('mode=late&id=a&variant=password');
  for(const label of ['Password','Code','Notes','Comment'])assert.ok(password.script.includes('aria-label=\\"'+label+'\\"'),label);
  assert.equal(count(password.script,'data-step aria-label'),3,'three typed steps in the root');
  assert.ok(!password.script.includes(PASSWORD),'the owner types the password; the page holds none in its late root');
  const form=pageOf('mode=late&id=a&variant=form'),known=pageOf('mode=late&id=a&variant=known'),moved=pageOf('mode=late&id=a&variant=moved');
  for(const page of [form,moved]){assert.ok(page.script.includes('name=\\"draft\\" data-step'));assert.ok(!page.script.includes(PASSWORD)&&!page.script.includes(LATE_DRAFT));}
  assert.ok(known.script.includes('type=\\"password\\" aria-label=\\"Secret\\" value=\\"'+PASSWORD+'\\"'));assert.ok(!known.script.includes('name=\\"draft\\"'));
  assert.ok(moved.body.includes('action="/receive?case=a-other"')&&moved.body.includes('Send other'));assert.ok(!form.body.includes('Send other'));
  for(const page of [form,known,moved])assert.ok(page.body.includes('<button type="button" id="start">Continue</button>'));
});

test('the password cases are named in the inventory where the brief puts them',()=>{
  const names=[...fs.readFileSync('control/chrome/ci/unread-matrix.mjs','utf8').matchAll(/await check\('([^']+)'/g)].map(match=>match[1]);
  assert.equal(names.length,3);
  assert.deepEqual(names.filter(name=>REQUIRED[7].includes(name)).length,2,'two cases in group 7, password_exclusion');
  assert.deepEqual(names.filter(name=>REQUIRED[3].includes(name)),['GROUP 3 BRIEF28 a form holding an unread field is refused unasked for a click Enter and a page submission'],'the refused forms in group 3, binding');
  assert.ok(REQUIRED[7].includes('GROUP 7 BRIEF28 the new read holds no password in any form of read'));
});
