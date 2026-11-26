// The native wire, including JSON inside reply chunks, uses the service's
// actual strict decoder. No browser or owner profile is started here.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {spawnSync} from 'node:child_process';

const source=fs.readFileSync('control/chrome/extension/background.js','utf8');
const boundary=source.slice(source.indexOf('function respond('),source.indexOf('function safeURL('));
const repair='  value=wellFormed(value);';
function fixture({fallback=false,removeBoundary=false}={}){
  let code=source.replace("import {POLICY} from './policy.js';",'');
  code=code.slice(0,code.indexOf('async function connect()'));
  // Named mutation: removing the repair at the common native-host boundary.
  if(removeBoundary||process.env.NATIVE_UNICODE_MUTATION==='remove-boundary'){
    assert.equal(code.split(repair).length,2);code=code.replace(repair,'');
  }
  const wires=[],context=vm.createContext({POLICY:{},chrome:{},crypto:{randomUUID:()=> 'fixture'},TextEncoder,
    btoa:value=>Buffer.from(value,'binary').toString('base64'),performance,setTimeout,clearTimeout});
  vm.runInContext(code,context);
  if(fallback)vm.runInContext('String.prototype.toWellFormed=undefined',context);
  context.nativePort={postMessage:value=>wires.push(JSON.stringify(value))};
  vm.runInContext('port=nativePort',context);
  return {wires,send(value,expression='respond(input)'){context.input=value;vm.runInContext(expression,context);}};
}

function decoded(wires){
  const messages=wires.map(line=>JSON.parse(line));
  if(!messages[0].chunk){assert.equal(messages.length,1);return {value:messages[0],json:wires[0]};}
  let offset=0;const parts=[];
  for(const {id,chunk}of messages){
    assert.equal(id,'read');assert.equal(chunk.offset,offset);assert.equal(chunk.total,messages[0].chunk.total);
    const bytes=Buffer.from(chunk.bytes,'base64');assert.ok(bytes.length>0&&bytes.length<=64*1024);
    parts.push(bytes);offset+=bytes.length;
  }
  assert.equal(offset,messages[0].chunk.total);
  const json=Buffer.concat(parts).toString('utf8');return {value:JSON.parse(json),json};
}
function strictResults(lines){
  const result=spawnSync('python3',['-c',`
import json,sys
from aresos_control.common import strict_json_loads, Refused
results=[]
for line in json.loads(sys.stdin.read()):
    try:
        strict_json_loads(line.encode('utf-8')); results.append('accepted')
    except Refused as error:
        results.append(error.code)
print(json.dumps(results))
`],{input:JSON.stringify(lines),encoding:'utf8',env:{...process.env,PYTHONDONTWRITEBYTECODE:'1',PYTHONPATH:'control'}});
  assert.equal(result.status,0,result.stderr);return JSON.parse(result.stdout);
}

const bad=['high \ud800','low \udc00','reversed \udc00\ud800','pair \ud83e\udd8a'];
const good=['high \ufffd','low \ufffd','reversed \ufffd\ufffd','pair \ud83e\udd8a'];
function message(strings,large){
  return {id:'read',ok:true,data:{[strings[0]]:{nested:[strings,{[strings[1]]:strings[2]}]},
    strings,valid:strings[3],primitives:[null,true,false,17],['__proto__']:'ordinary key',padding:large?'x'.repeat(600*1024):''}};
}

for(const fallback of [false,true])for(const large of [false,true])test(`native Unicode boundary: ${fallback?'fallback':'native'} repair, ${large?'chunked':'direct'} reply`,()=>{
  const f=fixture({fallback}),input=message(bad,large);f.send(input);
  const result=decoded(f.wires);assert.deepEqual(result.value,message(good,large));
  assert.equal(!!JSON.parse(f.wires[0]).chunk,large,'exercise the actual size-selected transport path');
  assert.deepEqual(input,message(bad,large),'repair does not mutate the internal binding or reader result');
  assert.deepEqual(strictResults([...f.wires,result.json]),Array(f.wires.length+1).fill('accepted'));
  const unsafe=fixture({fallback,removeBoundary:true});unsafe.send(input);const original=decoded(unsafe.wires);
  assert.deepEqual(strictResults([original.json]),['invalid_input'],'the unmodified JSON.stringify output is refused');
  if(large)assert.deepEqual(strictResults(unsafe.wires),Array(unsafe.wires.length).fill('accepted'),'the refusal is after chunk assembly');
  else assert.deepEqual(strictResults(unsafe.wires),['invalid_input'],'the small reply is refused directly');
});

test('native Unicode boundary covers events, audit data, errors and object keys',()=>{
  const f=fixture();
  for(const event of ['reader_error','held_step','owner_sites','hello'])f.send({event,error:bad[0],title:bad[1],dialog:{text:bad[2]},[bad[0]]:bad[3]});
  f.send({[bad[0]]:[...bad]},'recording=true;audit(input)');
  const values=f.wires.map(line=>JSON.parse(line));
  for(const value of values.slice(0,4)){
    assert.equal(value.error,good[0]);assert.equal(value.title,good[1]);assert.equal(value.dialog.text,good[2]);assert.equal(value[good[0]],good[3]);
  }
  assert.deepEqual(values[4],{event:'audit',data:{[good[0]]:good}});
  assert.deepEqual(strictResults(f.wires),Array(5).fill('accepted'));
});

test('audit fragments keep valid pairs whole and repair text before inner JSON serialization',()=>{
  const f=fixture(),prefix='x'.repeat(63999-'{"text":"'.length);
  f.send({text:prefix+'\ud83e\udd8a'+bad.join('|')},'recording=true;audit(input)');
  let text='';
  for(const line of f.wires){
    const {event,data}=JSON.parse(line);assert.equal(event,'audit');assert.equal(data.offset,text.length);text+=data.json_fragment;
    assert.ok(data.json_fragment.length<=64000);
  }
  assert.equal(f.wires.length,2);assert.equal(JSON.parse(f.wires[0]).data.json_fragment.length,63999);
  assert.deepEqual(JSON.parse(text),{text:prefix+'\ud83e\udd8a'+good.join('|')});
  assert.equal(text.length,JSON.parse(f.wires[0]).data.total);
  assert.deepEqual(strictResults([...f.wires,text]),Array(f.wires.length+1).fill('accepted'));
});

test('every native postMessage belongs to the common repair boundary',()=>{
  assert.ok(boundary.includes(repair));
  assert.doesNotMatch(source.replace(boundary,''),/\bport\??\.postMessage\s*\(/);
  assert.match(source,/respond\(\{event:'hello'/);
  assert.match(source,/respond\(\{event:'reader_error'/);
});
