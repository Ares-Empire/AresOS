import test from 'node:test';
import assert from 'node:assert/strict';
import {allTabs} from '../chrome/ci/tabs.mjs';
test('fixture tab inventory follows every public ten-row page',async()=>{
  const seen=[];const result=await allTabs(async(action,args)=>{assert.equal(action,'tabs');assert.equal(args.limit,10);seen.push(args.cursor);return args.cursor?{items:[{tab:11}]}:{items:Array.from({length:10},(_,tab)=>({tab})),cursor:'next'};});
  assert.equal(result.items.length,11);assert.equal(result.items.at(-1).tab,11);assert.deepEqual(seen,[undefined,'next']);
});
