import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {pathToFileURL} from 'node:url';
import {completedFailure,recordCompletion,LOGICAL_FAILURE} from './qualification-completion.mjs';

test('QUALIFICATION completion distinguishes final aggregate assertions from crash or cleanup errors',()=>{
  assert.equal(completedFailure(new Error(LOGICAL_FAILURE)),false);
  assert.equal(completedFailure(new AggregateError([new Error('crash')],'Unfinished fixture')),false);
  assert.equal(completedFailure(new AggregateError([],LOGICAL_FAILURE)),false);
  assert.equal(completedFailure(new AggregateError([new Error('adapter assertion')],LOGICAL_FAILURE)),true);
});
test('QUALIFICATION observer preserves process failures and distinguishes completed failures from interrupted suites',()=>{
  const directory=fs.mkdtempSync(path.resolve('.work/20-chrome/observer-'));
  try{
    fs.writeFileSync(path.join(directory,'qualification-result.json'),'fixture result');
    fs.writeFileSync(path.join(directory,'matrices.json'),'fixture matrix');
    const module=pathToFileURL(path.resolve('control/chrome_tests/qualification-completion.mjs')).href;
    for(const [statement,status,marker]of [
      ['',0,'success'],
      [`throw new AggregateError([Error('fixture adapter failure')],${JSON.stringify(LOGICAL_FAILURE)});`,1,'failure'],
      ["throw Error('fixture cleanup failure');",1,null],
      ['process.exit(137);',137,null]
    ]){
      const child=spawnSync(process.execPath,['--input-type=module','-e',`import {observeHarness} from ${JSON.stringify(module)};observeHarness(${JSON.stringify(directory)},{repeat:1});${statement}`],{encoding:'utf8'});
      assert.equal(child.status,status,child.stderr);
      const target=path.join(directory,'qualification-complete.json');
      if(marker)assert.equal(JSON.parse(fs.readFileSync(target)).outcome,marker);
      else assert.equal(fs.existsSync(target),false);
    }
  }finally{fs.rmSync(directory,{recursive:true,force:true});}
});
test('QUALIFICATION completion binds actual result and matrix bytes, and requires both',()=>{
  const directory=fs.mkdtempSync(path.resolve('.work/20-chrome/completion-'));
  try{
    fs.writeFileSync(path.join(directory,'qualification-result.json'),'fixture result');
    assert.throws(()=>recordCompletion(directory,{repeat:1},'failure'));
    assert.equal(fs.existsSync(path.join(directory,'qualification-complete.json')),false);
    fs.writeFileSync(path.join(directory,'matrices.json'),'fixture matrix');
    recordCompletion(directory,{repeat:1},'failure');
    const first=JSON.parse(fs.readFileSync(path.join(directory,'qualification-complete.json')));
    assert.equal(first.outcome,'failure');assert.equal(first.identity.repeat,1);
    fs.writeFileSync(path.join(directory,'qualification-result.json'),'changed fixture result');
    recordCompletion(directory,{repeat:1},'failure');
    const second=JSON.parse(fs.readFileSync(path.join(directory,'qualification-complete.json')));
    assert.notEqual(first.digests['qualification-result.json'],second.digests['qualification-result.json']);
    assert.equal(first.digests['matrices.json'],second.digests['matrices.json']);
  }finally{fs.rmSync(directory,{recursive:true,force:true});}
});
