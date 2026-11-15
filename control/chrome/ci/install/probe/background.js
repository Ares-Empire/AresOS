// Test-only probe (brief 18c-b, item 2). The install checks ask Chrome about its extensions through
// this extension and its own native host, so Chrome needs no debugging port. Never part of a release.
const HOST='org.aresos.install_probe';
const view=info=>({id:info.id,name:info.name,version:info.version,enabled:info.enabled,installType:info.installType,
  mayDisable:info.mayDisable,type:info.type,disabledReason:info.disabledReason??null,updateUrl:info.updateUrl??null});
const operations={
  async all(){return (await chrome.management.getAll()).map(view);},
  async get({id}){return view(await chrome.management.get(id));},
  async setEnabled({id,enabled}){await chrome.management.setEnabled(id,enabled);return true;},
  async uninstall({id}){await chrome.management.uninstall(id);return true;},
  // An update check of this probe alone, at once: shows where its checks go.
  async requestUpdateCheck(){return await chrome.runtime.requestUpdateCheck();},
  // What Chrome does with this extension's connection to another native host:
  // refused (with Chrome's reason), or still open after `wait` milliseconds.
  connectNative({name,wait=3000}){
    return new Promise(resolve=>{
      const messages=[];let settled=false;
      const finish=value=>{if(settled)return;settled=true;resolve({...value,messages});};
      const other=chrome.runtime.connectNative(name);
      other.onMessage.addListener(message=>messages.push(message));
      other.onDisconnect.addListener(()=>finish({connected:false,error:chrome.runtime.lastError?.message??null}));
      setTimeout(()=>{finish({connected:true,error:null});try{other.disconnect();}catch{}},wait);
    });
  },
};
let port=null;
function connect(){
  if(port)return;
  const current=port=chrome.runtime.connectNative(HOST);
  current.onMessage.addListener(async request=>{
    let reply;
    try{
      if(!Object.hasOwn(operations,request.op))throw Error('unknown operation');
      reply={id:request.id,ok:true,value:await operations[request.op](request.args??{})};
    }catch(error){reply={id:request.id,ok:false,error:String(error?.message??error)};}
    try{current.postMessage(reply);}catch{}
  });
  // An open native port keeps this worker alive; a lost one is opened again.
  current.onDisconnect.addListener(()=>{void chrome.runtime.lastError;if(port===current)port=null;setTimeout(connect,500);});
  current.postMessage({event:'hello',id:chrome.runtime.id,version:chrome.runtime.getManifest().version});
}
chrome.runtime.onStartup.addListener(connect);
chrome.runtime.onInstalled.addListener(connect);
connect();
