import assert from 'node:assert/strict';
import test from 'node:test';
import {receiverSnapshot} from '../chrome/ci/receiver-evidence.mjs';

test('receiver evidence retains the independent arrival rows at each approval boundary',()=>{
  const arrivals=[{url:'/receive?case=other',method:'POST',body:'other'}];
  const before=receiverSnapshot(arrivals,'review','before approval');
  arrivals.push({url:'/receive?case=review',method:'POST',body:'approved'});
  const after=receiverSnapshot(arrivals,'review','after approval');
  const repeat=receiverSnapshot(arrivals,'review','after repeat');
  assert.deepEqual([before.count,after.count,repeat.count],[0,1,1]);
  assert.deepEqual(after.arrivals,[arrivals[1]]);
  assert.deepEqual(repeat.arrivals,after.arrivals);
  assert.equal(before.arrivals.length,0,'later delivery cannot rewrite the before snapshot');
});
