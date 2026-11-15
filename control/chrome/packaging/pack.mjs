// CRX3 packaging is browser-free. Key identity is stable; no private key is copied to output.
import fs from 'node:fs';
import path from 'node:path';
import {createPrivateKey,createPublicKey} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {pack,idFor} from '../../checks/17-chrome/install.mjs';

export function packageExtension(extension,output,pem) {
  const privateKey=createPrivateKey(pem),publicKey=createPublicKey(privateKey);
  fs.mkdirSync(output,{recursive:true});
  const id=idFor(publicKey.export({type:'spki',format:'der'}));
  const file=pack(extension,output,{privateKey,publicKey});
  return {id,file,version:JSON.parse(fs.readFileSync(path.join(extension,'manifest.json'))).version};
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const [key,output]=process.argv.slice(2);
  if (!key || !output) throw Error('Usage: node control/chrome/packaging/pack.mjs KEY.pem OUTPUT');
  console.log(JSON.stringify(packageExtension(path.resolve('control/chrome/extension'),path.resolve(output),fs.readFileSync(key))));
}
