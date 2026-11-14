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
      f.advance(40000);
      page=await f.read({name,text:'fixture.test',limit:2,cursor:page.cursor});
    }
    assert.deepEqual(seen,expected);assert.equal(f.searches(),1);
  }
});

test('idle catalogue snapshots still expire after five minutes',async()=>{
  for(const name of ['downloads','history','bookmarks']){
    const f=fixture();let page=await f.read({name,text:'fixture.test',limit:2});
    f.advance(299999);
    page=await f.read({name,text:'fixture.test',limit:2,cursor:page.cursor});
    f.advance(300000);
    await assert.rejects(f.read({name,text:'fixture.test',limit:2,cursor:page.cursor}),/stale_reference:.*start the list again without a cursor/);
    assert.equal(f.searches(),1,'expired cursors never silently query a new list');
  }
});

test('active catalogue walks expire exactly thirty minutes after creation and must restart',async()=>{
  for(const name of ['downloads','history','bookmarks']){
    const f=fixture();f.advance(123000);
    let page=await f.read({name,text:'fixture.test',limit:2});
    for(let minute=4;minute<=28;minute+=4){
      f.advance(240000);
      page=await f.read({name,text:'fixture.test',limit:2,cursor:page.cursor});
    }
    f.advance(119999);
    page=await f.read({name,text:'fixture.test',limit:2,cursor:page.cursor});
    f.advance(1);
    await assert.rejects(f.read({name,text:'fixture.test',limit:2,cursor:page.cursor}),/stale_reference:.*start the list again without a cursor/);
    f.advance(1);
    await assert.rejects(f.read({name,text:'fixture.test',limit:2,cursor:page.cursor}),/stale_reference:.*start the list again without a cursor/);
    assert.equal(f.searches(),1,'an expired walk does not renew or silently restart');
    f.rows.splice(0,f.rows.length,{id:'replacement',url:'http://fixture.test/replacement'});
    const restarted=await f.read({name,text:'fixture.test',limit:2});
    assert.deepEqual(Array.from(restarted.items,row=>row.id),['replacement']);assert.equal(f.searches(),2);
  }
});

test('new catalogues prune absolute expiry even when the expired snapshot was used last',async()=>{
  const f=fixture();let page=await f.read({name:'history',text:'fixture.test',limit:2});
  const old=page.cursor.split(':')[0];
  for(let minute=4;minute<=28;minute+=4){
    f.advance(240000);
    page=await f.read({name:'history',text:'fixture.test',limit:2,cursor:page.cursor});
  }
  const recent=await f.read({name:'bookmarks',text:'fixture.test',limit:2});
  f.advance(60000);await f.read({name:'history',text:'fixture.test',limit:2,cursor:page.cursor});
  f.advance(60000);await f.read({name:'downloads',text:'fixture.test',limit:2});
  assert.equal(f.run(`listSnapshots.has(${JSON.stringify(old)})`),false);
  assert.equal(f.run(`listSnapshots.has(${JSON.stringify(recent.cursor.split(':')[0])})`),true);
  assert.equal(f.run('listSnapshots.size'),2);
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
