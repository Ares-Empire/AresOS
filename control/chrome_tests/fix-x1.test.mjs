// Regression descendants of the two reviewers' scratch reader/service probes.
import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {page} from './outline-dom.mjs';

const marker='withheld-fixture-text';
function service(data){
  const result=spawnSync('python3',['control/chrome_tests/x1_service_probe.py'],{input:JSON.stringify(data),encoding:'utf8',
    env:{...process.env,PYTHONDONTWRITEBYTECODE:'1',PYTHONPATH:'control:control/chrome_tests'}});
  assert.equal(result.status,0,result.stderr);return JSON.parse(result.stdout);
}
const typed=[undefined,'text','search','email','url','tel','number','unrecognised'];
for(const context of ['watched','unwatched','late-root'])for(const role of ['none','presentation'])for(const protection of ['history','credential']){
  test(`X1 withholding: ${context}, role ${role}, ${protection}`,()=>{
    const withheld=protection==='credential'||context!=='watched';let host;
    const controls=h=>{
      const attrs={'aria-label':protection==='credential'?'Password':'Notes',role,value:withheld?marker:'live readable text',$secret:withheld};
      const kinds=protection==='credential'?[...typed,'password','checkbox','radio','range','color','date','time','datetime-local','month','week','file','button','submit','reset','image']:typed;
      const nodes=[h('textarea',attrs,marker),...kinds.map(type=>h('input',{...attrs,...(type?{type}:{})}))];
      if(protection==='credential')nodes.push(h('select',attrs,h('option',{},marker)),h('button',attrs,marker),h('div',{...attrs,contenteditable:'true'},marker));
      return nodes;
    };
    const f=page(h=>context==='late-root'?[host=h('div')]:controls(h),{watched:context!=='unwatched'});
    if(host){f.outline();f.h.shadow(host,...controls(f.h));}
    // Use the raw reply so the service check independently sees a leaked text node on the baseline.
    const raw=f.run({command:'outline'});assert.equal(raw.ok,true,JSON.stringify(raw));
    const results=service({mode:'reads',outline:raw.data,needle:marker});
    for(const result of results){
      assert.equal(result.ok,true,JSON.stringify(result));
      assert.ok(!JSON.stringify(result).includes(marker),'default/withheld text reached outline, full or find');
      assert.equal(result.data.reads[0].typed_fields,protection==='history'&&withheld?typed.length+1:0);
    }
    const nodes=f.outline().nodes;
    assert.equal(nodes.length,controls(f.h).length);
    if(withheld)assert.ok(nodes.every(node=>node.unread));
    else assert.ok(nodes.every(node=>node.value==='live readable text'));
  });
}

for(const kind of ['files','selection'])for(const check of ['token','until','cursor'])test(`X1 ${kind}: ${check}`,()=>{
  const f=page(h=>[h('p',{},'unchanged prefix '.repeat(150)),kind==='files'?h('input',{type:'file','aria-label':'Attachment'}):
    h('select',{'aria-label':'Choice'},h('option',{selected:''},'First choice'),h('option',{},'Second choice'))]);
  const element=f.body.childNodes[1];let files=[{name:'first.txt'}];
  if(kind==='files')Object.defineProperty(element,'files',{get:()=>files});
  const capture=()=>({outline:f.outline(),state:f.run({command:'page_state'}).data});
  const before=capture();
  if(kind==='files')files=[{name:'second.txt'}];
  else{delete element.options[0].attrs.selected;element.options[1].attrs.selected='';}
  const after=capture(),needle=kind==='files'?'second.txt':'Second choice';
  if(check==='token'){assert.notEqual(before.state.fields,after.state.fields,'the live field digest must change');return;}
  const result=service({mode:'state',before,after,needle});
  if(check==='cursor'){assert.ok(result.cursor);assert.equal(result.continued.data.reads[0].error?.code,'stale_reference');}
  else{assert.equal(result.waited.data.reads[0].until_met,true);assert.equal(result.calls.filter(([name])=>name==='outline').length,2);}
});
