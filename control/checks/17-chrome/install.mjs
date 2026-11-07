// Linux runner installation experiments. No calls from this module are made on macOS.
import fs from 'node:fs';
import path from 'node:path';
import {createHash,sign} from 'node:crypto';
import {execFileSync} from 'node:child_process';

function varint(value){const b=[];do{let n=value&127;value=Math.floor(value/128);if(value)n|=128;b.push(n);}while(value);return Buffer.from(b);}
function bytes(field,value){return Buffer.concat([varint(field*8+2),varint(value.length),value]);}
export function idFor(publicKey){return [...createHash('sha256').update(publicKey).digest().subarray(0,16)].map(b=>String.fromCharCode(97+(b>>4),97+(b&15))).join('');}
export function pack(dir,work,keypair){
  const zip=path.join(work,'own-extension.zip');
  execFileSync('python3',['-c','import pathlib,zipfile,sys;root=pathlib.Path(sys.argv[1]);z=zipfile.ZipFile(sys.argv[2],"w",zipfile.ZIP_DEFLATED);[z.write(p,p.relative_to(root)) for p in sorted(root.rglob("*")) if p.is_file()];z.close()',dir,zip]);
  const payload=fs.readFileSync(zip);
  const publicKey=keypair.publicKey.export({type:'spki',format:'der'});
  const signed=bytes(1,createHash('sha256').update(publicKey).digest().subarray(0,16));
  const len=Buffer.alloc(4);len.writeUInt32LE(signed.length);
  const signature=sign('sha256',Buffer.concat([Buffer.from('CRX3 SignedData\0'),len,signed,payload]),keypair.privateKey);
  const proof=Buffer.concat([bytes(1,publicKey),bytes(2,signature)]);
  const header=Buffer.concat([bytes(2,proof),bytes(10000,signed)]);
  const prefix=Buffer.alloc(12);prefix.write('Cr24');prefix.writeUInt32LE(3,4);prefix.writeUInt32LE(header.length,8);
  const crx=path.join(work,'own-extension.crx');fs.writeFileSync(crx,Buffer.concat([prefix,header,payload]));fs.unlinkSync(zip);
  return crx;
}
export function installExternal(id,version,crx,work){
  if(process.platform!=='linux'||process.env.GITHUB_ACTIONS!=='true')throw Error('External install only on disposable GitHub Linux runner');
  const descriptor=path.join(work,id+'.json');fs.writeFileSync(descriptor,JSON.stringify({external_crx:crx,external_version:version}));
  // The brief authorizes installing Chrome/extensions in CI; never run this on the owner's machine.
  execFileSync('sudo',['install','-D','-m','644',descriptor,`/opt/google/chrome/extensions/${id}.json`]);
  console.log('EXTERNAL_EXTENSION_INSTALLED',id,version,'/opt/google/chrome/extensions/'+id+'.json');
}
