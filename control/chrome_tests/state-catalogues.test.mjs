import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

function fixture(){
  let now=0,id=0,searches=0;
  const rows=Array.from({length:80},(_,index)=>({id:String(index),url:'http://fixture.test/catalogue/'+index}));
  const search=async()=>{searches++;return rows.map(row=>({...row}));};
  const source=fs.readFileSync('control/chrome/extension/background.js','utf8');
  const context=vm.createContext({Date:{now:()=>now},crypto:{randomUUID:()=>String(++id)},session:'fixture-session',
    listSnapshots:new Map(),stable:JSON.stringify,chrome:{downloads:{search},history:{search},bookmarks:{search}}});
  vm.runInContext(source.slice(source.indexOf('async function collection('),source.indexOf('async function dispatch(')),context);
  return {read:command=>vm.runInContext(`collection(${JSON.stringify(command)})`,context),advance:milliseconds=>{now+=milliseconds;},
    searches:()=>searches,run:code=>vm.runInContext(code,context),rows};
}

test('active catalogue paging outlives five minutes without changing its captured rows',async()=>{
  for(const name of ['downloads','history','bookmarks']){
    const f=fixture(),expected=f.rows.map(row=>row.id),seen=[];
    let page=await f.read({name,text:'fixture.test',limit:2});
    f.rows.splice(0,f.rows.length,{id:'replacement',url:'http://fixture.test/replacement'});
    for(;;){
      seen.push(...page.items.map(row=>row.id));
      if(!page.cursor)break;
      f.advance(240000);
      page=await f.read({name,text:'fixture.test',limit:2,cursor:page.cursor});
    }
    assert.deepEqual(seen,expected);assert.equal(f.searches(),1);
  }
});

test('idle catalogue snapshots still expire after five minutes',async()=>{
  const f=fixture(),page=await f.read({name:'history',text:'fixture.test',limit:2});
  f.advance(300001);
  await assert.rejects(f.read({name:'history',text:'fixture.test',limit:2,cursor:page.cursor}),/stale_reference/);
});

test('invalid cursors cannot renew a snapshot and retained snapshots stay bounded',async()=>{
  const f=fixture(),page=await f.read({name:'history',text:'fixture.test',limit:2});
  f.advance(240000);
  await assert.rejects(f.read({name:'history',text:'other.test',limit:2,cursor:page.cursor}),/stale_reference/);
  await assert.rejects(f.read({name:'history',text:'fixture.test',limit:2,cursor:page.cursor.split(':')[0]+':9999'}),/stale_reference/);
  f.advance(60001);
  await assert.rejects(f.read({name:'history',text:'fixture.test',limit:2,cursor:page.cursor}),/stale_reference/);
  for(const text of ['first.test','second.test','third.test'])await f.read({name:'history',text,limit:2});
  assert.equal(f.run('listSnapshots.size'),2);
});
