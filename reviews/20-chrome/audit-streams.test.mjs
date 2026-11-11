import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {completeIngress} from '../../control/chrome/ci/ingress-scan.mjs';
import {jsonLines,completeIngressStream,containsText,digestFile} from './audit-streams.mjs';

function fixture(t,text){
  const directory=fs.mkdtempSync(path.resolve('.work/audit-streams-'));
  t.after(()=>fs.rmSync(directory,{recursive:true,force:true}));
  const file=path.join(directory,'fixture.jsonl');fs.writeFileSync(file,text);return file;
}
async function collect(values){const rows=[];for await(const row of values)rows.push(row);return rows;}
const encoded=rows=>rows.map(row=>JSON.stringify(row)).join('\n');
function fragments(value,cuts){
  const text=JSON.stringify(value),positions=[0,...cuts,text.length];
  return positions.slice(0,-1).map((start,index)=>({json_fragment:text.slice(start,positions[index+1]),offset:start,total:text.length}));
}

test('streaming ingress retains nulls and matches completeIngress across UTF-8 and fragment boundaries',async t=>{
  const value={protocol_event:{method:'Page.frameNavigated'},text:'x'.repeat(65531)+'💡漢字',nested:{value:null}};
  const rows=[null,{command:'read'},...fragments(value,[1,101,65580]),null,{reader_ingress:{kind:'input'}}];
  const text=encoded(rows)+'\n';assert.deepEqual(await collect(completeIngressStream(fixture(t,text))),completeIngress(text));
});

test('streaming JSON lines preserve the original empty-line and trailing-line semantics',async t=>{
  for(const text of ['', '\n\n', 'null', '{}\nnull\n', '\n{}\n\nnull']){
    assert.deepEqual(await collect(jsonLines(fixture(t,text))),text.split('\n').filter(Boolean).map(line=>JSON.parse(line)));
  }
  await assert.rejects(collect(jsonLines(fixture(t,'{}\n\r\n'))),SyntaxError);
});

test('every malformed fragment fails with the unchanged completeIngress reason',async t=>{
  const normal=fragments({text:'draft'},[3]);
  const cases=[
    [normal[0]],
    [normal[1]],
    [normal[0],null],
    [normal[0],normal[0]],
    [normal[0],{...normal[1],offset:4}],
    [normal[0],{...normal[1],total:100}],
    [{json_fragment:'{}x',offset:0,total:2}],
    [{json_fragment:'x',offset:0,total:1}],
  ];
  for(const rows of cases){
    const text=encoded(rows);let failure;try{completeIngress(text);}catch(error){failure=error;}
    assert(failure,'the original parser must reject this fixture');
    await assert.rejects(collect(completeIngressStream(fixture(t,text))),{message:failure.message});
  }
});

test('sentinel scans find an ASCII sentinel split across stream chunks without retaining the file',async t=>{
  const needle='SENTINEL_PRIVATE_PASSWORD_20';
  for(const split of [1,needle.length-1]){
    const text='x'.repeat(65536-split)+needle+'尾';
    assert.equal(await containsText(fixture(t,text),needle),true);
  }
  assert.equal(await containsText(fixture(t,'safe 💡 text'),'absent'),false);
  assert.equal(await containsText(fixture(t,'safe'),'s'),true);
  await assert.rejects(containsText(fixture(t,'safe'),''),/Empty evidence scan needle/);
});

test('streamed SHA-256 equals the complete byte digest including multibyte chunk boundaries',async t=>{
  const text='x'.repeat(65535)+'💡漢字\n'.repeat(2000),file=fixture(t,text);
  assert.equal(await digestFile(file),crypto.createHash('sha256').update(Buffer.from(text)).digest('hex'));
});
