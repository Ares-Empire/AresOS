// Native UI is mocked: these tests start no process, browser or profile.
import test from 'node:test';
import assert from 'node:assert/strict';
import {ownerUI} from '../chrome/ci/owner-ui.mjs';
import {popupMatrices} from '../chrome/ci/popups.mjs';

async function eventually(fn,label){let error;for(let n=0;n<12;n++)try{const value=await fn();if(value)return value;}catch(cause){error=cause;}throw Error(label+': '+error?.message);}
function fixture(){
  const state={selected:0,restoring:0,typed:null,commands:[],geometry:0,nativeWindow:'77',rows:[{tab:10,index:0,window:5,url:'http://other.test/'},{tab:11,index:1,window:5,url:'http://fixture.test/'}]};
  const call=async()=>({items:state.rows.map((row,index)=>({...row,active:index===state.selected,focused:true,cleanup_pending:row.tab===11&&state.restoring-->0}))});
  const exec=(command,args)=>{
    state.commands.push([command,...args]);
    if(args[0]==='key')for(const key of args){if(key==='ctrl+1')state.selected=0;if(key==='ctrl+Tab')state.selected=(state.selected+1)%state.rows.length;if(key==='Return')state.rows[state.selected].url=state.typed;}
    if(args[0]==='type')state.typed=args.at(-1);
    if(args[0]==='search')return state.nativeWindow+'\n';
    if(args[0]==='getwindowgeometry'){state.geometry++;return 'X=-8\nY=20\nWIDTH='+(state.geometry===1?0:620)+'\nHEIGHT='+(state.geometry===1?0:514)+'\n';}
    return '';
  };
  return {state,ui:ownerUI({call,currentTab:()=>11,window:()=> 'native-root',eventually,exec})};
}
test('owner navigation selects the exact native tab after restoration changes its index',async()=>{
  const {state,ui}=fixture();state.restoring=2;
  await ui.navigate('http://fixture.test/changed');
  assert.equal(state.rows[1].url,'http://fixture.test/changed');assert.equal(state.rows[0].url,'http://other.test/');
  assert.ok(state.commands.some(args=>args.includes('ctrl+Tab')));assert.equal(state.selected,1);
});
test('missing native position refuses before typing into any tab',async()=>{
  const {state,ui}=fixture();delete state.rows[1].index;
  await assert.rejects(ui.navigate('http://fixture.test/changed'),/native tab index/);assert.equal(state.commands.length,0);
});
test('popup comparison waits for positive mapped geometry and retains native window identity',async()=>{
  const {state,ui}=fixture();const before=await ui.popupWindow('popup-clean');
  assert.deepEqual(before,{window:'77',X:-8,Y:20,WIDTH:620,HEIGHT:514});assert.equal(state.geometry,3);
  assert.deepEqual(await ui.popupWindow('popup-clean'),before);
  state.nativeWindow='78';assert.notDeepEqual(await ui.popupWindow('popup-clean'),before,'a replacement native window cannot pass the comparison');
});
test('popup cases use the recovered opener rather than a captured retired tab',async()=>{
  let current=7,checks=0,readTab;
  const stop=Error('stop after independently checking the next case target');
  await assert.rejects(popupMatrices({getTab:()=>current,
    check:async(name,fn)=>{if(checks++===0){current=8;return;}await fn();},
    nav:async()=>{},call:async(name,args)=>{if(name==='read'){readTab=args.tab;return {untrusted_content:{tree:JSON.stringify({expected:{name:'Open window'},reference:{tab:args.tab}})}};}return {};},
    approval:async()=>{throw stop;},
  }),error=>error===stop);
  assert.equal(readTab,8);
});
