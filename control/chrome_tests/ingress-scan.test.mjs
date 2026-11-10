import test from 'node:test';
import assert from 'node:assert/strict';
import {completeIngress} from '../chrome/ci/ingress-scan.mjs';

test('P30 password scans reassemble boundaries and refuse missing or reordered fragments',()=>{
  const source=JSON.stringify({value:'SENTINEL_PRIVATE_PASSWORD_20'}),split=20;
  const fragments=[{json_fragment:source.slice(0,split),offset:0,total:source.length},{json_fragment:source.slice(split),offset:split,total:source.length}];
  assert.match(JSON.stringify(completeIngress(fragments.map(JSON.stringify).join('\n'))),/SENTINEL_PRIVATE_PASSWORD_20/);
  assert.throws(()=>completeIngress(JSON.stringify(fragments[0])));assert.throws(()=>completeIngress(fragments.reverse().map(JSON.stringify).join('\n')));
});
