// Compile synthetic page code locally; this test never starts a browser.
import assert from 'node:assert/strict';
import test from 'node:test';
import vm from 'node:vm';
import {sitePage} from '../chrome/ci/sites/fixture.mjs';

test('adapter fixture scripts compile for every site and confirmation mismatch',()=>{
  for(const site of ['gmail','whatsapp','github','gemini','deezer','bank'])for(const variant of ['', 'two','unknown','incomplete'])for(const mismatch of ['', 'kind','text','frame','site','button','twice']){
    const url=new URL('http://'+site+'.test:8765/?case=adapter-sites&id=fixture&variant='+variant+'&mismatch='+mismatch);
    const page=sitePage(url,url.host);new vm.Script(page.script);
    assert.ok(page.body.length);assert.doesNotMatch(page.script,/https?:\/\/(?![^\s"']*\.test)/);
  }
  new vm.Script(sitePage(new URL('http://second.test:8765/?id=child&variant=child'),'second.test:8765').script);
});
