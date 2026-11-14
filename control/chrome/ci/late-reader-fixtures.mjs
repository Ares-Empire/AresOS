export const lateInputTypes=['text','tel','number','unknown','checkbox','radio','date','email','url','search','range','color','datetime-local','month','week','time'];
export const lateTypedTypes=['text','tel','number','unknown','email','url','search'];
export function lateReaderPage(){
  const credential='SENTINEL_PRIVATE_PASSWORD_20';
  let fields='';
  for(const [signal,term]of [['name','password'],['id','Passwort'],['autocomplete','PIN'],['aria-label','Passcode'],['placeholder','one-time code'],['label','Sicherheitscode']]){
    const field=`<input type="${signal==='name'?'password':'text'}" ${signal==='label'?'':signal+'="'+term+'"'} value="${credential}">`;
    fields+=signal==='label'?'<label>'+term+field+'</label>':field;
  }
  // Final F2: added names, the card security code token and a label split inside a word.
  for(const [signal,term]of [['autocomplete','cc-csc'],['name','tan'],['aria-label','mTAN'],['placeholder','CVC'],['id','user_pwd'],['name','passwd'],['aria-label','Kartenprüfnummer'],['placeholder','Verifizierungscode'],['aria-label','Geheimzahl'],['name','client_secret'],['aria-label','Passphrase'],['placeholder','Authentifizierungscode'],['label','SMS-TAN'],['label','P<b>a</b>sswort']])
    fields+=signal==='label'?`<label>${term}<input type="text" value="${credential}"></label>`:`<input type="text" ${signal}="${term}" value="${credential}">`;
  for(const term of ['Distanz','Tank'])fields+=`<input type="text" aria-label="${term}" value="PUBLIC_ORDINARY_${term}_20">`;
  fields+=`<span id="credential-label">Password</span><input type="text" aria-labelledby="credential-label" value="${credential}">`;
  fields+=`<label for="credential-combined">Security</label><label for="credential-combined">code</label><input id="credential-combined" type="text" value="${credential}">`;
  fields+=`<input style="-webkit-text-security:disc" aria-label="Security code" value="${credential}">`;
  for(const type of lateInputTypes){
    const value=type==='number'?'123':type==='date'?'2026-11-13':type==='email'?'person@fixture.test':type==='url'?'https://fixture.test/typed':type==='range'?'42':type==='color'?'#112233':type==='datetime-local'?'2026-11-13T10:20':type==='month'?'2026-11':type==='week'?'2026-W46':type==='time'?'10:20':'PUBLIC_TYPED_'+type+'_20';
    fields+=`<input type="${type}" aria-label="Type ${type}" value="${value}">`;
  }
  for(const type of ['search','email','url'])fields+=`<input type="password" data-revealed-type="${type}" aria-label="Previous ${type}" value="PRIVATE_REVEALED_${type}_20">`;
  fields+='<textarea style="-webkit-text-security:disc" aria-label="Long value">PRIVATE_REVEALED_TEXTAREA_20</textarea>';
  fields+='<input type="text" value="PUBLIC_UNLABELLED_20"><textarea aria-label="Safe textarea">PUBLIC_TEXTAREA_20</textarea><div contenteditable="true" aria-label="Safe editor">PUBLIC_EDITOR_20</div>';
  return {body:'<form>'+fields+'</form>',script:`for(const field of document.querySelectorAll('input[type=password]'))field.type=field.getAttribute('data-revealed-type')||'text';for(const field of document.querySelectorAll('[style]'))field.style.webkitTextSecurity='none';globalThis.reviewChange=()=>{document.querySelector('[aria-label="Type text"]').setAttribute('aria-label','Changed text label');const field=document.createElement('input');field.setAttribute('aria-label','Added field');field.value='PUBLIC_ADDED_20';document.querySelector('form').append(field);};`};
}
