import test from 'node:test';
import assert from 'node:assert/strict';
import {generateKeyPairSync,createHash,verify} from 'node:crypto';
import fs from 'node:fs';
import {packageExtension} from '../chrome/packaging/pack.mjs';

test('signed CRX3 keeps key-derived identity; packaging starts no browser',()=>{
  const work=fs.mkdtempSync('.work/20-chrome/pack-');
  try {
    const key=generateKeyPairSync('rsa',{modulusLength:2048});
    const pem=key.privateKey.export({type:'pkcs8',format:'pem'});
    const first=packageExtension('control/chrome/extension',work,pem), second=packageExtension('control/chrome/extension',work,pem);
    assert.equal(first.id,second.id);assert.match(first.id,/^[a-p]{32}$/);
    const file=fs.readFileSync(first.file);assert.equal(file.subarray(0,4).toString(),'Cr24');assert.equal(file.readUInt32LE(4),3);
    assert.ok(file.length>file.readUInt32LE(8)+12);
    assert.equal(fs.readdirSync(work).some(name=>/pem|key|profile/.test(name)),false);
  } finally {fs.rmSync(work,{recursive:true,force:true});}
});
