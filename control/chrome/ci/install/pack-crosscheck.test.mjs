// The node cross-check for pack.py (brief 18c-b, item 1). A package made by
// pack.py verifies with node:crypto, and this reader accepts install.mjs's own
// package the same way: that is the packer CI has installed on a real Chrome
// since package 17, so the two write one container format.
// Runs in item 2's container (node, python3 with cryptography):
//   node --test control/chrome/ci/install/*.test.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash,createPublicKey,generateKeyPairSync,verify} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {idFor,pack} from '../../../checks/17-chrome/install.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../../..');
const extension=path.join(root,'control/chrome/extension');

// A protobuf message of length-delimited fields as [[number, bytes]].
function fields(buffer){
  const result=[];let offset=0;
  const varint=()=>{let value=0,scale=1;for(;;){const byte=buffer[offset++];value+=(byte&127)*scale;if(byte<128)return value;scale*=128;}};
  while(offset<buffer.length){
    const tag=varint(),length=varint();
    assert.equal(tag%8,2);
    result.push([Math.floor(tag/8),buffer.subarray(offset,offset+length)]);offset+=length;
  }
  assert.equal(offset,buffer.length);
  return result;
}
function read(crx){
  assert.equal(crx.subarray(0,4).toString('latin1'),'Cr24');
  assert.equal(crx.readUInt32LE(4),3);
  const size=crx.readUInt32LE(8),header=fields(crx.subarray(12,12+size)),archive=crx.subarray(12+size);
  assert.deepEqual(header.map(([number])=>number),[2,10000]);
  const proof=fields(header[0][1]);
  assert.deepEqual(proof.map(([number])=>number),[1,2]);
  const signed=header[1][1],id=fields(signed);
  assert.deepEqual(id.map(([number])=>number),[1]);
  return {publicKey:proof[0][1],signature:proof[1][1],signed,crxId:id[0][1],archive};
}
function verified(crx){
  const parts=read(crx),length=Buffer.alloc(4);length.writeUInt32LE(parts.signed.length);
  const key=createPublicKey({key:parts.publicKey,format:'der',type:'spki'});
  const signedData=Buffer.concat([Buffer.from('CRX3 SignedData\0'),length,parts.signed,parts.archive]);
  assert.equal(verify('sha256',signedData,key,parts.signature),true);
  assert.equal(Buffer.compare(parts.crxId,createHash('sha256').update(parts.publicKey).digest().subarray(0,16)),0);
  return {...parts,key,id:idFor(parts.publicKey)};
}

test("a pack.py package verifies with node:crypto and has install.mjs's container",()=>{
  const work=fs.mkdtempSync(path.join(os.tmpdir(),'pack-crosscheck-'));
  try{
    const output=path.join(work,'bundle');
    const record=JSON.parse(execFileSync('python3',[path.join(root,'control/chrome/packaging/pack.py'),extension,output],{encoding:'utf8'}));
    const file=path.join(output,'extension.crx');
    const ours=verified(fs.readFileSync(file));
    assert.equal(ours.id,record.id);
    assert.equal(ours.key.asymmetricKeyType,'rsa');
    assert.equal(ours.key.asymmetricKeyDetails.modulusLength,2048);
    assert.equal(createHash('sha256').update(ours.publicKey).digest('hex'),record.public_key_sha256);
    assert.equal(createHash('sha256').update(fs.readFileSync(file)).digest('hex'),record.crx_sha256);
    assert.deepEqual(Object.keys(JSON.parse(fs.readFileSync(path.join(output,'policy.json'),'utf8')).ExtensionSettings),[record.id]);
    assert.deepEqual(JSON.parse(fs.readFileSync(path.join(output,'native-host.json'),'utf8')).allowed_origins,[`chrome-extension://${record.id}/`]);
    assert.deepEqual(fs.readdirSync(output).sort(),['extension.crx','native-host.json','policy.json','update.xml']);

    const pair=generateKeyPairSync('rsa',{modulusLength:2048});
    const theirs=verified(fs.readFileSync(pack(extension,work,pair)));
    assert.equal(theirs.id,idFor(pair.publicKey.export({type:'spki',format:'der'})));
    assert.notEqual(theirs.id,ours.id);

    // The check can fail: one changed byte of the archive no longer verifies.
    const broken=Buffer.from(fs.readFileSync(file));broken[broken.length-1]^=1;
    assert.throws(()=>verified(broken));
  }finally{fs.rmSync(work,{recursive:true,force:true});}
});
