import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {BROWSER_SHARDS,wordInventory,selected} from '../chrome/ci/shards.mjs';
const words=JSON.parse(fs.readFileSync('control/chrome/extension/policy.js','utf8').match(/\{[\s\S]*\}/)[0]).words;
test('word shards cover every label and key once within a single workflow run',()=>{
  const all=wordInventory(words),partition=BROWSER_SHARDS.filter(shard=>shard.startsWith('word-')).flatMap(shard=>wordInventory(words,shard));
  assert.equal(all.length,999);assert.equal(new Set(partition).size,all.length);assert.deepEqual(partition.sort(),all.sort());
  for(const shard of BROWSER_SHARDS)assert.equal(selected(shard,'word'),shard.startsWith('word-'));
  assert.throws(()=>selected('unknown','core'));assert.equal(selected(null,'core'),true);
});

test('all named blocks and word shards are required before any combined qualification',async()=>{
  const {caseInventories}=await import('../chrome/ci/shards.mjs');const {aggregate}=await import('../chrome/ci/merge-shards.mjs');
  const inventories=await caseInventories();
  const native={cases:[false,true].flatMap(skip=>['missing','matching','revoked','other-account','positive'].map(mode=>({case:'chrome-'+(skip?'skip-':'normal-')+mode,mode:skip?'bypassPermissions':'default',owner_entry:mode,arrivals:{tabs:1,submit:Number(mode==='positive'),typed:Number(mode==='positive'),trusted:Number(mode==='matching')},receiver_delta_sha256:'a'.repeat(64)})))};
  const shards=BROWSER_SHARDS.map(shard=>({proof:{shard,baseline:{owner:true,forgery:true,isolation:true,residual:true},adapters:Object.fromEntries(['gmail','whatsapp','github','gemini','deezer','bank'].map(name=>[name,true]))},results:shard.startsWith('word-')?[{name:'GROUP 1 what asks word/label/key matrix',passed:true}]:inventories[shard].map(name=>({name,passed:true})),words:shard.startsWith('word-')?wordInventory(words,shard):null}));
  assert.equal(aggregate(shards,native,words,{inventories}).qualified.groups[12],true);
  for(const mutate of [rows=>rows.pop(),rows=>rows.push(rows[0]),rows=>rows[0].results.pop(),rows=>rows.at(-1).words.pop(),rows=>rows[0].proof.baseline.owner=false]){
    const changed=structuredClone(shards);mutate(changed);assert.throws(()=>aggregate(changed,native,words,{inventories}));
  }
});
