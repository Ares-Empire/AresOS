import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';
const fixtureSource=fs.readFileSync('control/chrome_tests/page.test.mjs','utf8');
const {fixture}=await import('data:text/javascript;base64,'+Buffer.from(fixtureSource.slice(0,fixtureSource.indexOf('\ntest('))+'\nexport {fixture};').toString('base64'));
const rows=[];
for(const mode of ['open','closed']){
  const f=fixture({relay:true,nativeShadows:true,activate:false});
  const create=Object.getPrototypeOf(f.document).createElement;f.factory.activate();
  const host=new f.HTMLElement();f.arm(host,null);
  const root=f.nativeAttach.call(host,{mode}),link=create.call(f.document,'a');
  link.tagName='A';link.textContent='Delete';let handlers=0;
  f.nativeListen.call(link,'click',()=>handlers++);f.nativeAppend.call(root,link);
  f.originalDispatch.call(link,new f.Event('click',{bubbles:true,composed:false,cancelable:true}));
  rows.push({mode,handlers,held:f.reports.length,expected_handlers:0,expected_held:1});
  f.cleanup();f.guard.dispose();
}
const result={kind:'FAILURE EVIDENCE, NOT ACCEPTANCE',fixture_sha256:crypto.createHash('sha256').update(fixtureSource).digest('hex'),rows};
fs.writeFileSync('reviews/20-chrome/records/recheck2/native-production-gap.json',JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result));
assert.ok(rows.every(row=>row.handlers===0&&row.held===1),'Every borrowed-native noncomposed activation must stop its handler and report it');
