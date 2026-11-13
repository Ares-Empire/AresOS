import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

test('P30 ingress instrumentation records native values and raw source before any filtering',()=>{
  for(const page of ['?case=password-matrix','?case=review-page&mode=late-reader']){
  const records=[];
  class Node {get textContent(){return this.text;}}
  class Element extends Node {getAttribute(key){return this.attrs?.[key]??null;}}
  class HTMLElement extends Element {get innerText(){return this.text;}}
  class HTMLInputElement extends HTMLElement {get value(){return this.bytes;}}
  class HTMLTextAreaElement extends HTMLElement {get value(){return this.bytes;}}
  class HTMLSelectElement extends HTMLElement {get value(){return this.bytes;}}
  class HTMLIFrameElement extends HTMLElement {get srcdoc(){return this.source;}}
  const context=vm.createContext({Node,Element,HTMLElement,HTMLInputElement,HTMLTextAreaElement,HTMLSelectElement,HTMLIFrameElement,URL,location:{href:'http://fixture.test/'+page},chrome:{runtime:{sendMessage:value=>{records.push(value);return Promise.resolve();}}}});
  vm.runInContext(fs.readFileSync('control/chrome/ci/password-ingress.js','utf8'),context);
  const field=new HTMLInputElement();field.bytes='SENTINEL_PRIVATE_PASSWORD_20';field.attrs={value:field.bytes};assert.equal(field.value,field.bytes);field.getAttribute('value');
  const frame=new HTMLIFrameElement();frame.source='<input type="password" value="SENTINEL_PRIVATE_PASSWORD_20">';assert.equal(frame.srcdoc,frame.source);
  for(const kind of ['value','attribute:value','srcdoc'])assert.ok(records.some(row=>row.kind===kind&&row.value.includes('SENTINEL_PRIVATE_PASSWORD_20')),kind+' ingress must retain the raw sensitive string so a forbidden getter cannot hide');
  }
});
