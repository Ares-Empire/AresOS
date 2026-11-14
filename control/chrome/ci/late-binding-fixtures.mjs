// Unknown-history fixtures, opened by native owner navigation before take.
export function lateBindingPage(url){
  const mode=url.searchParams.get('mode'),id=url.searchParams.get('id'),variant=url.searchParams.get('variant');
  if(mode==='late-binding-child'){
    const phase=url.searchParams.get('phase');
    return {body:`<input aria-label="Frame value" value="PRIVATE_FRAME_${phase}_20">`,script:`fetch('/compat-report',{method:'POST',body:JSON.stringify({id:${JSON.stringify(id)},phase:'late-frame-ready',version:${JSON.stringify(phase)}})});`};
  }
  if(mode==='late-withheld-form')return {
    body:'<div id="host"></div><iframe name="sink" hidden></iframe>',
    script:`const root=document.querySelector('#host').attachShadow({mode:'closed'});root.innerHTML='<form method="post" target="sink" action="/receive?case='+${JSON.stringify(id)}+'"><label>Draft<input name="draft" value="PRIVATE_LATE_FORM_A_20"></label><button type="submit">Send</button></form>';globalThis.reviewChange=()=>{root.querySelector('input').value='PRIVATE_LATE_FORM_B_20';};fetch('/compat-report',{method:'POST',body:JSON.stringify({id:${JSON.stringify(id)},phase:'late-form-ready'})});`,
  };
  const child='http://second.test:8766/?case=review-page&mode=late-binding-child&id='+encodeURIComponent(id)+'&phase=';
  const change=variant==='replacement'?`document.querySelector('input').outerHTML='<input aria-label="Value" value="PRIVATE_REPLACED_20">';`:variant==='frame'?`document.querySelector('iframe').src=${JSON.stringify(child+'next')};`:variant==='credential'?`const field=document.querySelector('input');field.placeholder='Passwort';field.value='SENTINEL_PRIVATE_PASSWORD_20';`:`document.querySelector('input').setAttribute('aria-label','Relabelled value');`;
  return {body:`<input aria-label="Value" value="PRIVATE_FIRST_20"><input aria-label="Value" value="PRIVATE_SECOND_20"><input value="PRIVATE_UNLABELLED_20"><iframe src="${child}first"></iframe>`,script:`globalThis.reviewChange=()=>{${change}};`};
}
