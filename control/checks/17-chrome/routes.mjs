import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {execFileSync,execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {createHash} from 'node:crypto';
import {launch,address,key,x,delay,loadUnpacked,screenshot,stopChrome} from './ui.mjs';
import {websocket,session,evaluate,eventually} from './protocol.mjs';
import {save,readAndAct,holdChecks,disconnectProbe} from './checks.mjs';
import {installExternal} from './install.mjs';

const require=createRequire(import.meta.url);
export async function otherRoutes({here,work,out,profile,fixture}){
  const results={};let chrome,browser,raw;
  try{
    // Exact Web Store artifact 0.5.0. Integrity pinned; no automatic version substitution.
    const crx=path.join(work,'playwright.crx');
    execFileSync('curl',['-fsSL','--retry','3','https://clients2.google.com/service/update2/crx?response=redirect&prodversion=158.0.0.0&acceptformat=crx2,crx3&x=id%3Dmmlmfjhmonkocbjadbfplnigmagldckm%26uc','-o',crx]);
    const hash=createHash('sha256').update(fs.readFileSync(crx)).digest('hex');
    assert.equal(hash,'598517ba87d9f2f3b3642483cb6662bc0ea061401c5d3c1eb188a19847c92b0b');
    const extension=path.join(work,'playwright-extension');
    execFileSync('python3',['-c','import zipfile,sys;zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])',crx,extension]);
    const manifest=JSON.parse(fs.readFileSync(path.join(extension,'manifest.json')));assert.equal(manifest.version,'0.5.0');
    save(out,'playwright-pin',{version:manifest.version,sha256:hash,engine:'1.65.0'});
    installExternal('mmlmfjhmonkocbjadbfplnigmagldckm',manifest.version,crx,work);
    chrome=launch(profile,fixture.base+'/owner',path.join(out,'chrome-playwright.log'));await delay(3000);
    await address(fixture.base+'/owner');
    // The tab is open and signed in before the upstream attach factory is invoked.
    const {tools}=require('./node_modules/playwright-core/lib/coreBundle.js');
    const config={extension:true,browser:{browserName:'chromium',userDataDir:profile,launchOptions:{channel:'chrome'},contextOptions:{}},timeouts:{}};
    const connecting=tools.createBrowserWithInfo(config,{clientName:'AresOS check'},{browser:'chrome'},{title:'Chrome feasibility check',workspaceDir:here});
    connecting.catch(()=>{});
    await delay(2500);await screenshot(out,'playwright-consent');
    await key('ctrl+f');x('type','Owner fixture');await key('Escape');await key('Tab');await key('Return');
    const info=await Promise.race([connecting,delay(10000).then(()=>{throw Error('Playwright tab selection did not complete');})]);
    browser=info.browser;
    const context=browser.contexts()[0];
    const page=await eventually(()=>context.pages().find(p=>p.url()===fixture.base+'/owner'),'Playwright selected existing tab');
    assert.match(await page.locator('body').innerText(),/Signed in: synthetic member/);
    // Public newCDPSession asks for a browser-target session, which chrome.debugger rejects.
    // For this pinned experiment, reuse the page session already owned by the upstream bridge.
    const impl=page._connection.toImpl(page),delegate=impl.delegate;
    const cdp=delegate._mainFrameSession._client;
    cdp.pwPage=page;
    await screenshot(out,'playwright-attached');
    console.log('ATTACH_PLAYWRIGHT PASS','extension 0.5.0, engine 1.65.0; existing signed-in tab');
    const frameSessions=async()=>{
      return [...delegate._sessions.values()].filter(s=>s!==delegate._mainFrameSession).map(s=>({sessionId:s._targetId,cdp:s._client}));
    };
    results.playwright={metrics:await readAndAct(cdp,fixture,out,'playwright',options=>page.ariaSnapshot(options),frameSessions),holds:await holdChecks(cdp,fixture,out,'playwright')};
    try{
      const peer=await promisify(execFile)(process.execPath,[path.join(here,'peer-probe.mjs'),'playwright',info.endpoint,page.url()],{timeout:6000});
      results.playwright.peer={result:'another same-UID process reused the bound endpoint without new Chrome consent',output:peer.stdout.trim()};
    }catch(e){results.playwright.peer={result:'peer could not reuse endpoint',output:e.stdout?.trim(),error:e.message};}
    console.log('PLAYWRIGHT_SAME_UID_PEER',JSON.stringify(results.playwright.peer));
    results.playwright.disconnect=await disconnectProbe(cdp,fixture,out,'playwright',async()=>browser.close());browser=undefined;await stopChrome(chrome);chrome=undefined;

    // Consent-based debugging is enabled from chrome://inspect, never via launch switches.
    chrome=launch(profile,fixture.base+'/owner',path.join(out,'chrome-consent.log'));await delay(2800);
    await key('ctrl+t');await address('chrome://inspect/#remote-debugging');
    await screenshot(out,'consent-inspect-before');
    // UI checkbox in Chrome's remote-debugging panel; screenshot documents the experiment.
    x('mousemove',253,170,'click',1);await delay(800);await screenshot(out,'consent-inspect-enabled');
    const portFile=path.join(profile,'DevToolsActivePort');
    await eventually(()=>fs.existsSync(portFile),'consent DevToolsActivePort',4000);
    const [port,wsPath]=fs.readFileSync(portFile,'utf8').trim().split('\n');
    const endpoint=`ws://127.0.0.1:${port}${wsPath}`;
    const attach=websocket(endpoint);attach.catch(()=>{});await delay(700);await screenshot(out,'consent-request');
    await key('Tab');await key('Return');
    raw=await Promise.race([attach,delay(5000).then(()=>{throw Error('Chrome consent not accepted');})]);
    const targets=(await raw.send('Target.getTargets')).targetInfos;
    const target=targets.find(t=>t.url===fixture.base+'/owner');assert.ok(target);
    const {sessionId}=await raw.send('Target.attachToTarget',{targetId:target.targetId,flatten:true});
    const cdpConsent=session(raw,sessionId);
    assert.match(await evaluate(cdpConsent,'document.body.innerText'),/Signed in: synthetic member/);
    await screenshot(out,'consent-attached');
    console.log('ATTACH_CONSENT PASS','running Linux stable; owner enabled inspect and approved connection; TCP port='+port);
    results.consent={metrics:await readAndAct(cdpConsent,fixture,out,'consent'),holds:await holdChecks(cdpConsent,fixture,out,'consent')};
    results.consent.disconnect=await disconnectProbe(cdpConsent,fixture,out,'consent',async()=>raw.close());raw=undefined;
    await stopChrome(chrome);chrome=undefined;
  } finally {
    save(out,'other-routes',results);
    if(raw)raw.close();if(browser)await browser.close();if(chrome)await stopChrome(chrome);
  }
  return results;
}
