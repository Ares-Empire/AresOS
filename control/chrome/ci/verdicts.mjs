// Complete named-suite evidence only; missing or failed cases never qualify.
export const REQUIRED={
    1:['GROUP 1 Unicode word matching agrees across service and guard','GROUP 1 what asks word/label/key matrix','GROUP 1 submit compose deletion and free-input matrix'],
    2:['GROUP 2 stopped page steps handler/resume matrix','GROUP 2 script activations never replay','GROUP 2 loop with uncancelled enclosing submit sends once','GROUP 2 owner synchronous task delayed work and in-flight interleavings','GROUP 2 nested validation and fresh-frame fallback','GROUP 2 delayed submission stays held after slow frame arming','GROUP 2 unknown activation survives navigation of its source document'],
    3:['GROUP 3 binding every form fact and generic sibling draft','GROUP 3 cross-frame adapter empty and oversized drafts'],
    4:['GROUP 4 page confirmations bind their full text and ask independently','GROUP 4 exact native confirmation and mismatch matrix','GROUP 4 a native-dialog handler submission is prepared separately'],
    5:['GROUP 5 question fields, hidden values, password label, upload path and hash'],
    6:['GROUP 6 exclusions through frame, popup, redirect, taking and history','GROUP 6 schemes links and forward routes'],
    7:['GROUP 7 all password kinds across open closed and cross-site roots','GROUP 7 no listening port after tool suite','GROUP 7 native compatibility inside and outside Claude tabs'],
    8:['GROUP 8 drop release close and stale references never dispatch prepared work','GROUP 8 actual popup Stop button drops all prepared work','GROUP 8 deadline and tabs outside the group','GROUP 8 taken tabs preserve reads and guard the first input reload'],
    9:['GROUP 9 Chrome host service crash cutpoints never replay'],
    10:['GROUP 10 adapter gmail','GROUP 10 adapter whatsapp','GROUP 10 adapter github','GROUP 10 adapter gemini','GROUP 10 adapter deezer','GROUP 10 read-only bank','GROUP 10 adapter shortcuts and account-specific questions'],
    11:['GROUP 11 exact owner kind, recipients, account and revocation'],
    13:['GROUP 13 changed read-only preview is a stated residual','GROUP 13 autosave and after-limit submissions are not held'],
  };

export function verdicts(results,baseline,adapters){
  const passed=name=>{const matches=results.filter(item=>item?.name===name);return matches.length===1&&matches[0].passed===true;};
  const groups=Object.fromEntries(Object.entries(REQUIRED).map(([group,names])=>[group,names.every(passed)]));
  groups[2] &&= baseline.owner===true;
  groups[7] &&= baseline.forgery===true && baseline.isolation===true;
  groups[13] &&= baseline.residual===true;
  const supportNames=['FEATURE tools forms options find wait fill_form scroll and full catalogues','VIEW representative long article/form complete paging','QUALIFICATION conservative activations ask and core failures gate before reads'];
  const support=supportNames.every(passed)&&results.every(item=>[...Object.values(REQUIRED).flat(),...supportNames].includes(item?.name));
  const qualified={groups,core:{classification:groups[1],page_script:groups[2]&&groups[8]&&groups[9]&&groups[13],binding:groups[3]&&groups[4]&&groups[5],password_exclusion:groups[7]},adapters:Object.fromEntries(['gmail','whatsapp','github','bank','gemini','deezer'].map(site=>[site,adapters[site]===true&&groups[10]&&groups[11]&&support]))};
  for(const group of Object.keys(qualified.core))qualified.core[group] &&= groups[6]&&support;
  return qualified;
}
