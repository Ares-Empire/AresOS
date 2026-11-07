// The 17d dunst action-menu helper, now answering a checkpoint-owned capture.
export default async function(c,operation){
 const notification=c.spawn('dunstify',['--appname=17e checkpoint CHECK','--timeout=0','--action=send,Send',"--action=drop,Don't send",'--block','Guarded fixture send',`Captured synthetic operation ${operation.id}. ${operation.length} bytes.`],{stdio:['ignore','pipe','pipe']});
 let output='',errors='';notification.stdout.on('data',b=>output+=b);notification.stderr.on('data',b=>errors+=b);
 const done=new Promise((resolve,reject)=>{notification.on('error',reject);notification.on('exit',code=>code===0?resolve(output.trim()):reject(Error('dunstify: '+errors)))});
 await c.delay(500);await c.screenshot(c.out,'owner-notification-waiting');
 const menu=c.spawn('dunstctl',['context'],{stdio:'ignore'});await c.delay(500);await c.screenshot(c.out,'owner-notification-menu');c.x('type','--clearmodifiers','Send');await c.key('Return');
 try{const action=await Promise.race([done,c.delay(6000).then(()=>{throw Error('No real notification action')})]);c.assert.equal(action,'send');await c.control('approve',{id:operation.id});return action;}finally{menu.kill();notification.kill();}
}
