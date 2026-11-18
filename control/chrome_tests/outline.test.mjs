// Brief 28, item 1: the reader's `outline`, `options` and `page_state`, run in
// a VM against a small tree of DOM doubles. A protected value's getter throws,
// so a test fails when the reader touches one.
import test from 'node:test';
import assert from 'node:assert/strict';
import {H1_REFERENCES} from '../chrome/ci/efficiency-fixtures.mjs';

import {page, BASE} from './outline-dom.mjs';

test('a visible form stays readable when a named control shadows hidden, while a hidden form stays excluded',()=>{
  const f=page(h=>{
    const field=h('input',{id:'hidden',type:'hidden',name:'hidden name'});
    const shown=h('form',{'aria-label':'Visible form'},field,h('textarea',{'aria-label':'Note',value:'Readable note'}));
    const hidden=h('form',{'aria-label':'Hidden form',hidden:''},h('textarea',{'aria-label':'Private note',value:'Must stay out'}));
    // HTMLFormElement's named-property lookup can override HTMLElement.hidden.
    Object.defineProperty(shown,'hidden',{value:field});Object.defineProperty(hidden,'hidden',{value:false});
    return [shown,hidden];
  });
  const nodes=f.outline().nodes,form=nodes.find(node=>node.role==='form'&&node.name==='Visible form');
  assert.ok(form,'the form is visible despite its named property');assert.deepEqual(form.hidden,['hidden name']);
  assert.ok(nodes.some(node=>node.parent===form.id&&node.value==='Readable note'));
  assert.ok(!JSON.stringify(nodes).includes('Hidden form'));assert.ok(!JSON.stringify(nodes).includes('Must stay out'));
});

test('inline formatting is text of its element, and only the link stands between the runs',()=>{
  const f=page(h=>[h('p',{},'Order ',h('b',{},'confirmed'),' today, see ',h('i',{},'the ',h('a',{href:'/t'},'timetable')),'.')]);
  const data=f.outline();
  assert.deepEqual(data.nodes,[
    {id:1,parent:null,role:'p',text:['Order confirmed today, see the ',2,'.']},
    {id:2,parent:1,role:'link',name:'timetable',href:'https://fixture.test/t',text:['timetable']}]);
  assert.deepEqual([data.watched,data.url,data.title,data.origin,data.scroll,data.height,data.omitted],[true,BASE+'page','Fixture','https://fixture.test',120,0,0]);
  assert.match(data.document,/^[0-9a-f]{32}$/);assert.match(data.reader,/^[0-9a-f]{32}$/);
});

test('a role comes from the list or the tag, never from a page\'s own string',()=>{
  const f=page(h=>[
    h('div',{role:'h1 injected'},'A'),h('div',{role:'password'},'B'),h('span',{role:'BUTTON'},'Go'),h('div',{role:'link\n"evil'},'C'),
    h('div',{role:'heading','aria-level':'3'},'D'),h('nav',{},h('a',{href:'/x'},'X')),h('section',{},'plain'),h('section',{'aria-label':'Named'},'in'),
    h('table',{},h('tr',{},h('th',{scope:'row'},'R'),h('th',{},'H'),h('td',{},'c')))]);
  const nodes=f.outline().nodes;
  assert.deepEqual(nodes.map(node=>node.role),['text','text','button','link','h3','navigation','link','text','region','table','row','rowheader','columnheader','cell']);
  assert.deepEqual(nodes[2],{id:nodes[2].id,parent:null,role:'button',name:'Go',text:['Go']});
  assert.deepEqual(nodes[8],{id:nodes[8].id,parent:null,role:'region',name:'Named',text:['in']});
  assert.ok(!JSON.stringify(nodes.map(node=>node.role)).includes('evil'));
});

test('a form: labels, hidden names, states, an error text once, a list field, and password fields as leaves',()=>{
  const f=page(h=>[h('form',{'aria-label':'Account',method:'post',action:'/account?step=2'},
    h('input',{type:'hidden',name:'csrf',value:'x'}),
    h('label',{},'Line 0 ',h('input',{name:'line0',value:'Value 0'})),
    h('label',{},h('input',{type:'checkbox',name:'news',checked:''}),' News'),
    h('label',{},'Country ',h('select',{name:'country'},...Array.from({length:60},(_,index)=>h('option',{value:'c'+index,...(index===7?{selected:''}:{})},'Country '+index)))),
    h('label',{},'Email ',h('input',{type:'email',name:'email',value:'not-an-address',required:'','aria-invalid':'true','aria-describedby':'email-error'})),
    h('span',{id:'email-error'},'Enter a valid address'),
    h('label',{},'Password ',h('input',{type:'password',name:'password',value:'never'})),
    h('label',{},'One-time code ',h('input',{name:'one_time',autocomplete:'one-time-code',value:'123456',$secret:true})),
    h('button',{type:'submit'},'Save'))]);
  const data=f.outline(),nodes=data.nodes,options=Array.from({length:60},(_,index)=>({label:'Country '+index,value:'c'+index,chosen:index===7,disabled:false}));
  assert.deepEqual(nodes,[
    {id:1,parent:null,role:'form',name:'Account',method:'post',action:'https://fixture.test/account?step=2',hidden:['csrf']},
    {id:2,parent:1,role:'text',text:['Line 0 ',3]},{id:3,parent:2,role:'textbox',name:'Line 0',value:'Value 0'},
    {id:4,parent:1,role:'text',text:[5,' News']},{id:5,parent:4,role:'checkbox',name:'News',states:['checked']},
    {id:6,parent:1,role:'text',text:['Country ',7]},{id:7,parent:6,role:'combobox',name:'Country',option_count:60,chosen:'Country 7',options:options.slice(0,50)},
    {id:8,parent:1,role:'text',text:['Email ',9]},{id:9,parent:8,role:'textbox',name:'Email',value:'not-an-address',states:['required','invalid'],error:'Enter a valid address'},
    {id:10,parent:1,role:'text',text:['Password ',11]},{id:11,parent:10,role:'password',name:'Password',unread:true},
    {id:12,parent:1,role:'text',text:['One-time code ',13]},{id:13,parent:12,role:'password',name:'One-time code',unread:true},
    {id:14,parent:1,role:'button',name:'Save',text:['Save']}]);
  // `options` returns every option of one list field, by the number the outline gave,
  // and only to the document and reader instance that gave it.
  const from={document:data.document,reader:data.reader};
  assert.deepEqual(f.run({command:'options',element:7,...from}),{ok:true,data:options});
  for(const element of [3,11,'e7',0,999,null]){const refused=f.run({command:'options',element,...from});assert.equal(refused.ok,false);assert.match(refused.error,/^stale_reference: /);}
  for(const other of [{},{document:data.document},{reader:data.reader},{...from,reader:'0'.repeat(32)},{...from,document:'0'.repeat(32)}]){
    const refused=f.run({command:'options',element:7,...other});assert.equal(refused.ok,false,JSON.stringify(other));assert.match(refused.error,/^stale_reference: /);
  }
});

test('in a document the reader has not watched, a typed field says only filled or empty',()=>{
  const f=page(h=>[
    h('input',{'aria-label':'Code',value:'typed',$secret:true}),h('input',{'aria-label':'Nickname',$secret:true}),
    h('textarea',{'aria-label':'Notes',value:'draft',$secret:true}),h('input',{type:'date','aria-label':'Born',value:'2001-02-03'}),
    h('input',{type:'checkbox','aria-label':'Tick',checked:''})],{watched:false});
  const data=f.outline();
  assert.equal(data.watched,false);
  assert.deepEqual(data.nodes.map(({id,parent,...rest})=>rest),[
    {role:'textbox',name:'Code',unread:true,filled:true},{role:'textbox',name:'Nickname',unread:true,filled:false},
    {role:'textbox',name:'Notes',unread:true,filled:true},{role:'textbox',name:'Born',value:'2001-02-03'},
    {role:'checkbox',name:'Tick',states:['checked']}]);
  assert.equal(f.run({command:'page_state'}).ok,true);
});

test('hidden parts, scripts and the head are left out; a shadow root and a pre are read; a modal hides the rest',()=>{
  const f=page(h=>[h('p',{hidden:''},'no'),h('p',{style:'display:none'},'no'),h('script',{},'x()'),h('p',{},'yes'),
    h.shadow(h('div',{}),h('p',{},'in the shadow root')),h('pre',{},'a\n  b')]);
  assert.deepEqual(f.outline().nodes.map(({role,text})=>[role,text]),[['p',['yes']],['p',['in the shadow root']],['p',['a\n  b']]]);
  const modal=page(h=>[h('p',{},'behind'),h('dialog',{open:''},h('p',{},'inside'))]);
  assert.deepEqual(modal.outline().nodes.map(({role,text})=>[role,text]),[['dialog',undefined],['p',['inside']]]);
});

test('beyond 20,000 nodes the reply says how many were left out',()=>{
  const f=page(h=>Array.from({length:20001},(_,index)=>h('p',{},'Paragraph '+index)));
  const data=f.outline();
  assert.equal(data.nodes.length,20000);assert.equal(data.omitted,1);assert.deepEqual(data.nodes.at(-1).text,['Paragraph 19999']);
  // The background passes what is left of the tab's nodes; a parent that is cut takes its children along.
  const small=page(h=>[h('p',{},'One'),h('ul',{},h('li',{},'Two'),h('li',{},'Three')),h('p',{},'Four')]);
  const cut=limit=>{const result=small.run({command:'outline',limit});assert.equal(result.ok,true,JSON.stringify(result));return [result.data.nodes.map(node=>node.role),result.data.omitted];};
  assert.deepEqual(cut(3),[['p','list','listitem'],2]);assert.deepEqual(cut(1),[['p'],4]);assert.deepEqual(cut(0),[[],5]);
  for(const limit of [5,20001,-1,1.5,'2',null])assert.deepEqual(cut(limit),[['p','list','listitem','listitem','p'],0],String(limit));
});

test('H1 controls exceed the reference bound while its capped outline fits the native reply',()=>{
  const f=page(h=>Array.from({length:20001},(_,index)=>index<H1_REFERENCES?
    h('i',{role:'button','aria-label':'Element '+index}):h('i',{role:'img'})));
  const data=f.outline();
  assert.equal(data.nodes.length,20000);assert.equal(data.omitted,1);
  assert.equal(data.nodes.filter(node=>node.role==='button').length,H1_REFERENCES);
  assert.ok(H1_REFERENCES>5000);
  // Leave room for the background's tab, frame, session and command envelope.
  assert.ok(Buffer.byteLength(JSON.stringify(data))<1024*1024-4096);
});

test('page_state moves with a typed value and a tick, and carries no value',()=>{
  const f=page(h=>[h('input',{'aria-label':'A',value:'one'}),h('input',{type:'checkbox','aria-label':'B'}),h('input',{type:'password',value:'never'})]);
  const state=()=>{const result=f.run({command:'page_state'});assert.equal(result.ok,true,JSON.stringify(result));return result.data;};
  const first=state();
  assert.deepEqual(Object.keys(first).sort(),['address','document','fields','origin','reader','ready','revision']);assert.equal(first.origin,'https://fixture.test');
  assert.match(first.fields,/^[0-9a-f]{64}$/);assert.match(first.address,/^[0-9a-f]{64}$/);assert.deepEqual([first.ready,first.revision],[true,0]);
  assert.deepEqual(state(),first);
  f.body.childNodes[0].attrs.value='two words';const typed=state();
  f.body.childNodes[1].attrs.checked='';const ticked=state();
  assert.equal(new Set([first.fields,typed.fields,ticked.fields]).size,3);
  assert.deepEqual([typed.address,ticked.address],[first.address,first.address]);
  assert.ok(!JSON.stringify([first,typed,ticked]).includes('two words'));
});

test('a shadow root met late: a typed field that already holds text is never read, and an empty one is watched from then on',()=>{
  let host,late,empty;
  const f=page(h=>[host=h('div',{}),h('input',{'aria-label':'Page field',value:'plain'})]);
  assert.deepEqual(f.outline().nodes.map(({role,name,value})=>[role,name,value]),[['textbox','Page field','plain']]);
  // A component attaches its root to an element that is already in the page: no observer sees it.
  f.h.shadow(host,late=f.h('input',{'aria-label':'Code',value:'typed before the reader came',$secret:true}),empty=f.h('input',{'aria-label':'Nickname'}),
    f.h('textarea',{'aria-label':'Notes',value:'draft',$secret:true}),f.h('input',{'aria-label':'Password',value:'never',$secret:true}),
    f.h('input',{type:'checkbox','aria-label':'Tick',checked:''}),f.h('input',{type:'date','aria-label':'Born',value:'2001-02-03'}));
  const fields=()=>f.outline().nodes.map(({id,parent,...rest})=>rest),after=[{role:'checkbox',name:'Tick',states:['checked']},{role:'textbox',name:'Born',value:'2001-02-03'},{role:'textbox',name:'Page field',value:'plain'}];
  assert.deepEqual(fields(),[{role:'textbox',name:'Code',unread:true,filled:true},{role:'textbox',name:'Nickname',value:''},{role:'textbox',name:'Notes',unread:true,filled:true},{role:'password',name:'Password',unread:true},...after]);
  // The asking read may list the two, by the reader's own mark, and never the field named like a credential.
  const list=f.run({command:'typed_fields'});assert.equal(list.ok,true,JSON.stringify(list));
  assert.deepEqual(list.data.fields.map(({label,type})=>[label,type]),[['Code','text'],['Notes','textarea']]);
  // Claude doesn't type into the one it can't read.
  const code=f.outline().nodes.find(node=>node.name==='Code').id,nickname=f.outline().nodes.find(node=>node.name==='Nickname').id;
  f.run({command:'set_control',generation:'epoch'});
  const refused=f.run({command:'focus',element:'e'+code,generation:'epoch'});assert.equal(refused.ok,false);assert.match(refused.error,/^owner_signin: the tool may not read this field/);
  assert.doesNotMatch(String(f.run({command:'focus',element:'e'+nickname,generation:'epoch'}).error),/^owner_signin/);
  // For the life of the document: emptied and filled again it stays unread; the one met empty is read; a field added later is watched from its start.
  late.attrs.value='';empty.attrs.value='typed later';
  const added=f.h('input',{'aria-label':'Added',value:'new'});added.root=host.shadowRoot;host.shadowRoot.childNodes.push(added);
  assert.deepEqual(fields(),[{role:'textbox',name:'Code',unread:true,filled:false},{role:'textbox',name:'Nickname',value:'typed later'},{role:'textbox',name:'Notes',unread:true,filled:true},{role:'password',name:'Password',unread:true},
    ...after.slice(0,2),{role:'textbox',name:'Added',value:'new'},after[2]]);
  late.attrs.value='again';assert.deepEqual(fields()[0],{role:'textbox',name:'Code',unread:true,filled:true});
  assert.equal(f.run({command:'page_state'}).ok,true);
});

test('a shadow root that is in the page when the reader arrives: its filled typed fields are unread too, in a watched document',()=>{
  // The reader can't tell a component's own default from text typed before it met the root (KNOWN-LIMITS).
  const f=page(h=>[h.shadow(h('div',{}),h('input',{'aria-label':'Search',value:'a default',$secret:true}),h('input',{'aria-label':'Empty'})),h('input',{'aria-label':'Outside',value:'read'})]);
  assert.deepEqual(f.outline().nodes.map(({id,parent,...rest})=>rest),[{role:'textbox',name:'Search',unread:true,filled:true},{role:'textbox',name:'Empty',value:''},{role:'textbox',name:'Outside',value:'read'}]);
});

