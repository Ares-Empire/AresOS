import test from 'node:test';
import assert from 'node:assert/strict';
import {destinationRows,destinationExpectation,destinationPage,finalTargetRows} from '../chrome/ci/destination-fixtures.mjs';
import {assertDestinations} from '../chrome/ci/destination-evidence.mjs';
function fixture(){
  const evidence=[],snapshots=[],arrivals=[],contexts=[];
  for(const row of destinationRows()){
    const expected=destinationExpectation(row);
    const before={tab:77,target:{href:'http://fixture.test'+expected.before.path,browsing_target:expected.before.target}},after={tab:77,target:{href:'http://fixture.test'+expected.after.path,browsing_target:expected.after.target}};
    const approval=state=>({operation_id:state===before?'old':'fresh',description:{untrusted_content:{page_state:state}}});
    const context={id:row.id,phase:'destination-context',name:expected.top?'':expected.sink,top:expected.top,url:after.target.href+'?case='+row.id};contexts.push(context);
    evidence.push({...row,prepared:{approval:approval(before)},reasked:{operation:{state:'failed'},approval:approval(after)},context,nativeTab:{tab:77,controlled:true,url:context.top?context.url:'http://fixture.test/?case=review-page&id='+row.id}});
    for(const [phase,count] of [['changed destination held',0],['stale destination approval stays retired',0],['before approval',0],['after approval',1],['after repeat',1]])snapshots.push({id:row.id,phase,count});
    arrivals.push({url:new URL(after.target.href).pathname+'?case='+row.id});
  }
  return {evidence,snapshots,arrivals,contexts};
}
test('post18d independent destination audit requires every source and zero arrivals through stale approval',()=>{
  const f=fixture();assert.equal(assertDestinations(f.evidence,f.snapshots,f.arrivals,f.contexts).cases,96);
  for(const mutate of [f=>f.evidence.pop(),f=>f.contexts.pop(),f=>f.evidence[0].nativeTab.url='http://fixture.test/?id=wrong',f=>f.contexts[0].top=true,f=>f.snapshots[0].count=1,f=>f.arrivals.push(f.arrivals[0]),f=>f.evidence[0].reasked.approval.operation_id='old',f=>f.arrivals[0].url=f.arrivals[0].url.replace('/second/','/first/')]){
    const changed=fixture();mutate(changed);assert.throws(()=>assertDestinations(changed.evidence,changed.snapshots,changed.arrivals,changed.contexts));
  }
});

const FINAL_F3_ROUTES={
  'decoy-target':['a','area','form-action','button-formaction','input-formaction'],
  'sanitize-newline-target':['a','form-action'],'sanitize-bracket-target':['a','form-action'],
  'xlink-show':['svg-href','svg-xlink'],'empty-target':['a','area','form-action','button-formaction'],
  'owner-target':['form-action','button-formaction','input-formaction'],
};
test('final F3 browser rows for every target route are collected into the destination suite and its audit',()=>{
  const rows=destinationRows(),ids=new Set(rows.map(row=>row.id));assert.equal(ids.size,rows.length,'row ids are unique');
  for(const [change,sources] of Object.entries(FINAL_F3_ROUTES))for(const source of sources)assert.ok(ids.has(`post18d-destination-${source}-top-${change}`),change+' '+source);
  for(const frame of ['top','blank','srcdoc']){
    for(const source of ['area','svg-href','svg-xlink'])assert.ok(ids.has(`post18d-destination-${source}-${frame}-target`),'target change on '+source+' '+frame);
    assert.ok(ids.has(`post18d-destination-form-action-${frame}-owner`),'form owner without formaction '+frame);
  }
  assert.equal(finalTargetRows().length,30);
  const f=fixture(),index=f.evidence.findIndex(row=>row.change==='decoy-target');f.evidence.splice(index,1);
  assert.throws(()=>assertDestinations(f.evidence,f.snapshots,f.arrivals,f.contexts),'the audit requires every final row');
});
test('final F3 destination pages build each route the reader must resolve like Chrome',()=>{
  const page=row=>destinationPage(new URL('http://fixture.test:8765/?case=review-page&mode=destination&'+new URLSearchParams(row)));
  const rows=Object.fromEntries(destinationRows().map(row=>[row.id,row]));
  const decoy=page(rows['post18d-destination-a-top-decoy-target']);assert.ok(decoy.body.indexOf('<svg width="1" height="1"><base target="sink-first"/></svg>')<decoy.body.indexOf('<base id="destination-base"'),'the non-HTML base comes first');
  const newline=page(rows['post18d-destination-a-top-sanitize-newline-target']);assert.match(newline.body,/<base id="destination-base" href="\/first\/" target="sink&#10;first">/);assert.match(newline.body,/<iframe name="sink&#10;second"/);assert.match(newline.script,/\.target="sink\\nsecond"/);
  const bracket=page(rows['post18d-destination-form-action-top-sanitize-bracket-target']);assert.match(bracket.body,/target="sink&lt;first"/);assert.match(bracket.body,/<iframe name="sink&lt;second"/);
  const show=page(rows['post18d-destination-svg-xlink-top-xlink-show']);assert.match(show.body,/<a id="asking" aria-label="Delete" xlink:show="new" xlink:href=/);assert.doesNotMatch(show.body,/<a id="asking"[^>]*target=/);assert.match(show.script,/removeAttributeNS\('http:\/\/www.w3.org\/1999\/xlink','show'\)/);
  assert.match(page(rows['post18d-destination-a-top-empty-target']).body,/<a id="asking" target="" href=/);assert.match(page(rows['post18d-destination-area-top-empty-target']).body,/<area id="asking" target="" /);
  assert.match(page(rows['post18d-destination-form-action-top-empty-target']).body,/<form id="first" target="" method="post"/);assert.match(page(rows['post18d-destination-button-formaction-top-empty-target']).body,/id="asking" formtarget="" form="first"/);
  const owner=page(rows['post18d-destination-form-action-top-owner-target']);assert.match(owner.body,/<form method="post" id="third" target="sink-second" action="receive\?case=/);assert.match(owner.script,/node\.setAttribute\('form','third'\)/);
  for(const frame of ['blank','srcdoc']){assert.match(page(rows[`post18d-destination-area-${frame}-target`]).script,/node\.setAttribute\('target','sink-second'\)/);assert.match(page(rows[`post18d-destination-svg-href-${frame}-target`]).script,/node\.setAttribute\('target','sink-second'\)/);}
  assert.match(page(rows['post18d-destination-svg-href-top-target']).script,/node\.setAttribute\('target','sink-second'\)/,'a plain SVG target change, not the base');
  assert.match(page(rows['post18d-destination-form-action-srcdoc-owner']).script,/node\.setAttribute\('form','second'\)/);
  assert.deepEqual(destinationExpectation(rows['post18d-destination-svg-href-top-xlink-show']),{before:{path:'/first/receive',target:'_blank'},after:{path:'/first/receive',target:'_self'},top:true,sink:null});
  assert.deepEqual(destinationExpectation(rows['post18d-destination-form-action-top-owner']),{before:{path:'/first/receive',target:'sink-first'},after:{path:'/second/receive',target:'sink-first'},top:false,sink:'sink-first'});
});
