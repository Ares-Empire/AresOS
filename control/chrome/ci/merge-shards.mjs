// Artifact-only qualification: no browser or model is started here.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {BROWSER_SHARDS,wordInventory,caseInventories} from './shards.mjs';
import {verdicts,assertComplete} from './verdicts.mjs';
import {precedenceVerdict} from './precedence-evidence.mjs';
const WORD_CASE='GROUP 1 what asks word/label/key matrix';
export function aggregate(shards,precedence,words,{head,run,install,instructions,inventories}={}){
  assert.equal(shards.length,BROWSER_SHARDS.length,'every browser shard is required');
  const byName=new Map();const results=[],baseline={owner:true,forgery:true,isolation:true,residual:true},adapters={};let wordCases=[];
  for(const row of shards){
    const proof=row.proof;assert(BROWSER_SHARDS.includes(proof.shard));assert(!byName.has(proof.shard),'duplicate shard');byName.set(proof.shard,row);
    for(const [key,value]of Object.entries({head,run,install}))if(value)assert.equal(proof[key],value,'shard '+key);
    for(const key of Object.keys(baseline))baseline[key]&&=proof.baseline[key]===true;
    for(const [name,value]of Object.entries(proof.adapters)){
      assert.equal(typeof value,'boolean');adapters[name]=(adapters[name]??true)&&value;
    }
    if(proof.shard.startsWith('word-')){
      assert.deepEqual(row.words,wordInventory(words,proof.shard),'word shard exact inventory');
      assert.deepEqual(row.results,[{name:WORD_CASE,passed:true}]);wordCases.push(...row.words);
    }else{
      if(inventories)assert.deepEqual(row.results.map(item=>item.name).sort(),inventories[proof.shard],'exact named inventory for '+proof.shard);
      assert(row.results.every(item=>item.passed===true),'failed shard case');
      results.push(...row.results);
    }
  }
  assert.deepEqual([...byName.keys()].sort(),[...BROWSER_SHARDS].sort());
  assert.deepEqual([...wordCases].sort(),wordInventory(words).sort(),'complete disjoint word matrix');
  results.push({name:WORD_CASE,passed:true});
  assert(precedenceVerdict(precedence,instructions,{head,run}),'native group 12 missing or not bound to this run/head');
  const qualified=verdicts(results,baseline,adapters,precedence);assertComplete(results,qualified);
  return {results,qualified,baseline,adapters,wordCases:wordCases.length};
}
function json(file){return JSON.parse(fs.readFileSync(file,'utf8'));}
function append(source,target){const input=fs.openSync(source,'r'),output=fs.openSync(target,'a');try{const buffer=Buffer.alloc(65536);let count;while((count=fs.readSync(input,buffer,0,buffer.length,null)))fs.writeSync(output,buffer,0,count);}finally{fs.closeSync(input);fs.closeSync(output);}}
export async function mergeArtifacts(root,out,precedenceFile,identity){
  const folders=fs.readdirSync(root).map(name=>path.join(root,name)).filter(folder=>fs.existsSync(path.join(folder,'shard-complete.json')));
  const shards=folders.map(folder=>({proof:json(path.join(folder,'shard-complete.json')),results:json(path.join(folder,'matrices.json')),words:fs.existsSync(path.join(folder,'word-cases.json'))?json(path.join(folder,'word-cases.json')):null}));
  const policy=JSON.parse(fs.readFileSync('control/chrome/extension/policy.js','utf8').match(/\{[\s\S]*\}/)[0]);
  const precedence=json(precedenceFile),instructions=fs.readFileSync('control/generated/chrome-instructions.txt','utf8').replace(/\n$/,'');
  const inventories=await caseInventories();
  const merged=aggregate(shards,precedence,policy.words,{...identity,instructions,inventories});fs.mkdirSync(out,{recursive:true});
  const ignore=new Set(['matrices.json','qualification-result.json','shard-complete.json','qualification-complete.json','word-cases.json']);
  const first=new Set();
  for(const folder of folders.sort((a,b)=>Number(!a.endsWith('-core'))-Number(!b.endsWith('-core'))))for(const name of fs.readdirSync(folder)){
    if(ignore.has(name)||!fs.statSync(path.join(folder,name)).isFile())continue;
    const source=path.join(folder,name),target=path.join(out,name);
    if(name.endsWith('.jsonl')||['browser.txt','service.txt','latency-bridge.jsonl'].includes(name)){append(source,target);}
    else if(!first.has(name)){fs.copyFileSync(source,target);first.add(name);}
  }
  fs.writeFileSync(path.join(out,'matrices.json'),JSON.stringify(merged.results,null,2));
  fs.writeFileSync(path.join(out,'qualification-result.json'),JSON.stringify(merged.qualified,null,2));
  fs.copyFileSync(precedenceFile,path.join(out,'chrome-precedence.json'));
  fs.writeFileSync(path.join(out,'aggregate-complete.json'),JSON.stringify({...identity,shards:shards.map(row=>row.proof),word_cases:merged.wordCases},null,2));
  console.log('Every browser shard and all '+merged.wordCases+' word cases PASS; native group 12 PASS');
  return merged;
}
if(process.argv[1]?.endsWith('/merge-shards.mjs'))await mergeArtifacts(process.argv[2],process.argv[3],process.argv[4],{head:process.env.RUNTIME_COMMIT||process.env.GITHUB_SHA,run:process.env.GITHUB_RUN_ID,install:process.env.INSTALL_MODE});
