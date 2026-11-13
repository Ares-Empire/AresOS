export const lateInputTypes=['text','tel','number','unknown','checkbox','radio','date','email','url','search'];
export function lateReaderPage(){
  const credential='SENTINEL_PRIVATE_PASSWORD_20';
  let fields='';
  for(const [signal,term]of [['name','password'],['id','Passwort'],['autocomplete','PIN'],['aria-label','Passcode'],['placeholder','one-time code'],['label','Sicherheitscode']]){
    const field=`<input type="password" ${signal==='label'?'':signal+'="'+term+'"'} value="${credential}">`;
    fields+=signal==='label'?'<label>'+term+field+'</label>':field;
  }
  fields+=`<input style="-webkit-text-security:disc" aria-label="Security code" value="${credential}">`;
  for(const type of lateInputTypes){
    const value=type==='number'?'123':type==='date'?'2026-11-13':type==='email'?'person@fixture.test':type==='url'?'https://fixture.test/typed':'PUBLIC_TYPED_'+type+'_20';
    fields+=`<input type="${type}" aria-label="Type ${type}" value="${value}">`;
  }
  fields+='<input type="text" value="PUBLIC_UNLABELLED_20"><textarea aria-label="Safe textarea">PUBLIC_TEXTAREA_20</textarea><div contenteditable="true" aria-label="Safe editor">PUBLIC_EDITOR_20</div>';
  return {body:'<form>'+fields+'</form>',script:`for(const field of document.querySelectorAll('input[type=password]'))field.type='text';document.querySelector('[style]').style.webkitTextSecurity='none';globalThis.reviewChange=()=>{document.querySelector('[aria-label="Type text"]').setAttribute('aria-label','Changed text label');const field=document.createElement('input');field.setAttribute('aria-label','Added field');field.value='PUBLIC_ADDED_20';document.querySelector('form').append(field);};`};
}
