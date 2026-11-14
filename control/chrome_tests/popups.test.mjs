// The popup rows against a scripted stand-in for the Linux browser. These
// tests start no browser, process or profile, and touch no file.
import test from 'node:test';
import assert from 'node:assert/strict';
import {popupMatrices,recordedPath,firstAnswer,admittedAfter} from '../chrome/ci/popups.mjs';

const ROWS='GROUP 8 popups preserve opener flow and guard first input without moving windows';
const MODES=['clean','dirty','typed-clean','typed-early','typed-late'];
// The extension's rule as the run sees it: a list is judged on either path;
// a text field reloads without asking only after a document-start install.
const extension=(mode,path)=>mode==='clean'?'stale_reference':mode==='dirty'?'reload_required':path==='document_start'?'stale_reference':'reload_required';

// Tab 7 is the opener. A popup Claude's click opens is admitted at once; its
// document loads with the race's path, unless the fixture holds it: then it
// is admitted on the second look at the boundary log, and the path is
// document_start only if the hold was released after that. A popup the owner
// opens loads at once and gets the late path when Claude takes it.
function browser({race='late',answer=extension,records=null}={}){
  const opener={tab:7,controlled:true,url:'http://fixture.test:8765/?case=compose'},popups=new Map(),arrivals=[],holds=new Map(),seen=[];
  let next=20,generation=0,log='',looks=0;
  const arrive=(kind,body='')=>arrivals.push({url:'/receive?case='+kind,body});
  const load=popup=>{popup.loaded=true;popup.document='document-'+(++generation);arrive('loaded-'+popup.id,JSON.stringify({opener:true,name:'popup-'+popup.id}));};
  const admit=popup=>{popup.admitted=true;log+=JSON.stringify({popup_admitted:{tab:popup.tab,window:popup.tab,type:'popup',opener:7,badge:'POP on opener'}})+'\n';};
  const open=(id,mode,byClaude)=>{
    const popup={tab:next++,id,mode,controlled:byClaude,loaded:false,admitted:false,path:null};popups.set(popup.tab,popup);
    if(!byClaude){load(popup);return popup;}
    if(holds.has(id)){popup.waiting=true;return popup;}
    admit(popup);popup.path=race;load(popup);return popup;
  };
  const byId=id=>[...popups.values()].find(popup=>popup.id===id);
  const url=popup=>popup.loaded?'http://popup.test:8766/?case=popup-child&id='+popup.id+'&mode='+popup.mode:'';
  const tree=rows=>({untrusted_content:{tree:rows.map(row=>JSON.stringify(row)).join('\n')}});
  const harness={
    getTab:()=>7,setTab:()=>{},
    check:async(name,run)=>{if(name===ROWS)await run();},
    nav:async kind=>{const parameters=new URLSearchParams(kind);opener.page={id:parameters.get('id'),mode:parameters.get('mode')};},
    counts:kind=>arrivals.filter(row=>new URL(row.url,'http://fixture.test').searchParams.get('case')===kind).length,
    eventually:async(predicate,label)=>{for(let attempt=0;attempt<20;attempt++){const value=await predicate();if(value)return value;}throw Error(label);},
    fixture:{arrivals,hold:id=>{holds.set(id,true);return ()=>{holds.delete(id);const popup=byId(id);if(popup?.waiting){popup.waiting=false;popup.path=popup.admitted?'document_start':'late';load(popup);}};}},
    boundary:{size:()=>log.length,since:offset=>{looks++;for(const popup of popups.values())if(popup.waiting&&!popup.admitted&&looks>=2)admit(popup);return log.slice(offset);}},
    popupEvidence:async id=>({window:'native-'+id,X:0,Y:0,WIDTH:620,HEIGHT:480}),
    popupControl:async command=>{
      assert.equal(command,'state');
      const installs=[...popups.values()].filter(popup=>popup.controlled&&popup.loaded).map(popup=>({tab:popup.tab,document:popup.document,install:popup.path,ready:popup.path==='document_start'}));
      return {installs:records?records(installs,popups):installs};
    },
    ownerOpenPopup:async(tab,{id,mode})=>{assert.equal(tab,7);opener.controlled=false;const popup=open(id,mode,false);return {tab:popup.tab,url:url(popup),controlled:false};},
    approval:async(result,id)=>{assert.ok(result.approval);arrive(id);arrive('flow-'+id);},
    call:async(name,args={})=>{
      if(name==='tabs')return {items:[{tab:7,window:1,url:opener.url,controlled:opener.controlled},...[...popups.values()].map(popup=>({tab:popup.tab,window:popup.tab,url:url(popup),controlled:popup.controlled}))]};
      if(name==='read'){
        if(args.tab===7)return tree([{expected:{name:'Open window'},reference:{tab:7,document:'opener'}}]);
        const popup=popups.get(args.tab);assert.ok(popup.loaded&&popup.controlled,'read a loaded controlled popup');
        return tree([{expected:{name:'Continue'},reference:{tab:popup.tab,document:popup.document}}]);
      }
      if(name==='click'){
        if(args.reference.tab===7){assert.equal(opener.controlled,true);open(opener.page.id,opener.page.mode,true);return {};}
        return {approval:{operation:'fixture'}};
      }
      if(name==='take_tab'){
        if(args.tab===7){opener.controlled=true;return {};}
        const popup=popups.get(args.tab);assert.equal(opener.controlled,true,'a popup is taken with its opener');popup.controlled=true;popup.path='late';return {};
      }
      if(name==='close_tab'){popups.delete(args.tab);return {};}
      throw Error('unexpected call '+name);
    },
    rpc:async(name,{reference,discard_unsaved})=>{
      assert.equal(name,'click');const popup=popups.get(reference.tab);
      if(reference.document!==popup.document)return {ok:false,error:{code:'stale_reference'}};
      const code=answer(popup.mode,popup.path);seen.push({mode:popup.mode,path:popup.path,code});
      if(code==='reload_required'&&discard_unsaved!==true)return {ok:false,error:{code}};
      popup.path='document_start';load(popup);return {ok:false,error:{code:'stale_reference'}};
    },
  };
  return {harness,seen,holds};
}

test('popup rows: each install path gives its exact first answer, and the forced rows get their paths',async()=>{
  for(const race of ['document_start','late']){
    const {harness,seen,holds}=browser({race});await popupMatrices(harness);
    const first=Object.fromEntries(seen.map(row=>[row.mode,row]));
    assert.deepEqual(Object.keys(first),MODES);
    assert.deepEqual({path:first['typed-early'].path,code:first['typed-early'].code},{path:'document_start',code:'stale_reference'});
    assert.deepEqual({path:first['typed-late'].path,code:first['typed-late'].code},{path:'late',code:'reload_required'});
    assert.deepEqual({path:first['typed-clean'].path,code:first['typed-clean'].code},{path:race,code:race==='late'?'reload_required':'stale_reference'});
    assert.equal(holds.size,0,'every hold is released');
  }
});

test('popup rows: an answer against the recorded path fails its row, on either path',async()=>{
  // The stand-in turns one row's answer around and stays consistent with it:
  // a click that asks reloads only with discard_unsaved, one that reloads does.
  for(const [mode,race] of [['typed-early','late'],['typed-late','late'],['typed-clean','late'],['typed-clean','document_start']]){
    const flipped=(row,path)=>{const code=extension(row,path);return row!==mode?code:code==='stale_reference'?'reload_required':'stale_reference';};
    const {harness}=browser({race,answer:flipped});
    await assert.rejects(popupMatrices(harness),error=>error instanceof assert.AssertionError&&error.message.includes(mode+' on the'),mode+' '+race);
  }
});

test('popup rows: a forced row whose record names the other path fails, even with a matching answer',async()=>{
  // typed-early released before the admission: the stand-in loads it late.
  const early=browser();early.harness.boundary={size:()=>0,since:()=>JSON.stringify({popup_admitted:{tab:99,type:'popup',opener:7}})+'\n'};
  await assert.rejects(popupMatrices(early.harness),/typed-early must get the install path it forces/);
  // typed-late recorded as a document-start install.
  const late=browser({records:(rows,popups)=>rows.map(row=>popups.get(row.tab).mode==='typed-late'?{...row,install:'document_start',ready:true}:row),answer:(mode,path)=>mode==='typed-late'?'stale_reference':extension(mode,path)});
  await assert.rejects(popupMatrices(late.harness),/typed-late must get the install path it forces/);
});

test('popup rows: the path is read only from the extension record for this popup document',async()=>{
  for(const records of [()=>[],rows=>[...rows,...rows]]){
    const {harness}=browser({records});await assert.rejects(popupMatrices(harness),/exactly one install record/);
  }
  // Records for another tab or another document of this tab never decide it.
  const {harness,seen}=browser({race:'late',records:rows=>rows.flatMap(row=>[row,{...row,tab:row.tab+100,install:'document_start',ready:true},{...row,document:'other-document',install:'document_start',ready:true}])});
  await popupMatrices(harness);
  const first=Object.fromEntries(seen.filter(row=>row.mode.startsWith('typed-')).reverse().map(row=>[row.mode,row.code]));
  assert.deepEqual(first,{'typed-clean':'reload_required','typed-early':'stale_reference','typed-late':'reload_required'});
});

test('popup rows: an unfinished document-start install and unknown rows have no answer',()=>{
  assert.throws(()=>recordedPath({installs:[{tab:8,document:'d',install:'document_start',ready:false}]},8,'d'),/unknown install record/);
  assert.throws(()=>recordedPath({},8,'d'),/exactly one install record/);
  assert.equal(recordedPath({installs:[{tab:8,document:'d',install:'late',ready:false}]},8,'d'),'late');
  assert.throws(()=>firstAnswer('typed-clean',null),/unknown install path/);
  assert.throws(()=>firstAnswer('typed-other','late'),/unknown popup row/);
});

test('popup rows: the admission line names the opener and a popup window',()=>{
  const line=value=>JSON.stringify(value)+'\n';
  assert.equal(admittedAfter(line({popup_admitted:{tab:9,type:'popup',opener:7}}),7),true);
  assert.equal(admittedAfter(line({popup_admitted:{tab:9,type:'popup',opener:8}})+line({popup_admitted:{tab:9,type:'normal',opener:7}}),7),false);
  assert.equal(admittedAfter('{"popup_admitted":{"tab":9,"type":"popup","opener":7}}',7),true,'a whole line is enough without its newline');
  assert.equal(admittedAfter('{"popup_admitted":{"tab":9,"type":"pop',7),false,'a line still being written is not one');
});
