// Brief 28, group 14's password cases ("Passwords, in group 14 and in
// password_exclusion"), in the named inventory (verdicts.mjs): two cases in
// group 7 (password_exclusion) and the refused forms in group 3 (binding).
// Each reads through brief 20's tools and through the internal action
// chrome_outline (the test-only switch, run.sh). The fixtures are
// unread-fixtures.mjs; the recording is group 7's (password-ingress.js).
// They run last in the core shard: the final step leaves a page submission
// stopped in its document, which no later case may meet.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {setTimeout as delay} from 'node:timers/promises';
import {completeIngress} from './ingress-scan.mjs';
import {PASSWORD,PROBE,PLAIN_KINDS,PLAIN_ROOTS,NAMED,TYPED_KINDS,TYPED_AREA,DRAFT_AREA,OPTION,LIMIT,LATE_DRAFT} from './unread-fixtures.mjs';

const SECRET=new RegExp(PASSWORD);
const address=(mode,id,variant='')=>'password-unread&mode='+mode+'&id='+id+(variant?'&variant='+variant:'');
// A reference ends its line: five consonants of this run, then its number.
const REFERENCE=/ ([bcdfghjklmnpqrstvwxyz]{5}\d+)$/;
const count=(text,part)=>text.split(part).length-1;
// Brief 20's rows of the fields with this name: a field row says what its value is, or that it isn't read.
const fields=(rows,label)=>rows.filter(row=>row.expected.name===label&&['value','value_status','password'].some(key=>key in row.expected));
const unread=(row,label)=>{assert.equal(row.expected.value,undefined,label);assert.equal(row.expected.value_status,'filled',label);assert.equal(row.expected.password,undefined,label);};
const WITHHELD=/This form holds unread typed text; send it yourself/;

export async function unreadMatrix({check,call,rpc,read,nav,target,counts,approval,fixture,eventually,ownerNavigate,ownerKey,ownerType,getTab}){
  const evidence=[];
  const clean=(name,value)=>{const text=JSON.stringify(value??null);assert.doesNotMatch(text,SECRET,name+' holds the password');return text;};
  // One call of the new read. The whole result is checked for the password before anything else is looked at.
  const outline=async(name,args)=>{const result=await rpc('outline',args);clean(name,result);assert.equal(result.ok,true,name+': '+JSON.stringify(result.error));return result.data.reads;};
  const entryOf=async(name,args)=>{const entry=(await outline(name,args))[0];assert.ok(entry&&!entry.error,name+': '+JSON.stringify(entry?.error));return entry;};
  const full=async(name,tab)=>{
    let cursor,text='';
    do{const entry=await entryOf(name,{tab,full:true,max:40000,...(cursor?{cursor}:{})});text+=entry.untrusted_content.outline;cursor=entry.cursor;}while(cursor);
    return text;
  };
  // Every surface, on the driver's tab: the outline, the whole page, a form by
  // ref, find and until for the password itself, several tabs; and of brief
  // 20's tools a read and a find. No argument names the whole password, so a
  // request can't put it into a log either.
  const surfaces=async(name,tab,others=[])=>{
    const first=await entryOf(name+': outline',{tab}),whole=await full(name+': full',tab);
    const forms=whole.split('\n').filter(line=>line.trimStart().startsWith('form')).map(line=>line.match(REFERENCE)?.[1]).filter(Boolean);
    for(const ref of forms.slice(0,4))await entryOf(name+': a form by ref',{tab,ref,max:40000});
    for(const find of ['PRIVATE_PASSWORD','SENTINEL'])await outline(name+': find',{tab,find});
    const waited=await entryOf(name+': until',{tab,until:{text:'PRIVATE_PASSWORD_20'},timeout_ms:1000});
    assert.equal(waited.until_met,false,name+': a password value never meets until');
    if(others.length)assert.equal((await outline(name+': several tabs',{tabs:[tab,...others]})).length,others.length+1);
    const rows=await read();clean(name+': chrome_read',rows);
    clean(name+': chrome_find',await call('find',{tab,text:'PRIVATE_PASSWORD'}));
    return {first,whole,rows,forms:forms.length};
  };
  // Group 7's recording: what the content script's own reads returned, every
  // reply and event the extension handled, every tool result and the
  // service's log. `marker` is a public value of the case's pages, so the
  // recording is known to have covered them.
  const recording=(name,marker)=>{
    const ingress=completeIngress(fs.readFileSync('/out/browser-boundary.jsonl','utf8'));let covered=false;
    for(const row of ingress){
      const text=JSON.stringify(row);assert.doesNotMatch(text,SECRET,name+': browser-boundary.jsonl');
      covered||=row?.reader_ingress!==undefined&&text.includes(marker);
    }
    assert.ok(covered,name+': the recording holds the content script\'s read of '+marker);
    for(const file of ['tool.jsonl','service.txt'])assert.doesNotMatch(fs.readFileSync('/out/'+file,'utf8'),SECRET,name+': '+file);
  };
  // No reserved operation of this page waits for an approval.
  const waitingFor=async id=>{
    let cursor;
    do{
      const current=await call('control_pending',{limit:10,...(cursor?{cursor}:{})});
      for(const row of current.items){
        if(row.app!=='chrome'||row.state!=='reserved')continue;
        const status=await call('operation_status',{operation_id:row.operation_id});
        if(JSON.stringify(status.operation.approval?.description??null).includes(id))return row.operation_id;
      }
      cursor=current.cursor;
    }while(cursor);
  };
  // The late root, in a document watched from its start. The owner's own
  // navigation first puts the keyboard into this tab's page; the tool's
  // navigation then loads the watched document. The component attaches its
  // root at the first change, and the owner types each text with real keys,
  // Enter after each. Nothing reads the tab between the attachment and the
  // end of the typing, so the read that follows is the reader's first
  // meeting with the root.
  const lateRoot=async(id,variant,typed)=>{
    await call('release_tab',{tab:getTab()});await ownerNavigate('http://fixture.test:8765/?case=compose&id='+id);await call('take_tab',{tab:getTab()});
    await nav(address('late',id,variant));
    const before=await read();clean('before the root: chrome_read',before);
    await fixture.mutate(id,'review-change');
    await eventually(()=>fixture.compatibility.some(row=>row.id===id&&row.phase==='late-ready'),'the component attached its root: '+id);
    for(const text of typed){ownerType(text);ownerKey(true);}
    if(typed.length){
      const done=await eventually(()=>fixture.compatibility.find(row=>row.id===id&&row.phase==='late-typed'),'the owner typed into the late root: '+id);
      assert.equal(done.filled,typed.length,'every typed field holds text');assert.equal(done.trusted,true,'typed with real keys');
      // Past the hold's window, so the owner's Enter exempts nothing that follows.
      await delay(700);
    }
    return before;
  };

  await check('GROUP 7 BRIEF28 fields made plain before the reader came stay unread in every root and frame',async()=>{
    const id='brief28-plain',url=key=>'http://fixture.test:8765/?case='+address('plain',key),made=PLAIN_KINDS*PLAIN_ROOTS*2;
    const ready=(key,times)=>eventually(()=>['top','child'].every(frame=>fixture.compatibility.filter(row=>row.id===key&&row.phase==='plain-ready'&&row.frame===frame).length>=times),'the plain page finished: '+key);
    // A taken tab before its reload: the owner opened the page, and its fields were plain before any reader came.
    await call('release_tab',{tab:getTab()});await ownerNavigate(url(id));await ready(id,1);await call('take_tab',{tab:getTab()});
    const tab=getTab();
    // A tab of Claude's own shows the same page, watched from its start.
    const watchedTab=(await call('open',{url:url(id+'-watched')})).untrusted_content.tab;
    try{
      await ready(id+'-watched',1);
      const taken=await surfaces('taken tab',tab,[watchedTab]);
      assert.ok(taken.forms>=4,'forms read by ref: '+taken.forms);
      // The new read. Each field made plain, in the page, both roots and the second site's frame, shows only that it is filled.
      assert.equal(count(taken.whole,'"Code" (filled, not read)'),made,'every field made plain is filled, not read');
      assert.equal(count(taken.whole,'"Code"'),made,'and nothing else is named Code');
      // The name rule and a present mask win in a document that wasn't watched too: a password line, whatever the element.
      for(const label of NAMED)assert.ok(taken.whole.includes('password "'+label+'" (not read)'),'named like a credential, or masked now: '+label);
      // What such a document shows: a typed kind only as filled or empty.
      for(const type of Object.keys(TYPED_KINDS))assert.equal(count(taken.whole,'"Kind '+type+'" (filled, not read)'),1,'a typed field of kind '+type);
      assert.equal(count(taken.whole,'"Kind textarea" (filled, not read)'),1,'a textarea');
      for(const label of ['Kind empty','Kind empty area'])assert.equal(count(taken.whole,'"'+label+'" (empty)'),1,label);
      // A kind whose value isn't typed text keeps it, and an editable area's draft is read whole.
      for(const kept of ['"Kind date" = "2026-11-16"','checkbox "Kind box" checked','radio "Kind radio" checked','"Kind range" = "42"','"Kind colour" = "#112233"',OPTION,DRAFT_AREA])
        assert.ok(taken.whole.includes(kept),'kept as it is: '+kept);
      // The limit, shown honestly: the editable area unmasked before the reader came is read; the textarea with the same history is not.
      assert.ok(taken.whole.includes(LIMIT),'the known limit: an unmasked editable area labelled "Value" is read');
      assert.equal(count(taken.whole,'"Value" (filled, not read)'),1,'a textarea unmasked before the reader came stays unread');
      // Brief 20's read of the same tab.
      const codes=fields(taken.rows,'Code');assert.equal(codes.length,made,'chrome_read rows named Code: '+codes.length);
      for(const row of codes)unread(row,'Code');
      for(const label of NAMED)for(const row of fields(taken.rows,label)){assert.equal(row.expected.password,true,label);assert.equal(row.expected.value,undefined,label);}
      for(const label of ['Verification code','Stored','Recovery phrase','Private key','Box'])assert.ok(fields(taken.rows,label).length>=1,'chrome_read shows the field '+label);
      for(const type of Object.keys(TYPED_KINDS)){const row=fields(taken.rows,'Kind '+type)[0];assert.ok(row,type);unread(row,'Kind '+type);}
      assert.equal(fields(taken.rows,'Kind empty')[0]?.expected.value_status,'empty');
      assert.equal(fields(taken.rows,'Draft area')[0]?.expected.value,DRAFT_AREA);
      const values=fields(taken.rows,'Value');assert.equal(values.length,2,'the two fields labelled Value');
      assert.ok(values.some(row=>row.expected.value===LIMIT)&&values.some(row=>row.expected.value===undefined&&row.expected.value_status==='filled'),JSON.stringify(values.map(row=>row.expected)));
      const form=await call('read_form',{tab,reference:codes[0].reference});clean('taken tab: chrome_read_form',form);
      // No typed value of the unwatched document is in anything either read returned.
      const returned=JSON.stringify([taken.first,taken.whole,taken.rows,form]);
      for(const value of [...Object.values(TYPED_KINDS),TYPED_AREA])assert.ok(!returned.includes(value),'a typed value of an unwatched document was returned: '+value);
      // Claude's own tab watched the fields from the start: none shows a value, the named ones are password lines, a plain field is read.
      const watched=await full('watched tab: full',watchedTab);
      assert.equal(count(watched,'"Code"'),made);
      assert.equal(count(watched,'password "Code" (not read)')+count(watched,'"Code" (filled, not read)'),made,'a watched document shows no value of a field that was a password field');
      for(const label of NAMED)assert.ok(watched.includes('password "'+label+'" (not read)'),'watched: '+label);
      assert.ok(watched.includes('"Kind text" = "'+TYPED_KINDS.text+'"'),'a plain field of a watched document is read');
      // After the taken tab's reload a plain, unnamed text field of that page is read, and the named ones still aren't.
      await call('navigate',{tab,direction:'reload',discard_unsaved:true});await ready(id,2);
      const after=await surfaces('reloaded tab',tab);
      assert.ok(after.whole.includes('"Kind text" = "'+TYPED_KINDS.text+'"'),'after the reload a plain text field is read');
      assert.equal(fields(after.rows,'Kind text')[0]?.expected.value,TYPED_KINDS.text);
      for(const label of NAMED)assert.ok(after.whole.includes('password "'+label+'" (not read)'),'after the reload: '+label);
      assert.equal(count(after.whole,'"Code"'),made);
      assert.equal(count(after.whole,'password "Code" (not read)')+count(after.whole,'"Code" (filled, not read)'),made,'after the reload no field made plain shows a value');
      for(const row of fields(after.rows,'Code'))assert.equal(row.expected.value,undefined);
      recording('fields made plain',DRAFT_AREA);
      // The mutation check, in the browser. The same nine fields in three roots, holding a probe value in place of
      // the password, again in a taken tab before its reload: with the history rule as built every one is filled,
      // not read; with the rule switched off for that page in the test build (prepare.mjs) every one shows the
      // value. So the rule is what keeps them out, and the counts above would have moved without it.
      const probed={};
      for(const rule of ['kept','off']){
        const key=id+'-probe-'+rule;
        await call('release_tab',{tab});await ownerNavigate(url(key)+'&probe=1'+(rule==='off'?'&unprotect=history':''));
        await eventually(()=>fixture.compatibility.some(row=>row.id===key&&row.phase==='plain-ready'&&row.frame==='top'),'the probe page finished: '+key);
        await call('take_tab',{tab});
        probed[rule]=await full('probe page, rule '+rule,tab);assert.equal(count(probed[rule],'"Code"'),PLAIN_KINDS*PLAIN_ROOTS,rule);
      }
      assert.equal(count(probed.kept,'"Code" (filled, not read)'),PLAIN_KINDS*PLAIN_ROOTS,'the history rule keeps the probe value out');assert.ok(!probed.kept.includes(PROBE));
      assert.equal(count(probed.off,'"Code" = "'+PROBE+'"'),PLAIN_KINDS*PLAIN_ROOTS,'without the history rule every field made plain shows its value');
      assert.equal(count(probed.off,'(filled, not read)'),0);
      evidence.push({case:'plain',made,forms:taken.forms,taken:taken.first.untrusted_content.outline.split('\n').slice(0,40),watched:watched.split('\n').length});
    }finally{await rpc('close_tab',{tab:watchedTab,discard_unsaved:true});}
  });

  await check('GROUP 7 BRIEF28 a shadow root met late and the name rule keep secrets unread in a watched document',async()=>{
    const id='brief28-late';
    // The owner types the password into the field labelled "Password", into the one labelled "Code" and into the textarea; Enter makes each plain.
    const before=await lateRoot(id,'password',[PASSWORD,PASSWORD,PASSWORD]);
    // The name rule in a watched document, before the root exists: the sign-in code known by its name, the named textareas, the mask.
    for(const label of NAMED)for(const row of fields(before,label)){assert.equal(row.expected.password,true,label);assert.equal(row.expected.value,undefined,label);}
    for(const label of ['Verification code','Stored','Recovery phrase','Private key','Box'])assert.ok(fields(before,label).length>=1,'chrome_read shows the field '+label);
    const tab=getTab(),met=await surfaces('late root',tab);
    assert.equal(count(met.whole,'password "Password" (not read)'),2,'kept out by its name: the editable area of the page and the late root\'s field');
    assert.equal(count(met.whole,'"Code" (filled, not read)'),1,'kept out because it held text when the reader first met its root');
    assert.equal(count(met.whole,'"Code"'),1);
    assert.equal(count(met.whole,'"Notes" (filled, not read)'),1,'a textarea that held text at the first meeting');
    for(const label of NAMED)assert.ok(met.whole.includes('password "'+label+'" (not read)'),'watched: '+label);
    const comment=met.whole.split('\n').find(line=>line.includes('"Comment"'));
    assert.ok(comment&&!comment.includes('not read')&&!comment.includes('(empty)'),'a field that was empty at the first meeting is watched from then on: '+comment);
    const code=fields(met.rows,'Code');assert.equal(code.length,1);unread(code[0],'Code');
    const notes=fields(met.rows,'Notes');assert.equal(notes.length,1);unread(notes[0],'Notes');
    const passwords=fields(met.rows,'Password');assert.ok(passwords.length>=1);for(const row of passwords)assert.equal(row.expected.password,true);
    // Claude doesn't type into the field it may not read.
    const refused=await rpc('fill_form',{fields:[{...await target('Code'),text:'Overwritten'}]}),refusal=clean('a fill on the unread field',refused);
    assert.ok(refused.ok===false||refused.data.state==='refused',refusal);assert.match(refusal,/owner_signin|does not type into it either/);
    // The field that was empty at the first meeting is Claude's to fill, and is read afterwards.
    const filled=await call('fill_form',{fields:[{...await target('Comment'),text:'PUBLIC_COMMENT_28'}]});assert.equal(filled.remaining,0,JSON.stringify(filled));
    const later=await full('late root, after the fill',tab);
    assert.ok(later.includes('"Comment" = "PUBLIC_COMMENT_28"'),'the field that was empty at the first meeting is read');
    assert.equal(count(later,'"Code" (filled, not read)'),1);assert.equal(count(later,'"Notes" (filled, not read)'),1);
    clean('late root: chrome_read after the fill',await read());
    recording('the late root','PUBLIC_COMMENT_28');
    evidence.push({case:'late',refused,outline:later.split('\n').slice(0,40)});
  });

  await check('GROUP 3 BRIEF28 a form holding an unread field is refused unasked for a click Enter and a page submission',async()=>{
    // Refused, or stopped, with the tool's own message; no question; the receiver has nothing; nothing waits.
    const notSent=async(name,result,id)=>{
      // The reply's own part (its error or data); the pending list beside it belongs to other cases.
      const text=clean(name,result),own=JSON.stringify({error:result.error,data:result.data});
      assert.match(own,WITHHELD,name+': '+own);assert.doesNotMatch(own,/"approval"/,name+': no question');assert.doesNotMatch(text,new RegExp(LATE_DRAFT),name);
      await delay(700);assert.equal(counts(id),0,name+': the receiver has nothing');
      assert.equal(await waitingFor(id),undefined,name+': no operation waits that chrome_submit could run');
      evidence.push({case:'form',name,result});
    };
    const draftUnread=async()=>{const rows=await read();assert.doesNotMatch(JSON.stringify(rows),new RegExp(LATE_DRAFT));const draft=fields(rows,'Draft');assert.equal(draft.length,1);unread(draft[0],'Draft');};
    // 1. The late root holds a form: the draft that held text at the first meeting, a second field and Send.
    const id='brief28-form';await lateRoot(id,'form',[LATE_DRAFT]);await draftUnread();
    const tab=getTab(),send=async name=>notSent(name,await rpc('click',await target('Send')),id);
    await send('a click on Send');
    await notSent('Enter in the second field',await rpc('press',{...await target('Comment'),key:'Enter'}),id);
    // An approved asking read shows the draft once. It doesn't make the field readable for a binding.
    const asked=await call('prepare_read_typed_fields',{tab});assert.ok(asked.approval,JSON.stringify(asked));assert.match(asked.approval.question,/Draft/);
    const shown=await call('read_typed_fields',asked.approval);assert.match(JSON.stringify(shown.untrusted_content),new RegExp(LATE_DRAFT));
    await send('a click on Send after the approved asking read');
    // The draft's text changes after the refusal (the page's script stands in for the owner's edit): there is nothing chrome_submit could run.
    await fixture.mutate(id,'review-change');
    assert.equal(await waitingFor(id),undefined,'no operation waits after the draft changed');
    await send('a click on Send after the draft changed');
    // 2. The same form with a known password field in place of the unread one still asks, and sends once.
    const known='brief28-known';await lateRoot(known,'known',[]);clean('known password form: chrome_read',await read());
    const prepared=await call('click',await target('Send'));clean('the question of a form with a password field',prepared);
    assert.ok(prepared.approval,JSON.stringify(prepared));await approval(prepared,known);
    // 3. A form prepared while every field was readable. While the approval waits, the page moves the late root's filled draft into it.
    const moved='brief28-moved';await lateRoot(moved,'moved',[LATE_DRAFT]);await draftUnread();
    const waiting=await call('click',await target('Send other'));assert.ok(waiting.approval,JSON.stringify(waiting));assert.equal(counts(moved+'-other'),0);
    await fixture.mutate(moved,'review-change');
    for(const attempt of ['first','second']){
      const late=await rpc('submit',waiting.approval),text=clean('chrome_submit after the move',late);
      assert.ok(!late.ok||late.data.operation?.state!=='done',attempt+': '+text);
      assert.equal(late.data?.approval,undefined,attempt+': the changed form is not asked again');assert.ok(!late.data?.followups?.some(item=>item.approval),text);
      assert.doesNotMatch(text,new RegExp(LATE_DRAFT),attempt+': the unread draft is in no question');
      await delay(700);assert.equal(counts(moved+'-other'),0,attempt+': the receiver has nothing');
      evidence.push({case:'moved',attempt,result:late});
    }
    // 4. Last, because the submission stays stopped in this document: one the page starts from a click handler.
    const started='brief28-started';await lateRoot(started,'form',[LATE_DRAFT]);await draftUnread();
    await notSent('a submission the page starts from a click handler',await rpc('click',await target('Continue')),started);
    recording('the refused forms',LATE_DRAFT);
  });
  fs.writeFileSync('/out/unread-fields.json',JSON.stringify(evidence,null,2));
}
