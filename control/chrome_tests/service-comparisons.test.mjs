// Service-held facts came through respond; fresh DOM/CDP facts have not.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source=fs.readFileSync('control/chrome/extension/background.js','utf8');
const mutations={
  'remove-initial-binding':['stable(wellFormed(binding(snapshot,reference,command.kind,command.adapter))) !==','stable(binding(snapshot,reference,command.kind,command.adapter)) !=='],
  'remove-final-binding':['stable(wellFormed(binding(snapshot,reference,command.kind,command.adapter)))!==','stable(binding(snapshot,reference,command.kind,command.adapter))!=='],
  'remove-expected':['stable(wellFormed(target))','stable(target)'],
  'remove-typed-binding':['stable(wellFormed(current))!==stable(command.binding)','stable(current)!==stable(command.binding)'],
  'remove-dialog-binding':['stable(wellFormed(expected))!==stable(command.binding)','stable(expected)!==stable(command.binding)'],
  'remove-confirmation':['expected[key]===wellFormed(dialog[key])','expected[key]===dialog[key]'],
  'remove-option-value':['wellFormed(option.value)===input.value','option.value===input.value'],
};
function fixture(){
  let code=source.replace("import {POLICY} from './policy.js';",'');
  const mutation=process.env.SERVICE_COMPARISON_MUTATION;
  if(mutation){
    assert.ok(Object.hasOwn(mutations,mutation));const [before,after]=mutations[mutation];
    assert.equal(code.split(before).length,2,mutation+' has exactly one site');code=code.replace(before,after);
  }
  const listener=code.slice(code.indexOf('chrome.debugger.onEvent.addListener('),code.indexOf('chrome.debugger.onDetach.addListener('));
  code=code.slice(0,code.indexOf('async function connect()'));
  const wires=[],context=vm.createContext({POLICY:{holdMs:100},chrome:{},URL,TextEncoder,performance,
    crypto:{randomUUID:()=> 'fixture-session'},setTimeout,clearTimeout});
  vm.runInContext(code,context);
  const run=code=>vm.runInContext(code,context);
  context.nativePort={postMessage:value=>wires.push(JSON.stringify(value))};
  run(`port=nativePort;excludedHosts=[];controlled.set(7,{epoch:'epoch'});dispatchEpoch='epoch';
    globalThis.inputs=0;globalThis.valueReads=0;
    requireTab=async()=>({url:'https://fixture.test/',title:pageTitle});
    globalThis.pageTitle='Page';
    safeDestination=()=>{};holdDefaults=async()=>{};armedDocument=()=>{};expireDefaults=()=>{};
    finishFrames=async()=>false;collectSteps=async()=>[];observation=async()=>({});
    readyDialog=async()=>null;content=async()=>({});
    chrome.tabs={get:async()=>({active:true})};
    chrome.webNavigation={getAllFrames:async()=>[{frameId:0,parentFrameId:-1,documentId:'native',url:'https://fixture.test/'}]};
    pointer=async()=>({x:2,y:2});cdp=async()=>{inputs++;return {}};
    armDialog=async()=>({owner:controlled.get(7),frames:[],nonce:'nonce',ready:Promise.resolve()});`);
  return {run,listen:()=>run(listener),set:(name,value)=>{context[name]=value;},sent(expression){run(`respond({id:'facts',ok:true,data:${expression}})`);return JSON.parse(wires.at(-1)).data;}};
}
function inputFixture(){
  const f=fixture();
  f.run(`globalThis.reference={session,tab:7,frame:0,document:'doc',element:'e1'};
    globalThis.snapshot={session,tab:7,control:'epoch',url:'https://fixture.test/',title:'Page',dialog:null,
      frames:[{frame:0,parent:-1,document:'doc',browser_document:'native',url:'https://fixture.test/',title:'Frame',
        target:{element:'e1',role:'button',name:'Continue',label:'Label',title:'Hint',value:'Value',rich:'Markup',
          states:{},options:[{label:'One',value:'one'}],box:{x:1,y:1,width:10,height:10}},
        form:{element:'e2',action:'https://fixture.test/',fields:[{element:'e3',label:'Draft',value:'Body'}]},
        compose:{text:'Preview'},selected_files:[{label:'Attachment'}],editable:[{label:'Editor',value:'Body'}],
        item:'Item',item_fields:[{label:'Quantity',value:'1'}],adapter:{label:'Adapter'}}]};
    globalThis.factCalls=0;globalThis.changeAt=0;globalThis.change=()=>{};
    facts=async()=>{if(++factCalls===changeAt)change();return snapshot;};
    globalThis.command={name:'input',tab:7,reference,input:{verb:'click'},kind:'confirmation',operation:'op'};`);
  return f;
}

// Exercise each bound area, not just the title that exposed H1's failure.
const boundText=[
  'snapshot.title','snapshot.frames[0].title',
  ...['name','label','title','value','rich'].map(key=>'snapshot.frames[0].target.'+key),
  'snapshot.frames[0].target.options[0].label','snapshot.frames[0].form.fields[0].label',
  'snapshot.frames[0].form.fields[0].value','snapshot.frames[0].compose.text',
  'snapshot.frames[0].selected_files[0].label','snapshot.frames[0].editable[0].value',
  'snapshot.frames[0].item','snapshot.frames[0].item_fields[0].value',
];
for(const path of boundText)for(const boundary of [1,2])test(`repaired action binding ${boundary}: ${path}; visible changes still refuse`,async()=>{
  for(const replacement of ['same','\ud801','\udc00','Visible change','\ud800 ']){
    const f=inputFixture();f.run(`${path}='Text \\ud800';`);
    f.set('serviceBinding',f.sent('binding(snapshot,reference,command.kind,command.adapter)'));
    f.run('command.binding=serviceBinding');
    const before=f.run('JSON.stringify(snapshot)');
    if(replacement!=='same')f.run(`changeAt=${boundary};change=()=>{${path}=${JSON.stringify('Text '+replacement)}}`);
    const accepted=['same','\ud801','\udc00'].includes(replacement);
    if(accepted){assert.equal((await f.run('dispatch(command)')).dispatched,true);assert.equal(f.run('inputs'),2);}
    else {await assert.rejects(f.run('dispatch(command)'),boundary===1?/stale_approval: page changed;/:/stale_approval: page changed during frame setup/);assert.equal(f.run('inputs'),0);}
    if(replacement==='same')assert.equal(f.run('JSON.stringify(snapshot)'),before,'comparison repair never mutates facts');
  }
});

for(const key of ['name','label','title','value','rich'])test(`repaired command.expected: ${key}; visible changes still refuse`,async()=>{
  for(const changed of [false,true]){
    const f=inputFixture();f.run(`snapshot.frames[0].target.${key}='Text \\ud800'`);
    f.set('expected',f.sent('snapshot.frames[0].target'));f.run('command.expected=expected');
    if(changed)f.run(`snapshot.frames[0].target.${key}+=' '`);
    if(changed){await assert.rejects(f.run('dispatch(command)'),/stale_reference: element no longer holds/);assert.equal(f.run('inputs'),0);}
    else assert.equal((await f.run('dispatch(command)')).dispatched,true);
  }
});

test('repaired select value resolves one raw option; visible changes and repaired collisions refuse',async()=>{
  for(const variant of ['same','surrogate-only','visible','ambiguous','disabled']){
    const f=inputFixture();f.run(`command.input={verb:'select',value:'Option \\ufffd'};
      snapshot.frames[0].target.options=[{label:'Choice',value:'Option \\ud800'}];
      globalThis.selected=[];content=async(tab,frame,name,message)=>{if(name==='select')selected.push(message.value);return {}};`);
    // No binding here: isolate the value lookup rather than an earlier binding refusal.
    if(variant==='surrogate-only')f.run("snapshot.frames[0].target.options[0].value='Option \\udc00'");
    if(variant==='visible')f.run("snapshot.frames[0].target.options[0].value+=' '");
    if(variant==='ambiguous')f.run("snapshot.frames[0].target.options.push({label:'Other',value:'Option \\ud801'})");
    if(variant==='disabled')f.run('snapshot.frames[0].target.options[0].disabled=true');
    if(['same','surrogate-only'].includes(variant)){
      assert.equal((await f.run('dispatch(command)')).dispatched,true);
      assert.equal(f.run('selected.length'),1);assert.equal(f.run('selected[0]'),variant==='same'?'Option \ud800':'Option \udc00');
      assert.equal(f.run('snapshot.frames[0].target.options[0].value'),f.run('selected[0]'),'send the existing raw option without rewriting it');
    }else{
      await assert.rejects(f.run('dispatch(command)'),/stale_reference: the exact enabled option is missing or ambiguous/);
      assert.equal(f.run('selected.length'),0);
    }
  }
});

test('select without native option facts keeps the reader refusal before comparing or setting values',async()=>{
  const f=inputFixture();f.run(`command.input={verb:'select',value:'Choice'};delete snapshot.frames[0].target.options;
    content=async(tab,frame,name)=>{if(name==='select')throw Error('refused: choose an enabled native select control');return {}};`);
  await assert.rejects(f.run('dispatch(command)'),/^Error: refused: choose an enabled native select control$/);
  assert.equal(f.run('inputs'),0);
});

function typedFixture(){
  const f=fixture();
  f.run(`globalThis.metadata={document:'doc',reader:'reader',origin:'https://fixture.test',url:'https://fixture.test/',title:'Frame',
      fields:[{element:'e1',label:'Draft \\ud800',type:'text'},{element:'e2',label:'single-line field 2',type:'tel'}]};
    pageTitle='Page \\ud800';globalThis.listCalls=0;globalThis.changeAt=0;globalThis.change=()=>{};
    requireTab=async()=>{if(++listCalls===changeAt)change();return {url:'https://fixture.test/',title:pageTitle};};
    content=async(tab,frame,name,message)=>{
      if(name==='typed_fields')return structuredClone(metadata);
      if(name==='read_typed_fields'){
        if(message.expected.fields[0].label!==metadata.fields[0].label)throw Error('The private reader expectation must stay fresh and raw');
        valueReads++;return {fields:[{element:'e1',value:'Approved text'}]};
      }
      throw Error('Unexpected reader command');
    };
    globalThis.command={name:'read_typed_fields',tab:7,approved:true,operation:'op'};`);
  // The real typedFacts collects reader/document identity and labels without values.
  f.set('structuredClone',structuredClone);
  return f;
}
const typedChanges={title:"pageTitle+=' '",label:"metadata.fields[0].label+=' '",
  element:"metadata.fields[0].element='replacement'",type:"metadata.fields[0].type='search'",
  reader:"metadata.reader='replacement'",document:"metadata.document='replacement'",
  added:"metadata.fields.push({element:'e3',label:'Added',type:'text'})",
  order:'metadata.fields.reverse()'};
for(const [name,change] of Object.entries(typedChanges))test(`repaired asking list: ${name}; visible or identity change refuses before values`,async()=>{
  for(const when of [1,2]){
    const f=typedFixture();
    f.set('prepared',await f.run('typedFacts(7)'));f.set('serviceBinding',f.sent('prepared'));
    f.run(`command.binding=serviceBinding;listCalls=0;changeAt=${when};change=()=>{${change}}`);
    await assert.rejects(f.run('dispatch(command)'),name==='document'?/private password history was lost/:/stale_approval: typed-field list or document changed/);
    assert.equal(f.run('valueReads'),0);
  }
});
test('repaired asking list is accepted once without reading values during preparation',async()=>{
  for(const replacement of ['\ud800','\ud801','\udc00']){
    const f=typedFixture();f.set('prepared',await f.run('typedFacts(7)'));assert.equal(f.run('valueReads'),0);
    f.set('serviceBinding',f.sent('prepared'));f.run('command.binding=serviceBinding');
    f.run(`metadata.fields[0].label=${JSON.stringify('Draft '+replacement)};pageTitle=${JSON.stringify('Page '+replacement)}`);
    assert.equal((await f.run('dispatch(command)')).frames.length,1);assert.equal(f.run('valueReads'),1);
    assert.equal(f.run('metadata.fields[0].label.charCodeAt(6)'),replacement.charCodeAt(0),'raw internal label stays raw');
    await assert.rejects(f.run('dispatch(command)'),/fresh one-call approval/);assert.equal(f.run('valueReads'),1);
  }
});
test('asking list is rechecked after values are read',async()=>{
  const f=typedFixture();f.set('prepared',await f.run('typedFacts(7)'));f.set('serviceBinding',f.sent('prepared'));
  f.run("command.binding=serviceBinding;listCalls=0;changeAt=3;change=()=>{pageTitle+=' '}");
  await assert.rejects(f.run('dispatch(command)'),/stale_approval: typed-field list or document changed/);assert.equal(f.run('valueReads'),1);
});

for(const path of ['pageTitle','dialog.text'])test(`repaired dialog answer: ${path}; visible changes still refuse`,async()=>{
  for(const changed of [false,true]){
    const f=fixture();f.run(`globalThis.dialog={frame:0,frame_url:'https://fixture.test/',kind:'confirm',text:'Question \\ud800',id:'dialog'};
      pageTitle='Page \\ud800';readyDialog=async()=>dialog;
      globalThis.command={name:'dialog',tab:7,input:{accept:false}};`);
    f.set('serviceBinding',f.sent("({session,tab:7,control:'epoch',url:'https://fixture.test/',title:pageTitle,dialog})"));
    f.run('command.binding=serviceBinding');if(changed)f.run(`${path}+=' '`);
    if(changed){await assert.rejects(f.run('dispatch(command)'),/stale_approval: dialog or its opener changed/);assert.equal(f.run('inputs'),0);}
    else {assert.equal((await f.run('dispatch(command)')).dispatched,true);assert.equal(f.run('inputs'),1);}
    assert.equal(f.run("dialog.text.charCodeAt(9)"),0xd800);
  }
});

test('repaired anticipated confirmation accepts raw text and refuses a visible change',async()=>{
  for(const ending of ['\ud800','\ud801','\udc00','\ud800 ']){
    const f=fixture();f.run(`chrome.debugger={onEvent:{addListener:fn=>{globalThis.onEvent=fn}}};
      privacyDocuments.set('native','private');nativeDialogStarts.set('[7,"native"]',[{kind:'confirm',document:'private'}]);
      confirmationPlans.set(7,{browser_document:'native',expected:{kind:'confirm',text:'Question \\ufffd',frame_url:'https://fixture.test/',button:'OK',frame:0},matched:[]});`);
    f.listen();
    await f.run(`onEvent({tabId:7},'Page.javascriptDialogOpening',{url:'https://fixture.test/',type:'confirm',message:${JSON.stringify('Question '+ending)}})`);
    assert.equal(f.run('inputs'),ending.endsWith(' ')?0:1);
    assert.equal(f.run('confirmationPlans.get(7).matched.length'),ending.endsWith(' ')?0:1);
    assert.equal(f.run('dialogs.get(7).text'), 'Question '+ending,'CDP text stays raw');
  }
});
