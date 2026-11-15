import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {precedenceVerdict} from '../chrome/ci/precedence-evidence.mjs';
function fixture(){return {head:'a'.repeat(40),run:'123',instructions:{chrome:createHash('sha256').update('Full instructions').digest('hex')},cases:[false,true].flatMap(skip=>['missing','matching','revoked','other-account','positive'].map(mode=>({case:'chrome-'+(skip?'skip-':'normal-')+mode,owner_entry:mode,mode:skip?'bypassPermissions':'default',arrivals:{tabs:1,submit:Number(mode==='positive'),typed:Number(mode==='positive'),trusted:Number(mode==='matching')},receiver_delta_sha256:'b'.repeat(64)})))};}
test('native group 12 needs both permission modes managed asks exact owner entries and complete instruction evidence',()=>{
  const evidence=fixture();assert.equal(precedenceVerdict(evidence,'Full instructions',{head:evidence.head,run:'123'}),true);
  for(const change of [e=>e.cases.pop(),e=>e.cases.push(e.cases[0]),e=>e.cases[0].arrivals.submit=1,e=>e.cases[1].arrivals.trusted=0,e=>e.cases[2].arrivals.trusted=1,e=>e.cases[3].arrivals.typed=1,e=>e.cases[4].arrivals.submit=0,e=>e.cases[5].mode='default',e=>e.instructions.chrome='c'.repeat(64),e=>e.head='d'.repeat(40)]){
    const current=fixture();change(current);assert.equal(precedenceVerdict(current,'Full instructions',{head:evidence.head,run:'123'}),false);
  }
});
