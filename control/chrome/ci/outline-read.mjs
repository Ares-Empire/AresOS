// Brief 28, group 14 in the browser: reading and references, through the
// internal action chrome_outline (the test-only switch, run.sh). They are
// named cases of the core shard (verdicts.mjs): the password case in group 7
// (password_exclusion), the others beside brief 20's FEATURE and VIEW cases.
// They leave nothing pending: each case closes the tabs it opened, and
// Claude's tab is filled only in its own document.
// Each read's outline is kept in /out/outline-read/ (no field values of
// password kind can be in it: the password case checks that first), so the
// expected outlines of the small fixtures can be committed from a green run.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {F3_UNIQUE,ADDRESS_MARK,ADDRESS_LINKS,addressOf} from './efficiency-fixtures.mjs';

const fixtureUrl=(name,query='')=>'http://fixture.test:8765/?case=efficiency-'+name+query;
// A reference ends its line: five consonants of this run, then its number.
const REFERENCES=/ ([bcdfghjklmnpqrstvwxyz]{5})(\d+)$/gm;
const referencesOf=outline=>[...String(outline).matchAll(REFERENCES)].map(match=>({string:match[1]+match[2],letters:match[1]}));
const OUT='/out/outline-read';

export async function outlineReadMatrix({check,call,rpc,nav,target,getTab}){
  fs.mkdirSync(OUT,{recursive:true});
  const opened=[];
  // A case that opens tabs closes them, also when it fails.
  const closing=fn=>async()=>{try{await fn();}finally{while(opened.length)await rpc('close_tab',{tab:opened.pop(),discard_unsaved:true});}};
  // One read through the service's socket; the whole result is kept beside its query.
  const read=async(name,args)=>{
    const result=await rpc('outline',args);
    fs.appendFileSync(OUT+'/calls.jsonl',JSON.stringify({name,args,result})+'\n');
    return result;
  };
  const entryOf=async(name,args)=>{
    const result=await read(name,args);assert.equal(result.ok,true,name+': '+JSON.stringify(result.error));
    const entry=result.data.reads[0];assert.ok(entry&&!entry.error,name+': '+JSON.stringify(entry?.error));
    return {result,entry};
  };
  // Every page of one query, joined; each page holds at least one character.
  const pages=async(name,args)=>{
    let cursor,text='',count=0;
    do{
      const {entry}=await entryOf(name,{...args,...(cursor?{cursor}:{})});
      assert.ok(entry.untrusted_content.outline.length>0||entry.total===0,name+': a page advances');
      text+=entry.untrusted_content.outline;cursor=entry.cursor;count++;
    }while(cursor);
    fs.writeFileSync(OUT+'/'+name+'.txt',text);
    return {text,count};
  };
  const open=async(url,text)=>{
    const tab=(await call('open',{url})).untrusted_content.tab;opened.push(tab);
    const {entry}=await entryOf('open '+text,{tab,until:{text},timeout_ms:6000});
    assert.equal(entry.until_met,true,'loaded: '+text);
    return tab;
  };
  // Passwords (GROUP 7's page): the new read holds no password, in any form of
  // read. No argument names the whole value, so it is in no request either.
  await check('GROUP 7 BRIEF28 the new read holds no password in any form of read',async()=>{
    await nav('password');
    const passwordTab=getTab();
    for(const [name,args] of [['password outline',{tab:passwordTab}],['password full',{tab:passwordTab,full:true,max:40000}],
      ['password find',{tab:passwordTab,find:'SENTINEL'}],['password until',{tab:passwordTab,until:{text:'PRIVATE_PASSWORD_20'},timeout_ms:1000}]]){
      const result=await read(name,args);assert.equal(result.ok,true,JSON.stringify(result.error));
      assert.doesNotMatch(JSON.stringify(result),/SENTINEL_PRIVATE_PASSWORD_20/,name);
      if(args.until)assert.equal(result.data.reads[0].until_met,false,'a password value never meets until');
    }
  });

  // References that can't collide: two tabs show the same page.
  await check('READ BRIEF28 two tabs of one page share no reference and find with role returns its one link',closing(async()=>{
    const first=await open(fixtureUrl('f3'),'Results'),second=await open(fixtureUrl('f3'),'Results');
    const [a,b]=[(await entryOf('f3 tab a',{tab:first})).entry,(await entryOf('f3 tab b',{tab:second})).entry];
    const [ofA,ofB]=[referencesOf(a.untrusted_content.outline),referencesOf(b.untrusted_content.outline)];
    assert.ok(ofA.length>=5&&ofB.length>=5,'both reads issue references: '+ofA.length+', '+ofB.length);
    assert.equal(new Set([...ofA,...ofB].map(reference=>reference.letters)).size,1,'one run, one set of letters');
    const strings=new Set(ofB.map(reference=>reference.string));
    assert.deepEqual(ofA.filter(reference=>strings.has(reference.string)),[],'no reference string in both outlines');
    for(const reference of ofA){
      const result=await read('f3 a in b',{tab:second,ref:reference.string});
      assert.equal(result.ok,true,JSON.stringify(result.error));
      assert.equal(result.data.reads[0].error?.code,'stale_reference',reference.string+' read in the other tab');
    }
    // A reference of tab A still reads its own part in tab A.
    assert.equal((await entryOf('f3 a in a',{tab:first,ref:ofA[0].string})).entry.tab,first);
    console.log('GROUP 14 READ two tabs of one page share no reference',ofA.length,ofB.length);
    // find and role, as group 16's row: one hit with its path.
    const hit=(await entryOf('f3 find',{tab:first,find:F3_UNIQUE,role:'link'})).entry.untrusted_content.outline;
    assert.ok(hit.includes('link "'+F3_UNIQUE+'"'),hit);assert.equal(hit.split('\n').filter(line=>line.includes('link "')).length,1);
  }));

  // Paging: F1 in full, by pages of two sizes, joins to the same text with
  // every paragraph whole and every field, and no fold.
  await check('READ BRIEF28 paging joins whole and a cursor keeps its query',closing(async()=>{
    const long=await open(fixtureUrl('f1'),'Paragraph 0');
    const wide=await pages('f1 full 40000',{tab:long,full:true,max:40000}),narrow=await pages('f1 full 10000',{tab:long,full:true,max:10000});
    assert.equal(narrow.text,wide.text,'pages of either size join to one text');
    assert.ok(wide.count>=2&&narrow.count>wide.count,wide.count+' and '+narrow.count+' pages');
    for(let index=0;index<120;index++)assert.ok(wide.text.includes('Paragraph '+index+' '),'paragraph '+index);
    for(let index=0;index<80;index++)assert.ok(wide.text.includes('"Synthetic value '+index+'"'),'field '+index);
    assert.doesNotMatch(wide.text,/… \d+ more|…\+\d+/,'full folds and cuts nothing');
    // A cursor used with another query is refused, as an input.
    const {entry:paged}=await entryOf('f1 page 1',{tab:long,full:true,max:10000});
    for(const other of [{},{find:'Paragraph'}]){
      const refused=await read('f1 cursor elsewhere',{tab:long,cursor:paged.cursor,...other});
      assert.equal(refused.ok,false,JSON.stringify(other));assert.equal(refused.error.code,'invalid_input',JSON.stringify(refused.error));
    }
    console.log('GROUP 14 READ paging',wide.count,narrow.count);
  }));

  // The state token, in Claude's own tab: typing a value moves it, so the
  // cursor taken before is stale, and until is met by the value alone.
  await check('READ BRIEF28 typing moves the state token and until meets a value',async()=>{
    await nav('efficiency-f1');
    const tab=getTab(),{entry:before}=await entryOf('f1 claude page 1',{tab,full:true,max:10000});
    assert.ok(before.cursor);
    const typed='Typed only as a value '+Date.now();
    const field=await target('Field 3');
    assert.equal((await call('fill_form',{fields:[{...field,text:typed}]})).remaining,0);
    const stale=await read('f1 cursor after typing',{tab,full:true,max:10000,cursor:before.cursor});
    assert.equal(stale.ok,true,JSON.stringify(stale.error));assert.equal(stale.data.reads[0].error?.code,'stale_reference','typing moved the token');
    const met=(await entryOf('f1 until a value',{tab,until:{text:typed},timeout_ms:3000})).entry;
    assert.equal(met.until_met,true,'until met by a field value');
  });

  // F6: frames from a second site and open and closed shadow roots are read,
  // and until is met inside a frame.
  await check('READ BRIEF28 frames of a second site and shadow roots are read',closing(async()=>{
    const framed=await open(fixtureUrl('f6'),'Top document text');
    const frames=(await entryOf('f6 until in a frame',{tab:framed,until:{text:'Nested frame text'},timeout_ms:6000})).entry;
    assert.equal(frames.until_met,true,'until met inside a nested frame');
    const whole=(await pages('f6 full',{tab:framed,full:true,max:40000})).text;
    for(const text of ['Top document text','Open root link','Open search','Closed root text','Closed root button','Nested root button',
      'Text of the second site','Second site link','Frame root button','Nested frame text','Nested frame button'])
      assert.ok(whole.includes(text),'F6 reads '+text);
  }));

  // Addresses: the marker is in no result of the new read; an ordinary query is shown.
  await check('READ BRIEF28 addresses hold no sign-in and show an ordinary query',closing(async()=>{
    const marked=await open(addressOf(),'Address fixture');
    const clean=(name,result)=>{const text=JSON.stringify(result);assert.ok(!text.includes(ADDRESS_MARK)&&!text.includes(ADDRESS_MARK.slice(0,12)),name+' holds the marker');};
    const {result:shown,entry:page}=await entryOf('address outline',{tab:marked});clean('outline',shown);
    for(const part of ['v=dQw4w9WgXcQ','q=red+shoes','page=2','code=…'])assert.ok(page.untrusted_content.url.includes(part),page.untrusted_content.url+' shows '+part);
    clean('full',await read('address full',{tab:marked,full:true,max:40000}));
    clean('find',await read('address find',{tab:marked,find:'link'}));
    const outline=page.untrusted_content.outline;
    for(const name of [...ADDRESS_LINKS.map(([name])=>'link "'+name+'"'),'form "Marker form"','frame']){
      const line=outline.split('\n').find(line=>line.trimStart().startsWith(name));assert.ok(line,name+' in '+outline);
      const reference=referencesOf(line)[0];assert.ok(reference,line);
      const detail=await read('address '+name,{tab:marked,ref:reference.string});clean(name,detail);
      if(name==='link "Video link"'){
        const text=detail.data.reads[0].untrusted_content.outline;
        for(const part of ['v=dQw4w9WgXcQ','q=red+shoes','page=2','sig=…'])assert.ok(text.includes(part),text+' shows '+part);
      }
    }
  }));
}
