// Read retained Linux artifacts only. This program starts no browser.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {assertComplete} from '../../control/chrome/ci/verdicts.mjs';
import {assertOwnerOverlap} from '../../control/chrome/ci/owner-evidence.mjs';
import {assertDestinations} from '../../control/chrome/ci/destination-evidence.mjs';
import {precedenceVerdict} from '../../control/chrome/ci/precedence-evidence.mjs';
import {assertRecheck3} from '../../control/chrome/ci/recheck3-evidence.mjs';
import {assertNativeLimit} from '../../control/chrome/ci/activation-evidence.mjs';
import {jsonLines,completeIngressStream,containsText,digestFile} from './audit-streams.mjs';

const walk=directory=>fs.readdirSync(directory,{withFileTypes:true}).flatMap(entry=>entry.isDirectory()?walk(path.join(directory,entry.name)):[path.join(directory,entry.name)]);
const read=file=>fs.readFileSync(file,'utf8');
const json=file=>JSON.parse(read(file));
const caseId=row=>new URL(row.url,'http://fixture.test').searchParams.get('case');
const results=[];
for(const root of process.argv.slice(2))for(const matrix of walk(root).filter(file=>path.basename(file)==='matrices.json'&&!fs.existsSync(path.join(path.dirname(file),'shard-complete.json')))){
  const folder=path.dirname(matrix),rows=json(matrix),verdict=json(path.join(folder,'qualification-result.json'));
  assertComplete(rows,verdict);
  const browser=read(path.join(folder,'browser.txt')).split('\n');
  const testIndex=rows.map(row=>{
    const matches=browser.flatMap((line,index)=>line===row.name+' PASS'?[index+1]:[]);
    assert.equal(matches.length,row.name==='GROUP 1 what asks word/label/key matrix'&&fs.existsSync(path.join(folder,'aggregate-complete.json'))?4:1,row.name);
    return {name:row.name,line:matches[0]};
  });
  const rawIdentities=new Set(),counts=new Map(),ownerRows=[],ownerTraces=[],queryRows=[],bindingRows=[],limitRows=[],clipboardRows=[],recheck3Rows=[],recheck3Snapshots=[];
  for await(const row of jsonLines(path.join(folder,'receiver.jsonl'))){rawIdentities.add(JSON.stringify(row));const id=caseId(row);if(id?.startsWith('recheck3-')||id?.startsWith('ping-recheck3-'))recheck3Rows.push(row);if(id?.startsWith('recheck2b-limit-'))limitRows.push(row);if(id?.startsWith('recheck2c-clipboard-'))clipboardRows.push(row);if(/^recheck-query-[0-2]$/.test(id))queryRows.push(row);if(/^review-bind-(quantity|confirmation|shadow-binding|compose-key)-/.test(id))bindingRows.push(row);counts.set(id,(counts.get(id)||0)+1);if(['owner-recheck-owner-overlap','trace-recheck-owner-overlap'].includes(id))ownerRows.push(row);}
  for(const row of bindingRows)assert.equal(row.body,caseId(row).startsWith('review-bind-quantity-')?'2':caseId(row).startsWith('review-bind-shadow-binding-')?'Invoice B':'Different draft');
  assert.equal(queryRows.length,3,'all ordinary GET query regressions must arrive once');
  for(const [index,query]of ['Pay for lunch','Delete old notes','Send a letter'].entries()){const rows=queryRows.filter(row=>caseId(row)==='recheck-query-'+index);assert.equal(rows.length,1);assert.equal(rows[0].method,'GET');assert.equal(new URL(rows[0].url,'http://fixture.test').searchParams.get('q'),query);}
  const receiverAudits=[];
  for(const name of ['page-receiver.jsonl','adapters-receiver.jsonl']){
    const sequences=new Map();let snapshots=0;
    for await(const row of jsonLines(path.join(folder,name))){
      snapshots++;if(row.id.startsWith('recheck3-')||row.id.startsWith('ping-recheck3-'))recheck3Snapshots.push(row);
      assert.equal(row.count,row.arrivals.length,`${name}: ${row.id} ${row.phase}`);
      for(const arrival of row.arrivals){
        assert.equal(caseId(arrival),row.id);
        assert(rawIdentities.has(JSON.stringify(arrival)),`${row.id}: arrival missing from independent receiver`);
      }
      if(['before approval','after approval','after repeat'].includes(row.phase)){
        if(!sequences.has(row.id))sequences.set(row.id,[]);
        sequences.get(row.id).push([row.phase,row.count]);
      }
    }
    for(const [id,phases]of sequences){
      assert.deepEqual(phases,[['before approval',0],['after approval',1],['after repeat',1]],id);
      assert.equal(counts.get(id),1,`${id}: independent final receiver count`);
    }
    assert(sequences.size>0,`${name}: missing approval evidence`);
    if(name==='page-receiver.jsonl')for(const id of ['recheck-search-pay','recheck-search-delete','recheck-search-editable-native','recheck-search-editable-aria','review-bind-quantity-','review-bind-confirmation-form','review-bind-confirmation-submit','review-bind-confirmation-submit-send','preview-residual','recheck2-compose-outside',...['blank','frame','ping','form','form-blank','download'].map(variant=>'recheck2-default-'+variant),...['open','closed'].flatMap(mode=>['insertBefore','replaceChild','append','prepend','replaceChildren','markup'].map(route=>'recheck2-shadow-'+mode+'-'+route)),...['open','closed'].flatMap(mode=>['same','other','root'].map(variant=>'recheck2-event-'+mode+'-'+variant)),...['li-open','li-closed','row-open','row-closed','slot-li-open','slot-li-closed','slot-row-open','slot-row-closed'].map(variant=>'review-bind-shadow-binding-'+variant)])assert(sequences.has(id),id+': required regression evidence absent');
    receiverAudits.push({file:name,snapshots,complete_0_1_1_sequences:sequences.size,independent_arrivals_match:true});
  }
  for(const variant of ['blank','frame','ping','form','form-blank','download'])assert.equal(counts.get('recheck2-default-'+variant),1,'native default '+variant);
  assert.equal(counts.get('ping-recheck2-default-ping'),1,'approved ping remains exactly once');
  for(const mode of ['open','closed'])for(const route of ['insertBefore','replaceChild','append','prepend','replaceChildren','markup']){
    assert.equal(counts.get('recheck2-shadow-'+mode+'-'+route),1,'native shadow default');
    assert.equal(counts.get('handler-recheck2-shadow-'+mode+'-'+route),1,'native shadow handler after fresh approval');
  }
  for(const mode of ['open','closed'])for(const variant of ['same','other','root']){
    assert.equal(counts.get('recheck2-event-'+mode+'-'+variant),1,'reused event default after approval');
    assert.equal(counts.get('handler-recheck2-event-'+mode+'-'+variant),1,'reused event handler after approval');
    assert.equal(counts.get('other-handler-recheck2-event-'+mode+'-'+variant)||0,0,'reused event other handler');
  }
  assert.equal(counts.get('recheck2-compose-inside')||0,0,'bounded live preview never sent');
  assert.equal(counts.get('recheck2-compose-outside'),1,'outside live text never reasks');
  assert.equal(counts.get('recheck2-owner-navigation'),1,'owner navigation');
  const nativeLimit=assertNativeLimit(json(path.join(folder,'all-native-limit.json')),limitRows);assert.deepEqual(nativeLimit,json(path.join(folder,'all-native-limit-audit.json')));
  const clipboard=json(path.join(folder,'clipboard-report.json'));assert.equal(clipboard.length,4);
  for(const route of ['writeText','write','copy','writeText-nav']){
    const id='recheck2c-clipboard-'+route,matching=clipboard.filter(row=>row.id===id);assert.equal(matching.length,1);const row=matching[0];assert.equal(row.route,route);
    assert.deepEqual(row.result.untrusted_content.page.clipboard,{written:true,message:'The page wrote to the clipboard.',routes:[route==='writeText-nav'?'writeText':route]});
    assert(!JSON.stringify(row).includes('SYNTHETIC_CLIPBOARD_CONTENT_2C'),'clipboard contents must never be returned');
    const arrivals=clipboardRows.filter(row=>caseId(row)===id);assert.equal(arrivals.length,1);assert.equal(arrivals[0].body,route+' accepted');
  }
  const restart=json(path.join(folder,'network-restart-audit.json'));assert.notEqual(restart.before.session,restart.after.session);assert(restart.before.rules.some(rule=>rule.id===2));assert(!restart.after.network_rules.some(rule=>rule.id===2));
  const recheck3=assertRecheck3(json(path.join(folder,'recheck3.json')),recheck3Snapshots,recheck3Rows);
  let ingress=0,nullRows=0,events=0,getters=0;const getterKinds=new Map();
  for await(const row of completeIngressStream(path.join(folder,'browser-boundary.jsonl'))){
    ingress++;if(row===null)nullRows++;if(row?.owner_trace)ownerTraces.push(row.owner_trace);
    if(row?.protocol_event){events++;assert.equal(['Runtime.consoleAPICalled','Runtime.exceptionThrown'].includes(row.protocol_event.method),false);}
    if(row?.reader_ingress){getters++;const kind=row.reader_ingress.kind;getterKinds.set(kind,(getterKinds.get(kind)||0)+1);}
    assert(!JSON.stringify(row).includes('SENTINEL_PRIVATE_PASSWORD_20'),'Password sentinel reached browser-boundary.jsonl');
  }
  assert(events>0&&getters>0,'Missing protocol or sensitive-getter coverage');
  const ownerOverlap=assertOwnerOverlap('recheck-owner-overlap',ownerRows,ownerTraces);
  assert.deepEqual(ownerOverlap,json(path.join(folder,'owner-overlap.json')),'owner overlap must match raw private observations and independent receiver');
  for(const name of ['tool.jsonl','service.txt'])assert(!await containsText(path.join(folder,name),'SENTINEL_PRIVATE_PASSWORD_20'),`Password sentinel reached ${name}`);
  const pyProof=json(path.join(folder,'python-shards.json'));
  assert.equal(pyProof.shards.length,4);assert(pyProof.shards.every(row=>row.successful===true));
  assert.equal(new Set(pyProof.modules).size,pyProof.modules.length);
  assert.deepEqual([...pyProof.modules].sort(),fs.readdirSync('control/chrome_tests').filter(name=>/^test_.*\.py$/.test(name)).map(name=>name.slice(0,-3)).sort());
  const aggregate=json(path.join(folder,'aggregate-complete.json'));
  assert(precedenceVerdict(json(path.join(folder,'chrome-precedence.json')),read('control/generated/chrome-instructions.txt').replace(/\n$/,''),{head:aggregate.head,run:aggregate.run}));
  const rawDestinations=[],destinationSnapshots=[],destinationContexts=[];
  for await(const row of jsonLines(path.join(folder,'receiver.jsonl')))if(caseId(row)?.startsWith('post18d-destination-'))rawDestinations.push(row);
  for await(const row of jsonLines(path.join(folder,'page-receiver.jsonl')))if(row.id.startsWith('post18d-destination-'))destinationSnapshots.push(row);
  for await(const row of jsonLines(path.join(folder,'native-compatibility.jsonl')))if(row.phase==='destination-context')destinationContexts.push(row);
  const destinations=assertDestinations(json(path.join(folder,'destinations.json')),destinationSnapshots,rawDestinations,destinationContexts);
  const late=json(path.join(folder,'late-reader.json'));assert.equal(late.length,3);assert(!JSON.stringify(late).includes('SENTINEL_PRIVATE_PASSWORD_20'));
  assert(late[2].approved.untrusted_content);assert(!late[2].repeat.untrusted_content);assert(late[2].reasked.approval);

  const node=Object.fromEntries([...read(path.join(folder,'node.txt')).matchAll(/^(?:# |ℹ )?(tests|pass|fail|cancelled|skipped)\s+(\d+)/gm)].map(match=>[match[1],Number(match[2])]));
  assert(node.tests>=340);assert.deepEqual(node,{tests:node.tests,pass:node.tests,fail:0,cancelled:0,skipped:0});
  const hashes={};for(const name of ['browser.txt','matrices.json','receiver.jsonl','page-receiver.jsonl','adapters-receiver.jsonl','browser-boundary.jsonl','tool.jsonl','service.txt','python-shards.json','node.txt','owner-overlap.json','all-native-limit.json','all-native-limit-audit.json','clipboard-report.json','network-restart-audit.json','recheck3.json'])hashes[name]=await digestFile(path.join(folder,name));
  results.push({artifact:path.basename(folder),chrome:read(path.join(folder,'chrome-version.txt')).trim(),named_passes:rows.length,test_index:testIndex,verdicts:verdict,receiver_audit:receiverAudits,native_limit:nativeLimit,recheck3,destinations,group12:true,late_reader:{cases:late.length},clipboard:{cases:clipboard.length,contents_returned:false,borrowed_native_undetected:true},ordinary_get_queries:queryRows,owner_overlap:ownerOverlap,password_audit:{rows:ingress,null_rows:nullRows,protocol_events:events,forbidden_runtime_value_events:0,sensitive_getters:getters,getter_kinds:Object.fromEntries(getterKinds),password_sentinel_absent:true},python:{tests:pyProof.tests,shards:pyProof.shards.length},node,sha256:hashes});
}
assert(results.length>0,'No artifacts found');
console.log(JSON.stringify(results,null,2));
