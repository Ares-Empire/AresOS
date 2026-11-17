import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {fixtures} from '../chrome/ci/fixture.mjs';
import {outlinePage,LONG_TEXT,LONG_VALUE,WIDE_CELL,BYTE_TEXT} from '../chrome/ci/outline-fixtures.mjs';
import {efficiencyPage,HOSTILE,H1_NAME} from '../chrome/ci/efficiency-fixtures.mjs';
import {asciiBytes,stableReferences,completeEscapes,hostileGrammar,quoted,visible} from '../chrome/ci/outline-checks.mjs';

test('remaining paging and asking fixtures are served with exact stress sizes and compile',async()=>{
  assert.equal(LONG_TEXT.length,100000);assert.equal(LONG_VALUE.length,20000);assert.ok(WIDE_CELL.length>1000);
  assert.equal(H1_NAME.length,100000);assert.equal(H1_NAME.trim(),H1_NAME);
  const fixture=await fixtures({port:0,secondPort:0});
  try{
    for(const query of ['case=outline-paging','case=outline-paging&mode=row','case=outline-paging&mode=value',
      ...Object.keys(BYTE_TEXT).map(mode=>'case=outline-paging&mode='+mode),
      'case=outline-state','case=outline-state&mode=child','case=outline-state&mode=busy',
      ...['plain','child','added','replacement','label','duplicate','unlabelled','frame','type','mask'].map(mode=>'case=password-outline&mode='+mode)]){
      const page=outlinePage(new URL('http://fixture.test/?'+query+'&id=test'));
      assert.ok(page.body,query);new vm.Script(page.script);assert.doesNotMatch(page.script,/<\/script|<!--/i);
      const response=await fetch('http://127.0.0.1:'+fixture.port+'/?'+query+'&id=test');assert.equal(response.status,200);
      assert.ok((await response.text()).includes(page.body));
    }
  }finally{fixture.close();}
  for(const mode of Object.keys(BYTE_TEXT)){
    const {body}=outlinePage(new URL('http://fixture.test/?case=outline-paging&mode='+mode));
    assert.equal((body.match(/<p>/g)||[]).length,134);assert.equal((body.match(/<hr>/g)||[]).length,134);
  }
});

test('H1 puts each hostile string on the additional form list title and stale-line surfaces',()=>{
  for(let title=0;title<HOSTILE.length;title++){
    const {body,script}=efficiencyPage(new URL('http://fixture.test/?case=efficiency-h1&mode=surfaces&title='+title));
    new vm.Script(script);assert.doesNotMatch(script,/<\/script|<!--/i);
    for(const part of ['<form','<textarea','<select','<table','<th','<td','<ul','id="error"','type="hidden"','id="fold5"','id="dialog"'])assert.ok(body.includes(part),part);
    assert.ok(script.includes('globalThis.reviewChange'));assert.ok(script.includes('alert(hostile)'));
  }
});

test('wire measurement counts ASCII JSON and every escape remains whole',()=>{
  assert.equal(asciiBytes({text:'漢"\n\\'}),Buffer.byteLength('{"text":"\\u6f22\\"\\n\\\\"}'));
  for(const text of HOSTILE){completeEscapes(quoted(text));hostileGrammar('button '+quoted(text)+' bcdfg1');}
  for(const broken of ['\\','\\u12','\\u202'])assert.throws(()=>completeEscapes(broken));
  for(const raw of ['button "unterminated','button "x\u202ey"','button "x\ty"'])assert.throws(()=>hostileGrammar(raw));
  assert.equal(visible('\ud800\u{e0001}'),'\\ud800\\ue0001');
});

test('expected browser files preserve all characters except reference identities',()=>{
  const source=JSON.parse(fs.readFileSync(new URL('../chrome/ci/outline-expected/source.json',import.meta.url)));
  assert.equal(source.run,44106253829);assert.equal(source.attempt,1);
  for(const name of ['f6','f7','address']){
    const text=fs.readFileSync(new URL('../chrome/ci/outline-expected/'+name+'.txt',import.meta.url),'utf8');
    assert.ok(text.includes('REF1'));assert.equal(stableReferences(text),text);
  }
  assert.equal(stableReferences('button "A" bcdfg81\nbutton "B" bcdfg82\nbutton "A" bcdfg81'),'button "A" REF1\nbutton "B" REF2\nbutton "A" REF1');
});
