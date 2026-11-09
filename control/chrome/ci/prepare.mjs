import fs from 'node:fs';
import {generateKeyPairSync} from 'node:crypto';
import {packageExtension} from '../packaging/pack.mjs';
if(process.platform !== 'linux' || process.env.GITHUB_ACTIONS !== 'true' || !fs.existsSync('/.dockerenv'))throw Error('CI Linux container only');
const pair=generateKeyPairSync('rsa',{modulusLength:2048});
const result=packageExtension('/workspace/control/chrome/extension','/workspace/.work/20-package',pair.privateKey.export({type:'pkcs8',format:'pem'}));
fs.writeFileSync('/out/extension.json',JSON.stringify({id:result.id,version:result.version}));
fs.mkdirSync('/etc/aresos/control',{recursive:true});
fs.writeFileSync('/etc/aresos/control/chrome-excluded-sites.json',JSON.stringify({format:1,hosts:['approval.test']}),{mode:0o640});
fs.chownSync('/etc/aresos/control/chrome-excluded-sites.json',0,1001);
fs.mkdirSync('/etc/opt/chrome/native-messaging-hosts',{recursive:true});
fs.writeFileSync('/etc/opt/chrome/native-messaging-hosts/org.aresos.chrome.json',JSON.stringify({name:'org.aresos.chrome',description:'Synthetic test host',path:'/usr/libexec/aresos-control/chrome/host',type:'stdio',allowed_origins:[`chrome-extension://${result.id}/`]}));
if(process.env.INSTALL_MODE === 'policy') {
  fs.mkdirSync('/etc/opt/chrome/policies/managed',{recursive:true});
  fs.writeFileSync('/etc/opt/chrome/policies/managed/aresos.json',JSON.stringify({ExtensionInstallForcelist:[result.id+';http://127.0.0.1:8765/update.xml'],ExtensionSettings:{[result.id]:{toolbar_pin:'force_pinned'}}}));
} else {
  fs.mkdirSync('/opt/google/chrome/extensions',{recursive:true});
  fs.writeFileSync(`/opt/google/chrome/extensions/${result.id}.json`,JSON.stringify({external_crx:result.file,external_version:result.version}));
}
