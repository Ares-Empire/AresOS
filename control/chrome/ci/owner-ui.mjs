// Native owner input and window observations for the Linux fixture driver.
// Importing this module starts nothing; browser-free tests inject the executor.
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';

export function ownerUI({call,currentTab,window,eventually,exec=execFileSync}){
  async function tabInfo(tab){
    let cursor;
    do{
      const page=await call('tabs',{limit:10,...(cursor?{cursor}:{})});
      const item=page.items.find(item=>item.tab===tab);if(item)return item;
      cursor=page.cursor;
    }while(cursor);
  }
  async function select(tab){
    const before=await eventually(async()=>{const item=await tabInfo(tab);return item&&!item.cleanup_pending&&item;},'owner tab restoration settled');
    assert.ok(Number.isInteger(before.index)&&before.index>=0&&before.index<100,'native tab index is required');
    exec('xdotool',['windowactivate','--sync',window()]);
    exec('xdotool',['key','--clearmodifiers','ctrl+1']);
    if(before.index)exec('xdotool',['key','--clearmodifiers',...Array(before.index).fill('ctrl+Tab')]);
    await eventually(async()=>{const item=await tabInfo(tab);return item?.active&&item.focused&&item.window===before.window&&item.index===before.index;},'owner selected the exact tab');
  }
  return {
    select,
    async navigate(url){
      const tab=currentTab();await select(tab);
      exec('xdotool',['key','--clearmodifiers','ctrl+l']);
      exec('xdotool',['type','--clearmodifiers','--delay','1',url]);exec('xdotool',['key','Return']);
      await eventually(async()=>(await tabInfo(tab))?.url===url,'owner navigation committed in the exact tab');
    },
    async stopPopup(tab,{openPopup,state,capture}){
      await select(tab);await openPopup();
      // Opening the toolbar popup is the owner's focus change. Measure Stop from here.
      const before=await state(),beforeFocus=exec('xdotool',['getactivewindow'],{encoding:'utf8'}).trim();
      capture('before');exec('xdotool',['key','--clearmodifiers','Tab','Tab','Return']);
      await eventually(async()=>!(await state()).popups.length,'owner per-popup Stop ends control');
      const after=await state(),afterFocus=exec('xdotool',['getactivewindow'],{encoding:'utf8'}).trim();
      capture('after');exec('xdotool',['key','--clearmodifiers','Escape']);
      return {before,after,beforeFocus,afterFocus};
    },
    async closeOpener(tab,url){
      await select(tab);const backup=await call('open',{url});
      const replacement=backup.untrusted_content?.tab;
      assert.ok(Number.isInteger(replacement),'open must return the replacement tab in untrusted_content');
      await select(tab);exec('xdotool',['key','--clearmodifiers','ctrl+w']);
      await eventually(async()=>!await tabInfo(tab),'owner closes opener');return replacement;
    },
    async popupWindow(id){
      assert.match(id,/^[a-z0-9-]+$/);let previous;
      return eventually(()=>{
        const windows=exec('xdotool',['search','--onlyvisible','--name','^Popup '+id+'( -|$)'],{encoding:'utf8'}).trim().split('\n').filter(Boolean);
        assert.equal(windows.length,1,'one uniquely titled native popup');
        const value=exec('xdotool',['getwindowgeometry','--shell',windows[0]],{encoding:'utf8'});
        const state={window:windows[0],...Object.fromEntries(['X','Y','WIDTH','HEIGHT'].map(key=>[key,Number(value.match(new RegExp('^'+key+'=(-?\\d+)','m'))?.[1])]))};
        assert.ok(state.WIDTH>0&&state.HEIGHT>0&&Number.isFinite(state.X)&&Number.isFinite(state.Y),'popup is mapped with native geometry');
        const stable=JSON.stringify(state)===JSON.stringify(previous);previous=state;return stable&&state;
      },'native popup geometry settled');
    },
  };
}
