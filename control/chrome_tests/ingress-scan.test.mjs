import test from 'node:test';
import assert from 'node:assert/strict';
import {completeIngress,protocolEvents} from '../chrome/ci/ingress-scan.mjs';

test('P30 password scans reassemble boundaries and refuse missing or reordered fragments',()=>{
  const source=JSON.stringify({value:'SENTINEL_PRIVATE_PASSWORD_20'}),split=20;
  const fragments=[{json_fragment:source.slice(0,split),offset:0,total:source.length},{json_fragment:source.slice(split),offset:split,total:source.length}];
  assert.match(JSON.stringify(completeIngress(fragments.map(JSON.stringify).join('\n'))),/SENTINEL_PRIVATE_PASSWORD_20/);
  assert.throws(()=>completeIngress(JSON.stringify(fragments[0])));assert.throws(()=>completeIngress(fragments.reverse().map(JSON.stringify).join('\n')));
});


test('P30 protocol scanning retains forbidden events after legitimate null results',()=>{
  const rows=completeIngress([null,{},0,{reader_ingress:{kind:'value',value:'Public'}},{protocol_event:{method:'Page.frameNavigated'}},null,{protocol_event:{method:'Runtime.consoleAPICalled'}},{protocol_event:{method:'Runtime.exceptionThrown'}}].map(JSON.stringify).join('\n'));
  assert.equal(rows.filter(row=>row===null).length,2,'null audit values remain in the full privacy scan');
  const events=protocolEvents(rows);assert.deepEqual(events.map(event=>event.method),['Page.frameNavigated','Runtime.consoleAPICalled','Runtime.exceptionThrown']);
  assert.ok(events.some(event=>['Runtime.consoleAPICalled','Runtime.exceptionThrown'].includes(event.method)),'a null must not conceal later forbidden protocol values');
});
