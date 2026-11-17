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
import {F3_UNIQUE,ADDRESS_MARK,ADDRESS_LINKS,addressOf,HOSTILE,H1_NAME} from './efficiency-fixtures.mjs';
import {LONG_TEXT,LONG_VALUE,WIDE_CELL,BYTE_TEXT} from './outline-fixtures.mjs';
import {asciiBytes,stableReferences,completeEscapes,hostileGrammar,quoted,squeezed,visible} from './outline-checks.mjs';

const fixtureUrl=(name,query='')=>'http://fixture.test:8765/?case=efficiency-'+name+query;
// A reference ends its line: five consonants of this run, then its number.
const REFERENCES=/ ([bcdfghjklmnpqrstvwxyz]{5})(\d+)$/gm;
const referencesOf=outline=>[...String(outline).matchAll(REFERENCES)].map(match=>({string:match[1]+match[2],letters:match[1],number:Number(match[2])}));
const OUT='/out/outline-read';
const ENVELOPE_CASES=new Set(['READ BRIEF28 non ASCII and quote pages fit with a pending operation and the notice',
  'READ BRIEF28 five tabs each keep their byte share and continue with their own cursor']);

// These two fixtures need a fresh pending page. Execute them before the old
// crash fixtures leave unresolved operations, but report (and fail) them at
// the end of core so a new failure cannot hide brief 20's cases.
export function deferredOutlineCheck(report,{envelopeOnly=false,envelopeResults=null}={}){
  return (name,fn)=>{
    const envelope=ENVELOPE_CASES.has(name);
    if(envelopeOnly&&!envelope)return;
    if(!envelopeOnly&&envelope)return report(name,async()=>{
      const rows=envelopeResults?.filter(row=>row.name===name);
      assert.equal(rows?.length,1,name+': exactly one early execution is required');
      assert.equal(rows[0].passed,true,rows[0].error||name);
    });
    return report(name,fn);
  };
}

export async function outlineReadMatrix({check:report,call,rpc,nav,target,getTab,setTab,lifecycle,restoreControl,fixture,eventually,envelopeOnly=false,envelopeResults=null}){
  const check=deferredOutlineCheck(report,{envelopeOnly,envelopeResults});
  fs.mkdirSync(OUT,{recursive:true});
  const opened=[];
  let envelopeOperation=null;
  // A case that opens tabs closes them, also when it fails.
  const closing=fn=>async()=>{try{await fn();}finally{while(opened.length)await rpc('close_tab',{tab:opened.pop(),discard_unsaved:true});}};
  // One read through the service's socket; the whole result is kept beside its query.
  const read=async(name,args)=>{
    const result=await rpc('outline',args);
    fs.appendFileSync(OUT+'/calls.jsonl',JSON.stringify({name,args,wire_bytes:result.wireBytes,result})+'\n');
    assert.ok(Number.isSafeInteger(result.wireBytes)&&result.wireBytes<=48*1024,name+': the exact service JSON envelope fits');
    assert.ok(!result.bounds,name+': the base did not shorten the result');
    if(envelopeOperation&&result.ok){
      assert.ok(result.data.version_notice&&result.pending.chrome_version_notice,name+': both notices are measured');
      assert.ok(result.pending.items.some(row=>row.operation_id===envelopeOperation&&row.state==='reserved'),name+': the live reserved operation is in the measured envelope');
    }
    return result;
  };
  const entryOf=async(name,args)=>{
    const result=await read(name,args);assert.equal(result.ok,true,name+': '+JSON.stringify(result.error));
    const entry=result.data.reads[0];assert.ok(entry&&!entry.error,name+': '+JSON.stringify(entry?.error));
    return {result,entry};
  };
  // Every page of one query, joined; each page holds at least one character.
  const pages=async(name,args)=>{
    let cursor,text='',count=0,total;const entries=[];
    do{
      const {entry}=await entryOf(name,{...args,...(cursor?{cursor}:{})});
      if(total===undefined)total=entry.total;else assert.equal(entry.total,total,name+': total is stable');
      assert.equal(Array.from(entry.untrusted_content.outline).length,entry.characters);
      assert.ok(entry.characters<=(args.max||6000));completeEscapes(entry.untrusted_content.outline);
      assert.ok(entry.untrusted_content.outline.length>0||entry.total===0,name+': a page advances');
      text+=entry.untrusted_content.outline;cursor=entry.cursor;count++;entries.push(entry);
      assert.ok(count<2000,name+': paging ends');
    }while(cursor);
    fs.writeFileSync(OUT+'/'+name+'.txt',text);
    assert.equal(Array.from(text).length,total,name+': joined pages hold the whole query');
    return {text,count,entries};
  };
  const open=async(url,text)=>{
    const tab=(await call('open',{url})).untrusted_content.tab;opened.push(tab);
    const {entry}=await entryOf('open '+text,{tab,until:{text},timeout_ms:6000});
    assert.equal(entry.until_met,true,'loaded: '+text);
    return tab;
  };
  const issued=async name=>{
    const {entry}=await entryOf(name,{tab:getTab(),full:true,max:40000});
    const refs=referencesOf(entry.untrusted_content.outline);
    assert.ok(refs.length>=2,name+': the list and next-page link have references');
    return refs;
  };
  const disjoint=(old,fresh,name)=>{
    assert.ok(old.length&&fresh.length,name+': both reads issued references');
    const strings=new Set(old.map(ref=>ref.string));
    assert.deepEqual(fresh.filter(ref=>strings.has(ref.string)),[],name+': no old string is issued again');
  };
  const refused=async(name,tab,refs)=>{
    for(const ref of refs){
      const result=await read(name,{tab,ref:ref.string});
      assert.equal(result.ok,true,JSON.stringify(result.error));
      assert.equal(result.data.reads[0].error?.code,'stale_reference',name+': '+ref.string);
    }
  };
  // restoreControl takes the driver's owner-opened page. Navigate with the
  // tool afterwards; a guarded reload of an owner page with frames can refuse.
  const restored=async()=>{setTab(await restoreControl());await nav('efficiency-f7&page=1');};
  const refAt=(text,start)=>{const line=text.split('\n').find(line=>line.trimStart().startsWith(start));assert.ok(line,start);const ref=referencesOf(line)[0]?.string;assert.ok(ref,line);return ref;};
  // Existing root-only CI hook: a real bridge command, never a second tool.
  const bridge=async(command,args)=>{
    await lifecycle({fixture:'hold',command,arguments:args});
    const result=JSON.parse(fs.readFileSync('/out/fixture-hold.json','utf8'));
    fs.appendFileSync(OUT+'/bridge.jsonl',JSON.stringify({command,args,result})+'\n');return result;
  };

  // First, while GROUP 9's last service restart has left a small counter.
  // The extra tab advances the new counter without changing the old page.
  await check('READ BRIEF28 a service restart refuses old references after the new counter passes them',closing(async()=>{
    await nav('efficiency-f7&page=1');const old=await issued('service before');
    await lifecycle({fixture:'kill_service'});await lifecycle({fixture:'start_service'});await restored();
    const fresh=await issued('service after'),advance=await open(fixtureUrl('f3'),'Results');
    const further=referencesOf((await pages('service counter advanced',{tab:advance,full:true,max:40000})).text);
    assert.ok(further.length>=300,'the restarted service issues references for the other tab');
    assert.ok(Math.max(...further.map(ref=>ref.number))>Math.max(...old.map(ref=>ref.number)),'the new counter has passed every old number');
    disjoint(old,[...fresh,...further],'service restart');
    await refused('service old refused',getTab(),old);
  }));

  await check('READ BRIEF28 Chrome restart and extension reconnect each refuse every old reference without reissuing strings',async()=>{
    for(const component of ['chrome','host']){
      await nav('efficiency-f7&page=1');const old=await issued(component+' before');
      const session=(await call('tabs')).session;
      await lifecycle('kill_'+component);if(component==='chrome')await lifecycle('start_chrome');
      await restored();const fresh=await issued(component+' after');
      // The hello session names the extension worker. Killing only its host
      // cuts the connection while the worker (and that session) survives.
      const current=(await call('tabs')).session;
      if(component==='chrome')assert.notEqual(current,session,'Chrome restarted its extension worker');
      else assert.equal(current,session,'only the native connection was cut');
      assert.equal(fresh[0].letters,old[0].letters,component+': the service did not restart');
      assert.ok(Math.min(...fresh.map(ref=>ref.number))>Math.max(...old.map(ref=>ref.number)),component+': the counter goes on');
      disjoint(old,fresh,component);await refused(component+' old refused',getTab(),old);
    }
  });

  await check('READ BRIEF28 more than 5000 elements drop an old reference and never issue its string again',closing(async()=>{
    const tab=await open(fixtureUrl('h1','&mode=many'),'Many elements');
    const {entry:initial}=await entryOf('many first element',{tab,find:'Element 0',role:'button'});
    const [first]=referencesOf(initial.untrusted_content.outline);assert.ok(first,'the first element has a reference');
    await entryOf('many first reference live',{tab,ref:first.string});
    let cursor,seen=new Set();
    // Stop as soon as returned pages exceed the table's bound. Continuing
    // that cursor can itself refuse after eviction (the documented limit).
    for(let page=0;page<10&&seen.size<=5000;page++){
      const {entry}=await entryOf('many page '+page,{tab,full:true,max:40000,...(cursor?{cursor}:{})});
      const refs=referencesOf(entry.untrusted_content.outline);
      assert.ok(refs.length,'the page returns references');
      if(page===0){
        const line=entry.untrusted_content.outline.split('\n').find(line=>line.startsWith('button "Element 0" '));
        assert.ok(line,'the first element is on the first page');assert.equal(referencesOf(line)[0]?.string,first.string);
      }
      for(const ref of refs)seen.add(ref.string);
      cursor=entry.cursor;assert.ok(cursor,'more of the 100000 elements remain');
    }
    assert.ok(seen.size>5000,'more than 5000 different references were returned: '+seen.size);
    await refused('many dropped reference',tab,[first]);
    const {entry}=await entryOf('many first element again',{tab,find:'Element 0',role:'button'});
    const fresh=referencesOf(entry.untrusted_content.outline);
    assert.equal(fresh.length,1,'find reads the same first element');
    assert.match(entry.untrusted_content.outline,/button "Element 0" /);
    disjoint([first],fresh,'dropped element read again');
    await entryOf('many replacement live',{tab,ref:fresh[0].string});
    await refused('many old still refused',tab,[first]);
  }));

  await check('READ BRIEF28 release and retake refuse an old reference with the same document and element id',async()=>{
    await nav('efficiency-f7&page=1');const before=await target('Next page'),old=await issued('retake before');
    await call('release_tab',{tab:getTab()});await call('take_tab',{tab:getTab()});
    const after=await target('Next page'),fresh=await issued('retake after');
    assert.equal(after.reference.document,before.reference.document,'no reload between release and retake');
    assert.equal(after.reference.element,before.reference.element,'the reader reused the same element id');
    disjoint(old,fresh,'retake');await refused('retake old refused',getTab(),old);
  });
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

  await check('READ BRIEF28 100000 characters by ref advance at max 1000 without splitting escapes',closing(async()=>{
    const tab=await open('http://fixture.test:8765/?case=outline-paging','Paging fixture');
    const first=(await entryOf('long text outline',{tab})).entry;
    const ref=refAt(first.untrusted_content.outline,'p '),whole=await pages('100000 by ref',{tab,ref,max:1000});
    assert.equal(whole.text,'p '+quoted(LONG_TEXT)+' '+ref);
    assert.ok(whole.count>100);assert.ok(whole.entries.slice(0,-1).every(entry=>entry.mid_line));
    assert.equal(whole.entries.at(-1).mid_line,false);
    const cursor=whole.entries[0].cursor;
    for(const other of [{ref:refAt(first.untrusted_content.outline,'button "Other"')},{ref,find:'012'},{ref,full:true}]){
      const result=await read('long cursor wrong query',{tab,cursor,max:1000,...other});
      assert.equal(result.ok,false);assert.equal(result.error.code,'invalid_input');
    }
  }));

  await check('READ BRIEF28 a wide table row is returned whole across pages',closing(async()=>{
    const tab=await open('http://fixture.test:8765/?case=outline-paging&mode=row','Paging fixture');
    const ref=refAt((await entryOf('wide table outline',{tab})).entry.untrusted_content.outline,'table ');
    const whole=await pages('wide row',{tab,ref,max:1000});
    assert.equal(whole.text,'table "Wide" '+ref+'\ncolumns: "A" | "B"\n'+quoted(WIDE_CELL)+' | '+quoted(WIDE_CELL));
    assert.ok(whole.entries.some(entry=>entry.mid_line));assert.ok(whole.count>6);
  }));

  await check('READ BRIEF28 a 20000 character value is returned in full across pages',closing(async()=>{
    assert.equal(LONG_VALUE.length,20000);
    const tab=await open('http://fixture.test:8765/?case=outline-paging&mode=value','Paging fixture');
    const ref=refAt((await entryOf('long value outline',{tab})).entry.untrusted_content.outline,'textbox ');
    const whole=await pages('20000 value',{tab,ref,full:true,max:1000});
    assert.equal(whole.text,'textbox "Long value" = '+quoted(LONG_VALUE)+' '+ref);
    assert.ok(whole.entries.slice(0,-1).every(entry=>entry.mid_line));
  }));

  const byteExpected=mode=>'h1 "Paging fixture"\n'+Array.from({length:Math.ceil(BYTE_TEXT[mode].length/180)},(_,i)=>'p '+quoted(BYTE_TEXT[mode].slice(i*180,(i+1)*180))+'\nseparator').join('\n');
  await check('READ BRIEF28 non ASCII and quote pages fit with a pending operation and the notice',closing(async()=>{
    await nav('compose&id=outline-envelope');const reserved=(await call('click',await target('Send'))).approval;assert.ok(reserved);
    try{
      await lifecycle({fixture:'qualification',mode:'conservative'});
      assert.equal((await call('operation_status',{operation_id:reserved.operation_id})).operation.state,'reserved');
      envelopeOperation=reserved.operation_id;
      for(const mode of Object.keys(BYTE_TEXT)){
        const tab=await open('http://fixture.test:8765/?case=outline-paging&mode='+mode,'Paging fixture');
        const result=await read('byte envelope '+mode,{tab,full:true,max:40000});
        assert.equal(result.ok,true);assert.ok(result.data.version_notice);assert.ok(result.pending.chrome_version_notice);
        assert.ok(result.pending.items.some(row=>row.operation_id===reserved.operation_id&&row.state==='reserved'),'the live reserved operation is in the measured envelope');
        const whole=await pages('byte pages '+mode,{tab,full:true,max:40000});
        assert.equal(whole.text,byteExpected(mode));assert.ok(whole.count>1);
      }
    }finally{envelopeOperation=null;await lifecycle({fixture:'qualification',mode:'qualified'});await call('drop',{operation_id:reserved.operation_id});await call('notice_ack',{operation_id:reserved.operation_id});}
  }));

  await check('READ BRIEF28 five tabs each keep their byte share and continue with their own cursor',closing(async()=>{
    const modes=['unicode','quotes','unicode','quotes','unicode'],tabs=[];
    for(const mode of modes)tabs.push(await open('http://fixture.test:8765/?case=outline-paging&mode='+mode,'Paging fixture'));
    await nav('compose&id=outline-five');const reserved=(await call('click',await target('Send'))).approval;assert.ok(reserved);
    try{
      await lifecycle({fixture:'qualification',mode:'conservative'});
      assert.equal((await call('operation_status',{operation_id:reserved.operation_id})).operation.state,'reserved');
      envelopeOperation=reserved.operation_id;
      const result=await read('five byte shares',{tabs,max:40000});assert.equal(result.ok,true);assert.ok(result.data.version_notice);
      assert.ok(result.pending.items.some(row=>row.operation_id===reserved.operation_id&&row.state==='reserved'));
      assert.deepEqual(result.data.reads.map(entry=>entry.tab),tabs);
      const sizes=[];
      for(const [index,entry]of result.data.reads.entries()){
        assert.ok(!entry.error&&entry.cursor);assert.ok(entry.characters>0&&entry.characters<=40000);
        // With no spare-byte transfer, an entry's outline cannot consume a
        // fifth of even the full envelope (fixed fields take space too).
        sizes.push(asciiBytes(entry.untrusted_content.outline));assert.ok(sizes.at(-1)<48*1024/5);
        let text=entry.untrusted_content.outline,cursor=entry.cursor;
        while(cursor){const next=(await entryOf('five continue '+index,{tab:entry.tab,max:40000,cursor})).entry;text+=next.untrusted_content.outline;cursor=next.cursor;}
        assert.equal(text,byteExpected(modes[index]));
      }
      assert.ok(Math.max(...sizes)-Math.min(...sizes)<1200,'all five used an equal byte share');
    }finally{envelopeOperation=null;await lifecycle({fixture:'qualification',mode:'qualified'});await call('drop',{operation_id:reserved.operation_id});await call('notice_ack',{operation_id:reserved.operation_id});}
  }));

  await check('READ BRIEF28 a change inside a frame moves the state token',closing(async()=>{
    const tab=await open('http://fixture.test:8765/?case=outline-state&id=outline-state','Frame before');
    const before=await bridge('page_state',{tab});
    await fixture.mutate('outline-state-child','review-change');
    const after=await bridge('page_state',{tab});assert.notEqual(after.token,before.token);assert.equal(after.document,before.document);
    assert.equal((await entryOf('frame changed',{tab,until:{text:'Frame after'}})).entry.until_met,true);
  }));

  await check('READ BRIEF28 an unchanged page keeps its state token over 100 polls',closing(async()=>{
    const tab=await open(fixtureUrl('f7','&page=1'),'Results page 1'),before=await bridge('page_state',{tab});assert.ok(before.token);
    for(let poll=0;poll<100;poll++)assert.equal((await bridge('page_state',{tab})).token,before.token,'poll '+poll);
  }));

  await check('READ BRIEF28 until meets text on a page that never goes quiet',closing(async()=>{
    const tab=await open('http://fixture.test:8765/?case=outline-state&mode=busy&id=outline-busy','Busy fixture');
    await fixture.mutate('outline-busy','review-change');const before=await bridge('page_state',{tab});
    const {entry}=await entryOf('until never quiet',{tab,until:{text:'Busy answer arrived'},timeout_ms:6000});assert.equal(entry.until_met,true);
    const after=await bridge('page_state',{tab});assert.notEqual(after.token,before.token);
    await new Promise(resolve=>setTimeout(resolve,200));assert.notEqual((await bridge('page_state',{tab})).token,after.token,'still changing after the successful wait');
  }));

  await check('READ BRIEF28 H1 hostile roles stay on the fixed role list',closing(async()=>{
    const tab=await open(fixtureUrl('h1'),'Hostile text'),text=(await pages('H1 roles',{tab,full:true,max:40000})).text;
    hostileGrammar(text);
    for(const index of [0,3])assert.ok(text.includes('button "Role '+index+'"'),'allowed role '+index);
    for(const index of [1,2])assert.ok(text.includes('text "Text '+index+'"'),'tag fallback '+index);
    assert.ok(!text.includes('b'.repeat(10000)));assert.ok(!text.includes('Pay now'));
    for(let index=0;index<4;index++)assert.ok(text.includes('button "Real '+index+'"'));
  }));

  await check('READ BRIEF28 H1 names values options tables forms paths stale lines titles and dialogs stay quoted',closing(async()=>{
    for(const [index,hostile]of HOSTILE.entries()){
      const tab=await open(fixtureUrl('h1','&mode=surfaces&title='+index+'&id=hostile-'+index),'Hostile surfaces');
      const first=(await entryOf('hostile outline '+index,{tab,max:40000})).entry,text=first.untrusted_content.outline,safe=quoted(squeezed(hostile));
      hostileGrammar(text);assert.ok(text.includes((index===12?'password ':'button ')+safe));
      const nativeTitle=(await bridge('tab_context',{tab})).title;
      assert.equal(first.untrusted_content.title,visible(nativeTitle),'escape the title Chrome actually reports');
      const form=refAt(text,'form "Hostile form"'),table=refAt(text,'table "Hostile table"'),list=refAt(text,'list "Hostile list"'),link=refAt(text,'link "Detail link"');
      for(const [kind,ref]of [['form',form],['table',table],['list',list],['link',link]]){
        const detail=(await pages('hostile '+kind+' '+index,{tab,ref,max:40000})).text;hostileGrammar(detail);
        if(kind==='form'){
          assert.ok(detail.includes(' = '+quoted(hostile.replace(/\r\n?/g,'\n'))),'value '+index);
          assert.ok(detail.includes('option '+safe),'option '+index);assert.ok(detail.includes('error: '+safe),'error '+index);assert.ok(detail.includes('hidden: '+quoted(hostile)),'hidden '+index);
        }else if(kind==='table'){assert.ok(detail.includes('columns: '+safe+' | "Plain header"'));assert.ok(detail.includes('"Plain cell" | '+safe));}
        else if(kind==='list')assert.ok(detail.includes('listitem '+safe));
        else assert.ok(detail.includes('title: '+safe));
      }
      const found=(await pages('hostile find '+index,{tab,find:'Path target',max:40000})).text;hostileGrammar(found);
      // The accepted renderer caps each ancestor name at 24 characters and
      // the whole path at 80. The cut still goes through quoted().
      const name=Array.from(squeezed(hostile)),path='region '+quoted(name.slice(0,24).join(''))+(name.length>24?'…':'');
      assert.ok(found.endsWith(' · in '+(Array.from(path).length>80?'…':path)),found);
      const fold=refAt(text,'… 5 more');await fixture.mutate('hostile-'+index,'review-change');
      const stale=await read('hostile stale '+index,{tab,ref:fold});assert.equal(stale.ok,true);
      const failed=stale.data.reads[0];assert.equal(failed.error.code,'stale_reference');
      assert.equal(failed.error.message,"This reference isn't valid for this tab any more; read the page again.");
      assert.ok(failed.untrusted_content.line.startsWith('button '+safe));hostileGrammar(failed.untrusted_content.line);
      // Native dialogs and tab titles are JSON string fields in the same
      // untrusted envelope; their contents cannot create outline lines.
      const driver=getTab();let openedDialog;
      try{setTab(tab);await call('click',await target('Open dialog'));openedDialog=await bridge('dialog_facts',{tab});}finally{setTab(driver);}
      assert.ok(openedDialog.dialog);
      const dialog=(await entryOf('hostile dialog '+index,{tab})).entry;
      assert.equal(dialog.untrusted_content.outline,'');assert.equal(dialog.untrusted_content.dialog.text,visible(openedDialog.dialog.text));
      const answered=await call('dialog',{tab,expected:openedDialog.dialog,accept:true});
      if(answered.approval)assert.equal((await call('submit',answered.approval)).operation.state,'done');
      assert.equal((await bridge('page_state',{tab})).dialog,false,'the synthetic dialog was answered before close');
      await call('close_tab',{tab,discard_unsaved:true});opened.splice(opened.indexOf(tab),1);
    }
  }));

  await check('READ BRIEF28 H1 a 100000 character name is cut once and read whole by ref',closing(async()=>{
    const tab=await open(fixtureUrl('h1','&mode=name'),'Long name'),first=(await entryOf('H1 long name outline',{tab})).entry;
    assert.match(first.untrusted_content.outline,/…\+99,800 /);
    const ref=refAt(first.untrusted_content.outline,'button '),whole=await pages('H1 long name',{tab,ref,max:1000});
    assert.equal(whole.text,'button '+quoted(H1_NAME)+' '+ref);assert.ok(whole.count>=100);
  }));

  await check('READ BRIEF28 H1 100000 elements report the 20000 node cap',closing(async()=>{
    const tab=await open(fixtureUrl('h1','&mode=many'),'Many elements'),reply=await bridge('outline',{tab});
    assert.equal(reply.frames.reduce((sum,frame)=>sum+frame.nodes.length,0),20000);
    assert.equal(reply.frames.reduce((sum,frame)=>sum+frame.omitted,0),80001);
  }));

  await check('READ BRIEF28 small fixture outlines match the stored green browser results character for character',closing(async()=>{
    for(const [name,url,loaded]of [['f1',fixtureUrl('f1'),'Paragraph 0'],['f3',fixtureUrl('f3'),'Results'],['f7',fixtureUrl('f7','&page=1'),'Results page 1'],['f6',fixtureUrl('f6'),'Nested frame text'],['address',addressOf(),'Address frame text']]){
      const tab=await open(url,loaded),text=(await pages('expected '+name,{tab,max:40000})).text;
      assert.equal(stableReferences(text),fs.readFileSync(new URL('./outline-expected/'+name+'.txt',import.meta.url),'utf8'),name);
    }
  }));
}
