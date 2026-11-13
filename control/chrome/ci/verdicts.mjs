// Complete named-suite evidence only; missing or failed cases never qualify.
export const REQUIRED={
    1:['GROUP 1 REVIEW modified deletion keys normalized words malformed URLs and visible names','GROUP 1 Unicode word matching agrees across service and guard','GROUP 1 what asks word/label/key matrix','GROUP 1 submit compose deletion and free-input matrix'],
    2:['GROUP 2 RECHECK3 every single wrapped step holds across roots events and registration order','GROUP 2 RECHECK3 every hyperlink and form submitter default is neutralised','GROUP 2 RECHECK2 every borrowed native insertion route captures noncomposed shadow events','GROUP 2 RECHECK2 native defaults cover new tabs frames ping forms and downloads','GROUP 2 RECHECK2 the owner navigates during the network hold','GROUP 2 RECHECK explicit payment and delete labels override GET search','GROUP 2 RECHECK Claude timer fires inside the owner Enter mark','GROUP 2 REVIEW new shadow roots capture borrowed native events including noncomposed ones','GROUP 2 REVIEW borrowed wrappers respect another controlled tab and an ordinary document','GROUP 2 REVIEW owner mark exact form submitter and unconsumed delayed work','GROUP 2 REVIEW inherited and newly created frames hold submissions','GROUP 2 REVIEW synchronous new shadow roots keep all submission kinds held','GROUP 2 stopped page steps handler/resume matrix','GROUP 2 script activations never replay','GROUP 2 loop with uncancelled enclosing submit sends once','GROUP 2 owner synchronous task delayed work and in-flight interleavings','GROUP 2 after his mark timers never exempt forms submitters or validation repairs','GROUP 2 nested validation and fresh-frame fallback','GROUP 2 delayed submission stays held after slow frame arming','GROUP 2 uncancellable self navigation is stopped before its source document changes','GROUP 2 first-script natives are guarded in pages and frames'],
    3:['GROUP 3 RECHECK3 rendered whitespace survives questions reasking stopping and final dispatch','GROUP 3 changed read-only preview reasks with its changed content','GROUP 3 RECHECK2 live compose text reasks once while outside text stays free','GROUP 3 REVIEW ordinary blank and srcdoc editors bind drafts and send normally','GROUP 3 REVIEW owner chosen attachments show byte digests and bind identical metadata replacements','GROUP 3 REVIEW item confirmation file rich text and title mutations refuse','GROUP 3 binding every form fact and generic sibling draft','GROUP 3 cross-frame adapter empty and oversized drafts'],
    4:['GROUP 4 REVIEW blank and srcdoc native dialogs answer with a held continuation','GROUP 4 REVIEW borrowed native dialogs always ask bind the answer and never replay','GROUP 4 REVIEW ordinary native dialogs from Claude owner and page tasks keep working','GROUP 4 page confirmations bind their full text and ask independently','GROUP 4 exact native confirmation and mismatch matrix','GROUP 4 a native-dialog handler submission is prepared separately','GROUP 4 ADAPTER every named GitHub confirmation mismatch'],
    5:['GROUP 5 RECHECK2C clipboard writes are reported without reading contents','GROUP 5 REVIEW page outcome records the actual post-input notice','GROUP 5 question fields, hidden values, password label, upload path and hash'],
    6:['GROUP 6 exclusions through frame, popup, redirect, taking and history','GROUP 6 schemes links and forward routes'],
    7:['GROUP 7 all password kinds across open closed and cross-site roots','GROUP 7 no listening port after tool suite','GROUP 7 native compatibility inside and outside Claude tabs'],
    8:['GROUP 8 RECHECK2 extension restart reconciles leftover session network rules','GROUP 8 REVIEW preexisting dialogs hand off within bounds and recover after the owner answers','GROUP 8 REVIEW no-op checks and isolated choices leave the owner tab selected','GROUP 8 REVIEW Stop removes navigation blocks while a frozen wrapper awaits cleanup','GROUP 8 REVIEW iframe drafts and detached or Web Audio report before reload','GROUP 8 REVIEW script-started POST documents in tabs and popups never reload','GROUP 8 drop release close and stale references never dispatch prepared work','GROUP 8 actual popup Stop button drops all prepared work','GROUP 8 deadline and tabs outside the group','GROUP 8 taken tabs preserve reads and guard the first input reload','GROUP 8 Stop under a native modal revokes input before deferred cleanup','GROUP 8 popups preserve opener flow and guard first input without moving windows','GROUP 8 opener badges and per-popup Stop preserve windows documents and focus','GROUP 8 closing or releasing an opener ends popup control and clears badges','GROUP 8 POST popups never resubmit and ordinary openers stay untouched'],
    9:['GROUP 9 Chrome host service crash cutpoints never replay'],
    10:['GROUP 10 adapter gmail','GROUP 10 adapter whatsapp','GROUP 10 adapter github','GROUP 10 adapter gemini','GROUP 10 adapter deezer','GROUP 10 read-only bank','GROUP 10 adapter shortcuts and account-specific questions','GROUP 10 ADAPTER Gmail full compose and every bound field','GROUP 10 ADAPTER two Gmail compose windows and inbox shortcut','GROUP 10 ADAPTER WhatsApp every message chat text attachments and free activity','GROUP 10 ADAPTER GitHub actions and all named confirmations','GROUP 10 ADAPTER clear merge settings and sharing variants stay guarded','GROUP 10 ADAPTER Gemini question content and always asking chat changes','GROUP 10 ADAPTER Deezer playback additions removals posts shares and payments','GROUP 10 ADAPTER bank owner restriction all inputs and positive reads links scroll','GROUP 10 ADAPTER unfamiliar pages and qualification fallback on all sites','GROUP 10 ADAPTER Gemini question uses its required semantic name','GROUP 10 ADAPTER Gmail question names its attachments','GROUP 10 ADAPTER Gmail deletion shortcut question names the deletion'],
    11:['GROUP 11 REVIEW explicit pay and delete evidence overrides an owner allowed adapter','GROUP 11 exact owner kind, recipients, account and revocation','GROUP 11 ADAPTER Gmail exact To Cc Bcc roles account revocation and widening','GROUP 11 ADAPTER Gemini exact account owner entry and revocation'],
    13:['GROUP 13 RECHECK2B all-native limit records user activation and honest after-click reporting','GROUP 13 autosave and after-limit submissions are not held'],
  };

// Adapter-specific evidence must not turn an unrelated adapter off.
const MULTI_ADAPTER_REQUIRED={
  'GROUP 10 ADAPTER clear merge settings and sharing variants stay guarded':['github','gemini','deezer'],
  'GROUP 10 adapter shortcuts and account-specific questions':['gmail','whatsapp','gemini'],
  'GROUP 10 ADAPTER unfamiliar pages and qualification fallback on all sites':['gmail','whatsapp','github','bank','gemini','deezer'],
};
export const ADAPTER_REQUIRED=Object.fromEntries(['gmail','whatsapp','github','bank','gemini','deezer'].map(site=>[site,
  Object.values(REQUIRED).flat().filter(name=>
    name===`GROUP 10 adapter ${site}` || site==='bank'&&name==='GROUP 10 read-only bank' ||
    site==='gmail'&&name==='GROUP 10 ADAPTER two Gmail compose windows and inbox shortcut' ||
    site==='github'&&name==='GROUP 4 ADAPTER every named GitHub confirmation mismatch' ||
    MULTI_ADAPTER_REQUIRED[name]?.includes(site) ||
    new RegExp(`^GROUP (?:4|10|11) ADAPTER ${site}\\b`,'i').test(name))]));
export const SUPPORT=['FEATURE tools forms options find wait fill_form scroll and full catalogues','VIEW representative long article/form complete paging','QUALIFICATION conservative activations ask and core failures gate before reads'];
const adapterNames=new Set(Object.values(ADAPTER_REQUIRED).flat());
const sharedAdapterNames=Object.values(REQUIRED).flat().filter(name=>/^GROUP (?:4|10|11) ADAPTER /.test(name)&&!adapterNames.has(name));

export function verdicts(results,baseline,adapters){
  const passed=name=>{const matches=results.filter(item=>item?.name===name);return matches.length===1&&matches[0].passed===true;};
  const groups=Object.fromEntries(Object.entries(REQUIRED).map(([group,names])=>[group,names.every(passed)]));
  groups[2] &&= baseline.owner===true;
  groups[7] &&= baseline.forgery===true && baseline.isolation===true;
  groups[13] &&= baseline.residual===true;
  // Only 18d's actual precedence harness can supply group 12. Now cannot qualify.
  groups[12]=false;
  const known=new Set([...Object.values(REQUIRED).flat(),...SUPPORT]);
  const support=SUPPORT.every(passed)&&results.every(item=>known.has(item?.name));
  const sharedGroup=group=>REQUIRED[group].filter(name=>!name.includes(' ADAPTER ')).every(passed);
  const qualified={groups,core:{classification:groups[1],page_script:groups[2]&&groups[8]&&groups[9]&&groups[13],binding:groups[3]&&sharedGroup(4)&&groups[5],password_exclusion:groups[7]},adapters:{}};
  for(const group of Object.keys(qualified.core))qualified.core[group] &&= groups[6]&&support;
  const shared=Object.values(qualified.core).every(Boolean)&&sharedGroup(11)&&sharedAdapterNames.every(passed);
  for(const [site,names]of Object.entries(ADAPTER_REQUIRED))qualified.adapters[site]=adapters[site]===true&&shared&&names.every(passed);
  return qualified;
}


export function assertComplete(results,qualified){
  const expected=[...Object.values(REQUIRED).flat(),...SUPPORT].sort(),actual=results.map(row=>row?.name).sort();
  if(JSON.stringify(expected)!==JSON.stringify(actual)||results.some(row=>row.passed!==true))throw Error('Incomplete or failing named browser inventory');
  for(const [section,names]of Object.entries({groups:[...Object.keys(REQUIRED),'12'],core:['classification','page_script','binding','password_exclusion'],adapters:Object.keys(ADAPTER_REQUIRED)})){if(JSON.stringify(Object.keys(qualified[section]).sort())!==JSON.stringify(names.sort()))throw Error('Incomplete verdict inventory: '+section);}
  if(qualified.groups[12]!==false||Object.entries(qualified.groups).some(([group,value])=>group!=='12'&&value!==true)||Object.values(qualified.core).some(value=>value!==true)||Object.values(qualified.adapters).some(value=>value!==true))throw Error('A core, adapter or group verdict failed');
}
