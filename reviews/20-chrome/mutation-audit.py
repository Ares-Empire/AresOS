"""Browser-free review mutations, in a disposable copy inside this worktree."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'.work/20-review-mutations';WORK.mkdir(parents=True,exist_ok=True)
CASES=[]
def case(item,file,before,after,test,python=False,extra=()):
    CASES.append(dict(item=item,edits=[(file,before,after),*extra],test=test,python=python))
P='control/aresos_control/chrome/policy.py'
A='control/aresos_control/chrome/adapter.py'
B='control/chrome/extension/background.js'
G='control/chrome/extension/guard.js'
R='control/chrome/extension/reader.js'
M='control/chrome/extension/page.js'
def node(file,pattern):return [file,pattern]
case('P1',B,'const armed=await armDialog(tab,command.conservative);','const armed={owner:controlled.get(tab),nonce:"unarmed",frames:[]};armed.owner.hold={};',node('background','P1|answering a dialog collects'))
case('P1-boundary',B,'source.state.dialogBarrier={nonce,token:entry.token,documents,source,resolve,reject,ready};','',node('background','answering a dialog collects'))
case('P1-window-return',M,"finally{report(target,{kind:'dialog_end',token,dialog_kind:name});}",'finally{}',node('page','P1 native dialog return values'))
case('P1-dialog-conversion',M,'if(arguments[index]!==undefined)arguments[index]=`${arguments[index]}`;','',node('page','P1 borrowed dialogs during'))
case('P1-opening-once',B,'!native||native.dialog||native.kind','!native||native.kind',node('background','P1 a private native token'))
case('P1-opening-binding',B,'entry.dialog!==dialog.id||','',node('background','P1 a cross-site dialog'))
case('P1-opening-readiness',B,'if(opening){','if(false){',node('background','P1 native dialog metadata waits'))
case('P1-opening-final-reader',B,'if(dialogs.has(tab))return facts(tab,reference,typedOnly);','',node('background','P1 a dialog opening during'))
case('P1-opening-completion',B,'dialogOpenings.delete(dialog);finishOpening();','dialogOpenings.delete(dialog);',node('background','P1 native dialog metadata waits'))
case('P1-opening-deadline',B,"dialog opener is still being established; read again before answering')),5000)","dialog opener is still being established; read again before answering')),30000)",node('background','P1 dialog classification waits'))
case('P1-dialog-fresh',B,"if(dialogs.get(tab)!==expectedDialog)throw Error('stale_approval: dialog changed while checking its guard coverage');",'',node('background','P1 a dialog changed during'))
case('P1-end-lifetime',B,"retireNativeDialog(state.tab,document.document,boundary.result.value.token);",'void 0;',node('background','P1 a private end pause'))
case('P1-end-late-begin',B,"!nativeDialogEnds.has(JSON.stringify([sender.tab.id,message.document,message.token]))&&",'',node('background','P1 a private end pause'))
case('catalogue-active-lifetime',B,'record.time=Date.now();listSnapshots.delete(record.id);listSnapshots.set(record.id,record);','',node('background','catalogue snapshots survive'))
case('catalogue-absolute-lifetime',B,' || Date.now()-record.created>=1800000','',node('state-catalogues','active catalogue walks expire'))
case('catalogue-idle-deadline',B,'Date.now()-record.time>=300000','Date.now()-record.time>300000',node('state-catalogues','idle catalogue'))
case('catalogue-absolute-pruning',B,' || now-value.created>=1800000','',node('state-catalogues','new catalogues prune'))
case('catalogue-restart-message',B,'start the list again without a cursor','try later',node('state-catalogues','active catalogue walks expire'))
case('P1-end-pause-fresh',B,"if(current())await targetCommand(state,'Debugger.resume');","await targetCommand(state,'Debugger.resume');",node('background','P1 an old private end query'))
case('P1-return-no-poison',B,'if(owner&&pauseCurrent())owner.dialogPauseFailed=true;','if(owner)owner.dialogPauseFailed=true;',node('background','P1 an old dialog return query'))
case('P1-auth',B,"if(boundary.result.value.token!==barrier.token)",'if(false)',node('background','P1 only the authenticated'))
case('P1-conservative',A,"'operation':operation,'conservative':payload.get('conservative',False)","'operation':operation",'test_questions.Questions.test_p1_native_answer_keeps_the_service_conservative_policy',True)
case('P1-cross-site-target',B,"const source=documents.find(value=>value.doc.document===entry?.document);","const source=documents.find(value=>value.doc.document===entry?.document&&!value.state.source?.sessionId);",node('background','P1 a cross-site dialog'))
case('P1-coverage',B,'const documents=frames.map(frame=>candidates.find(value=>value.doc.document===privacyDocuments.get(frame.documentId)));','const documents=candidates;',node('background','answering a dialog collects'))
case('P1-ready',B,'privacyDocuments.set(sender.documentId,message.document);','',node('background','P1 native document registration'))
case('P1-existing-allowance',B,'(!existing.hasAllowance||approvedConfirmation)','true',node('background','P1 an existing modal hold'))
case('P1-existing-proof',B,'documents.every(value=>value.doc.activeNonce===existing.nonce)','true',node('background','P1 an existing modal hold'))
case('P1-borrowed-asks',A,"kind='confirmation'","kind=None",'test_questions.Questions.test_p1_decided_borrowed_dialog_always_asks_binds_answer_and_never_trusts',True)
case('P1-borrowed-warning',A,"This dialog used a native function outside the page guard; its continuation isn't held.",'Continuation approved.','test_questions.Questions.test_p1_decided_borrowed_dialog_always_asks_binds_answer_and_never_trusts',True)
case('P1-borrowed-trust',A,"if payload.get('unguarded_dialog'):",'if False:','test_questions.Questions.test_p1_borrowed_dialog_never_inherits_an_otherwise_valid_owner_entry',True)
case('P1-borrowed-answer',B,"answer:{accept:command.input.accept,...(command.input.text===undefined?{}:{text:command.input.text})}",'answer:command.binding.answer',node('background','P1 decided borrowed dialog refuses'))
case('P1-borrowed-approval',B,"if(command.approved!==true||!command.operation)",'if(false)',node('background','P1 decided borrowed dialog refuses'))
case('P1-borrowed-once',B,"used.add(command.operation);\n      const owner=controlled.get(tab),prior=owner.hold", "const owner=controlled.get(tab),prior=owner.hold",node('background','P1 an uncertain borrowed'))
case('P1-borrowed-origin',B,"dialog.unguarded=true;",'void 0;',node('background','P1 native opening metadata'))
case('P1-borrowed-matched',B,'const matched=!dialog.unguarded&&confirmationPlans','const matched=confirmationPlans',node('background','a stale approved dialog opening'))
case('P1-borrowed-prior-hold',B,'if(completion){const result=await Promise.race','if(false){const result=await Promise.race',node('background','P1 a borrowed answer preserves'))
case('P1-preexisting-bound',B,"if(!preloadTargets.get(targetKey({tabId:tab}))?.pageEnabled)resolve({owner_dialog:true});",'if(false)resolve({owner_dialog:true});',node('background','P1 preexisting modal handoff'))
case('P1-preexisting-detach',B,'await chrome.debugger.detach({tabId:tab});return;','return;',node('background','P1 preexisting modal handoff'))
case('P1-preexisting-retain',B,'if(previous.modalHandoff)return;','',node('background','P1 preexisting modal handoff'))
case('P1-preexisting-recover',B,"if(owner.modalHandoff){await recoverOwnerDialog(tab,owner);if(owner.modalHandoff)throw Error('owner_dialog: '+ownerDialogMessage);}",'',node('background','P1 preexisting modal handoff'))
case('P1-preexisting-slow',B,'if(!preloadTargets.get(targetKey({tabId:tab}))?.pageEnabled)resolve({owner_dialog:true});','if(true)resolve({owner_dialog:true});',node('background','P1 a responding Page domain'))
case('P2',B,'let effective;try { effective=frameAddress(frame,frames);','if(frame.url.startsWith("about:"))continue;let effective;try { effective=frameAddress(frame,frames);',node('background','P2'))
case('P3-inherit',B,'if(hold&&(hold.inFlight||Date.now()<hold.until)){','if(false){',node('background','P3 startup'))
case('P3-paused-task',B,"if(armed.exceptionDetails)throw Error('refused: new frame could not inherit the active hold');", "if(!hold.inFlight)await targetCommand(state,'Runtime.evaluate',{contextId:context.id,expression:'globalThis[Symbol.for(\"aresos.chrome.guard.v2\")].finish('+JSON.stringify(state.epoch)+','+JSON.stringify(hold.nonce)+')',awaitPromise:true});if(armed.exceptionDetails)throw Error('refused: new frame could not inherit the active hold');",node('background','P3 a remaining hold'))
case('P3-coverage',B,'if(armed.some(frame=>frame.frame===added.frame&&frame.document===added.document))continue;','if(true)continue;',node('background','P3 a frame'))
case('P4',M,'return owner===ownDocument||!!(defaultView?invoke(defaultView,owner,[]):owner.defaultView);','return owner===ownDocument;',node('page','P4'))
case('P5',M,"report(result,{kind:'watch_root'});",'',node('page','P5 new roots'))
case('P5-composed',M,'[options({composed:true})]','[options({composed:false})]',node('page','P5 composed root'))
case('P5-native-shadow-identity',M,"property(detail,'target_path',path,true);",'',node('page','P5 native shadow identity'))
case('P5-isolated-node',G,"for(const part of stage.detail.target_path?.split('.')||[])",'for(const part of [])',node('page','P5 native shadow identity'))
case('P6',P,"base_key in {'Delete', 'Backspace'}","key in {'Delete', 'Backspace'}",'test_policy.ReviewClassification.test_p6_equivalent_keys_classify_the_dispatched_tuple',True)
case('P6-adapter','control/aresos_control/chrome/sites.py',"if base_key == '#' and scoped","if key == '#' and scoped",'test_sites.SiteSemantics.test_p6_gmail_hash_shortcut_canonicalizes_modifiers_before_classification',True)
case('P7',G,re.search(r'function decoded\(value\) \{[^\n]+', (ROOT/G).read_text())[0],"function decoded(value) {try{return decodeURIComponent(value)}catch{return value}}",node('page','P7'))
case('P8',P,"unicodedata.normalize('NFC', text)",'text','test_policy.ReviewClassification.test_p7_tolerant_url_decoding_and_p8_canonical_unicode',True)
case('P8-guard',G,"value.normalize('NFC')",'value',node('page','P8'))
case('P9-classification',P,"if evidence in {'delete', 'pay', 'item'}:","if False:",'test_policy.ReviewClassification.test_p9_explicit_payment_and_deletion_override_adapter',True)
case('P9-trusted',A,"if forbidden or mode['conservative']","if mode['conservative']",'test_questions.Questions.test_p9_trusted_predicate_independently_forbids_explicit_deletion_payment_and_whatsapp',True)
case('P10',R,'[role=listitem],[role=row],[role=article],section[aria-label],section[aria-labelledby],','',node('reader','P10'))
case('P11',A,"if generic_draft else None","if kind == 'send' and not frame.get('form') and not adapter else None",'test_questions.Questions.test_p11_confirmation_binds_a_sibling_draft',True)
case('P12',R,"fileIdentities.set(file,{identity:randomToken()})","fileIdentities.set(file,{identity:file.name})",node('reader','P12'))
case('P12-hash',R,"return hash.map(value=>value.toString(16).padStart(8,'0')).join('');","return '0'.repeat(64);",node('reader','P12 HTTP'))
case('P12-rehash',R,'const identity=fileIdentity(file);','const identity=fileIdentity(file);if(identity.sha256)continue;',node('reader','P12 every binding rehashes'))
case('P12-race',R,'if(!unchanged())','if(false)',node('reader','P12 a selection changed'))
case('P12-binding',A,"'fields':item.get('selected_files',[])","'fields':[]",'test_questions.Questions.test_p12_owner_selected_file_question_shows_name_size_and_bound_digest',True)
case('P13',R,"value = editableText(element).replace(/\\n$/, '');","value = text(element);",node('reader','P13'))
case('P14',P,"ITEM = {'unsubscribe', 'abbestellen'}","ITEM = set()",'test_policy.ReviewClassification.test_p14_unsubscribe_binds_item_without_a_draft',True)
case('P15',R,"element.getAttribute('alt') || buttonValue ||","element.getAttribute('alt') || element.getAttribute('title') || buttonValue ||",node('reader','P15'))
case('P16',R,"element.hasAttribute('srcdoc') ? 'about:srcdoc'","element.srcdoc ? 'about:srcdoc'",node('reader','P16'))
case('P17',R,'const {protectedFields,fileIdentities}=privacy;','const protectedFields=new WeakSet(),fileIdentities=privacy.fileIdentities;',node('reader','P17'),extra=[(R,"const protectedKey=Symbol.for('aresos.chrome.password-node.v1');","const protectedKey=Symbol('aresos.chrome.password-node.v1');")])
case('P17-before-getter',R,"if(message.expected_document&&message.expected_document!==documentId)","if(false)",node('reader','P17 lost-history identity'))
case('P17-private-expectation',B,"...(privacyDocuments.has(frame.documentId)?{expected_document:privacyDocuments.get(frame.documentId)}:{})","...{}",node('background','P17 expected privacy identity'))
case('popup-late-reader',B,'if(!error.readerUnavailable||!frame.documentId)throw error;','throw error;',node('background','a popup committing after admission'))
case('popup-reader-document',B,'browserDocument?{documentId:browserDocument}:{frameId:frame}','{frameId:frame}',node('background','document replaced between frame enumeration'))
case('popup-install-document',B,'...(frame.documentId?{documentIds:[frame.documentId]}:{frameIds:[frame.frameId]})','frameIds:[frame.frameId]',node('background','a popup committing after admission'))
case('P2-native-frame',B,"origins=authenticated.length===1?authenticated:inherited?[]:frames.filter(frame=>frame.url===params.url);","origins=frames.filter(frame=>frame.url===params.url);",node('background','P2 native'))
case('P2-native-readonly',A,"facts.get('effective_url',facts['dialog']['frame_url'])","facts['dialog']['frame_url']",'test_questions.Questions.test_p2_inline_native_dialog_uses_authenticated_inherited_readonly_host',True)
case('P2-before-getter',R,"if(message.expected_origin&&message.expected_origin!==globalThis.origin)","if(false)",node('reader','P2 inherited origin'))
case('P18-descendants',R,'node=node.parentElement||node.getRootNode?.().host','node=null',node('reader','P18'))
case('P18-sticky',R,"if(protectedFields.has(element)||Object.getOwnPropertyDescriptor(element,protectedKey)?.value===true)return true;",'if(false)return true;',node('reader','P18'))
case('P19',B,"await targetCommand(state,'Page.enable');","await targetCommand(state,'Page.enable');await targetCommand(state,'Runtime.enable');",node('background','startup evaluates only fixed bundles'),extra=[('control/chrome/extension/policy.js','"Runtime.evaluate"','"Runtime.enable", "Runtime.evaluate"')])
case('P19-root-context',B,'if(params.frame.id===state.frameId){','if(false){',node('background','P19 root navigation'))
case('P19-context-generation',B,"(state.contextGeneration?'-navigation-'+state.contextGeneration:'')","''",node('background','P19 a cancelled startup'))
case('P19-context-check',B,"const documentCommand=async(method,parameters)=>{if(!sameDocument())throw Error('stale_reference: document changed during startup');const value=await targetCommand(state,method,parameters);if(!sameDocument())throw Error('stale_reference: document changed during startup');return value;};","const documentCommand=(method,parameters)=>targetCommand(state,method,parameters);",node('background','P19 a cancelled startup'))
case('P20-form',G,'||owner.form!==form','',node('page','P20 synchronous'))
case('P20-submitter',G,'||owner.submitter!==(submitter||null)','',node('page','P20 synchronous'))
case('P20-trust',G,'if(!event.isTrusted||inFlight)return;','if(inFlight)return;',node('page','P20 an untrusted'),extra=[(G,'||!owner.event.isTrusted','')])
case('P20-clear',G,'if(owner?.token===event.data)owner=null;','',node('page','P20 an unconsumed'))
case('P21',P,"if form and form.get('search') and form.get('method', '').lower() == 'get':","if False and form and form.get('search') and form.get('method', '').lower() == 'get':",'test_policy.ReviewClassification.test_p21_get_search_form_enter_in_ordinary_input',True)
case('P22-title-action',A,"'title':facts.get('title', '')","'title':''",'test_questions.Questions.test_p22_delete_question_names_the_action_key_item_and_bound_title',True)
case('P22-action',A,"'delete':'delete'","'delete':'activate'",'test_questions.Questions.test_p22_delete_question_names_the_action_key_item_and_bound_title',True)
case('P22-bounds',A,'return value if len(visible(value))<=120 else','return value if True else','test_questions.Questions.test_p22_many_recipients_and_long_names_are_bounded_without_losing_full_values',True)
case('P23',B,'page:await observation(tab,reference,dispatchEpoch)',"page:'Input dispatched once'",node('background','P23'))
case('P23-borrowed-dialog',B,'page:await observation(tab)}',"page:{available:true,url:current.url,notice:'Native answer dispatched'}}",node('background','P23 a borrowed dialog result'))
case('P24-last-check',B,'if(requireClean){','if(false){',node('background','P24'))
case('P24-audible',B,'playing=!!nativeTab.audible','playing=false',node('background','P24'),extra=[(B,"playing=!!(await chrome.tabs.get(tab)).audible","playing=false")])
case('P24-uncovered',B,'unsaved=!!current.uncovered?.length','unsaved=false',node('background','P24 uncovered'))
case('P24-unreadable',B,'catch{unsaved=true;}','catch{}',node('background','P24 uncovered'))
case('P24-designmode',R,"document.designMode?.toLowerCase()==='on'",'false',node('reader','P24 document'))
case('P25',B,"if(needsNative){","if(command.name==='input'){",node('background','P25'))
case('P25-report',B,'dispatched:!noChange,no_change:noChange','dispatched:true,no_change:false',node('background','P25'))
case('P26',M,'const value=({method(...args){return invoke(implementation,this,args);}}).method;','const value=implementation;',node('page','P26'))
case('P27',B,'tabIds=[...controlled.keys()]','tabIds=[...controlled.keys(),...releasing.keys()]',node('background','P27'))
case('P27-missing-context',B,"const gone=String(error).includes('Cannot find context with specified id');",'const gone=false;',node('background','P27 native missing-context'))
case('P27-unknown-context',B,"const gone=String(error).includes('Cannot find context with specified id');",'const gone=true;',node('background','P27 native missing-context'))
case('P28',B,'owner.uncertainFinish=await finishFrames(tab,armed,dispatchEpoch,inputNonce);','owner.uncertainFinish=false;',node('background','P28'))
V='control/chrome/ci/verdicts.mjs'
case('P29',V,'export function assertComplete(results,qualified){','export function assertComplete(results,qualified){return;',node('verdicts','P29'))
case('P30', 'control/chrome/ci/ingress-scan.mjs',"const result=[];let pending=null;","return text.split('\\n').filter(Boolean).map(JSON.parse);const result=[];let pending=null;",node('ingress-scan','P30'))
case('P30-getters','control/chrome/ci/password-ingress.js','get(){return emit(key,get.call(this));}','get(){return get.call(this);}',node('password-ingress','P30'))
case('P30-null-ingress','control/chrome/ci/ingress-scan.mjs','rows.filter(row=>row?.protocol_event)','rows.filter(row=>row.protocol_event)',node('ingress-scan','P30 protocol'))
case('P31-popup',B,'popupNeedsReload:true','popupNeedsReload:false',node('background','P31'))
F='control/chrome/ci/fixture.mjs'
case('combined-S12-review-dialog','control/chrome/ci/review-matrices.mjs',"(await call('read',{tab:getTab()})).untrusted_content.dialog","(await call('read',{tab:getTab()})).dialog",node('fixture','combined S12 native-dialog'))
case('P31-http',F,"else if(kind==='adapter-sites')","if(kind==='adapter-sites')",node('fixture','review pages reach'))
case('P31-head',F,'globalThis.firstScriptSubmit=HTMLFormElement.prototype.submit;','',node('fixture','P31 first script'))
case('P31-get-case',F,'target="_blank"><input type="hidden" name="case" value="\'+id+\'"><input type="search"','target="_blank"><input type="search"',node('fixture','P31 first script'))

case('recheck-search-activation',G,"if (!target.editable && explicit(target,form)) return true;","if(form&&target.submit)return false;",node('page','recheck search labels'))
case('recheck-search-submissions',G,"if(explicit(element?facts(element):null,form)||(form.fields||[]).some(field=>['submit','image'].includes(field.type)&&explicit(field,null)))return false;",'',node('page','recheck search labels'))
case('recheck-item-shadow',R,'node=composedParent(node)','node=node.parentElement',node('reader','recheck affected items'))
case('recheck-item-composed-text',R,'text(affectedItem(element),false,true)','text(affectedItem(element))',node('reader','recheck affected items'))
case('recheck-confirmation-service',A,"kind == 'confirmation' or kind == 'send' and not frame.get('form')","kind in {'confirmation','send'} and not frame.get('form')",'test_questions.Questions.test_recheck_confirmation_form_binds_changed_outside_draft_and_complete_coverage',True)
case('recheck-confirmation-submitter',P,"if evidence and target.get('page_dialog')","if False and evidence and target.get('page_dialog')",'test_questions.Questions.test_recheck_confirmation_form_binds_changed_outside_draft_and_complete_coverage',True)
case('recheck-confirmation-extension',B,"kind==='confirmation'||kind==='send'&&!frame.form","['confirmation','send'].includes(kind)&&!frame.form",node('background','recheck confirmation form'))
case('recheck-shadow-composed',G,'if(nodeRoot!==document){watch(nodeRoot);return;}','if(nodeRoot!==document)return;',node('page','recheck composed native roots'))
case('recheck-shadow-native-insertion',M,"[globalThis.DocumentFragment?.prototype,['append','prepend','replaceChildren']]","[globalThis.DocumentFragment?.prototype,[]]",node('page','recheck native roots'),extra=[(M,"[globalThis.Node?.prototype,['appendChild','insertBefore','replaceChild']]","[globalThis.Node?.prototype,[]]")])
case('recheck-shadow-native-listener',M,re.search(r"  install\(EventTarget.prototype,'addEventListener',function\(\)\{[\s\S]*?\n  \}\);",(ROOT/M).read_text())[0],'',node('page','recheck native roots'))
case('recheck-shadow-native-markup',M,'set innerHTML(html){watchReceiver(this);invoke(method,this,[html]);}','set innerHTML(html){invoke(method,this,[html]);}',node('page','recheck native roots'))
case('recheck-shadow-host',G,'if(shadow)watch(shadow);','if(shadow){watch(shadow);return;}',node('page','recheck a shadow host'))
case('recheck-search-service',P,"form.get('method','').lower()=='get' and not evidence","form.get('method','').lower()=='get'",'test_policy.RecheckSearch.test_explicit_search_submitters_ask_and_ordinary_search_stays_free',True)
case('recheck-shadow-setter-cleanup',M,"key=item.setter?'set':'value'","key='value'",node('page','recheck native roots'))
case('recheck-shadow-page-getter',M,'item.setter?options({...current,set:item.previous.set}):item.previous','item.previous',node('page','recheck native roots'))
case('recheck-owner-overlap-oracle','control/chrome/ci/owner-evidence.mjs',"assert(set.time<=timer.time&&timer.time<=held.time&&held.time<=ended.time,'the real timer fires inside the private mark interval');",'',node('owner-evidence','recheck owner evidence'))
case('recheck-owner-pass-oracle','control/chrome/ci/owner-evidence.mjs',"assert(entering&&pass&&passSet,'the immediate native owner submission must consume its private input allowance');",'',node('owner-evidence','recheck owner evidence'))
O='control/chrome/ci/owner-evidence.mjs'
case('recheck-owner-enter-observation',O,'assert(entering&&pass&&passSet,','assert(pass&&passSet,',node('owner-evidence','recheck owner evidence'))
case('recheck-owner-pass-observation',O,'assert(entering&&pass&&passSet,','assert(entering&&pass,',node('owner-evidence','recheck owner evidence'))
case('recheck-owner-held-key',O,"row.phase==='held'&&row.key==='Enter'&&!row.in_flight","row.phase==='held'&&!row.in_flight",node('owner-evidence','recheck owner evidence'))
case('recheck-owner-held-flight',O,"row.phase==='held'&&row.key==='Enter'&&!row.in_flight","row.phase==='held'&&row.key==='Enter'",node('owner-evidence','recheck owner evidence'))
case('recheck-owner-consumed',O,"row.phase==='pass'&&row.consumed===true","row.phase==='pass'",node('owner-evidence','recheck owner evidence'))
case('recheck-owner-pass-token',O,"row.token===pass.token&&row.input===pass.input","row.input===pass.input",node('owner-evidence','recheck owner evidence'))
case('recheck-search-query-content',P,"if k != 'value' or not target.get('editable')",'', 'test_policy.RecheckSearch.test_explicit_search_submitters_ask_and_ordinary_search_stays_free',True)
case('recheck-compose-draft-content',P,"if k != 'value' or not target.get('editable')",'', 'test_questions.Questions.test_recheck_editable_payment_words_keep_the_complete_send_draft_binding',True)
case('recheck-item-closed-slots',R,'const assignedRoot=shadow(element.parentElement);','const assignedRoot=null;',node('reader','recheck slotted affected items'))
case('recheck-editable-controls',R,'editable: !clickControl && (','editable: (',node('reader','recheck editable asking controls'))
case('recheck-item-fields-reader',R,'item_fields:element?itemFields(element,nodes):[]','item_fields:[]',node('reader','recheck item quantities'))
case('recheck-item-fields-extension',B,"item_fields:['delete','pay','item','activation','confirmation'].includes(kind) ? frame.item_fields||[] : null,",'',node('background','recheck payment dispatch'))
case('recheck-item-fields-service',A,"'item_fields':frame.get('item_fields',[]) if kind in {'delete','pay','item','activation','confirmation'} else None,",'','test_questions.Questions.test_recheck_payment_quantity_is_shown_and_bound',True)
case('recheck-post-page-barrier','control/chrome/ci/review-fixtures.mjs',"script=variant==='after-owner-navigation'?","script=false?",node('fixture','recheck script POST timer'))
case('recheck-post-driver-barrier','control/chrome/ci/review-matrices.mjs',"await fixture.mutate(id,'review-change');await eventually(()=>counts(id)===1,'script POST');","await eventually(()=>counts(id)===1,'script POST');",node('fixture','recheck script POST observes'))
case('recheck-post-document-commit','control/chrome/ci/review-matrices.mjs',"await eventually(async()=>(await allTabs(call)).items.some(row=>row.tab===tab&&row.url==='http://fixture.test:8765/post-document?case='+id),'script POST committed in the exact owner tab');",'',node('fixture','recheck script POST observes'))

case('recheck2-native-created-capture',M,"report(node,{kind:'watch_node'});return node;}","return node;}",node('page','recheck2 native insertion'))
case('recheck2-native-target-capture',G,'nodeRoot!==root&&root!==element','nodeRoot!==root',node('page','recheck2 native insertion'))
case('recheck2-default-neutralization',G,'event.cancelable||stopDefault(element)','event.cancelable',node('page','recheck2 uncancellable defaults'))
case('recheck2-owner-navigation',G,'if(!inFlight&&event.isTrusted&&owner?.event===event&&!owner.consumed)return;','',node('page','recheck2 the owners trusted click'))
case('recheck2-network-rule',B,'if(heldTabs.length)addRules.push','if(false)addRules.push',node('background','recheck2 session default blocks'))
case('recheck2-network-expiry',B,'networkHolds.delete(tab);rules().catch(()=>{});','rules().catch(()=>{});',node('background','recheck2 session default blocks'))
case('recheck2-network-restart',B,'removeRuleIds:previous.map(rule=>rule.id),addRules','removeRuleIds:[],addRules',node('background','recheck2 startup reconciles'))
case('recheck2-network-release',B,'record.promise=(async()=>{\n    await rules();','record.promise=(async()=>{',node('background','recheck2 release removes'))
case('recheck2-compose-reader',R,'compose:element?composeText(element,nodes):null','compose:null',node('reader','recheck2 compose text'))
case('recheck2-compose-service',A,"'compose':frame.get('compose') if not adapter and kind in {'send','confirmation','form'} else None,","'compose':None,",'test_questions.Questions.test_recheck2_changed_compose_reasks_with_exact_change_once_then_sends_once',True)
case('recheck2-compose-reask',A,"if fresh.get('compose')!=state.get('compose'):","if False:",'test_questions.Questions.test_recheck2_changed_compose_reasks_with_exact_change_once_then_sends_once',True)
case('recheck2-compose-bounded',A,"if payload.get('compose_reasked'):return result","if False:return result",'test_questions.Questions.test_recheck2_compose_second_change_stops_and_tells_owner_without_an_ask_loop',True)
case('recheck2-compose-change-shown',A,"summary += f\"; text next to Send changed from '{changed['before']}' to '{changed['after']}'\"","summary += '; text changed'",'test_questions.Questions.test_recheck2_changed_compose_reasks_with_exact_change_once_then_sends_once',True)

case('recheck2-markup-handler',M,'set onclick(handler){watchCreated(this);invoke(method,this,[handler]);}','set onclick(handler){invoke(method,this,[handler]);}',node('page','recheck2 native markup'))
case('recheck2-single-capture',G,'if(capturedBefore(event,root))return;','',node('page','recheck2 node and ancestor'))
case('recheck2-compose-extension',B,"compose:!adapter&&['send','confirmation','form'].includes(kind)?frame.compose||null:null,",'compose:null,',node('background','recheck2 final extension binding'))
case('recheck2-compose-final-boundary',A,"if exc.code=='stale_approval' and not payload.get('native_dialog'):",'if False:','test_questions.Questions.test_recheck2_preview_changed_at_extension_boundary_reasks_without_dispatch',True)

case('recheck2-engine-reask','control/aresos_control/engine.py','if isinstance(replacement, dict):','if False:','test_questions.Questions.test_recheck2_changed_compose_reasks_with_exact_change_once_then_sends_once',True)
case('recheck2-engine-boundary-reask','control/aresos_control/engine.py',"replacement = getattr(exc, 'replacement', None)",'replacement = None','test_questions.Questions.test_recheck2_preview_changed_at_extension_boundary_reasks_without_dispatch',True)

case('recheck2-event-reuse',G,'if(capturedBefore(event,root))return;','if(captured.has(event))return;',node('page','recheck2 reusing a native Event'))

case('recheck2-slot-dedup-scope',G,'    if(capturedBefore(event,root))return;','',node('page','recheck2 irrelevant slot capture'),extra=[(G,'  function captureInput(event,root) {','  function captureInput(event,root) {\n    if(capturedBefore(event,root))return;')])

case('recheck2-clone-native-kinds',M,'if(kind===2||kind===10)return node;','',node('page','recheck2 clone hooks'))
case('recheck2-cached-factory',M,'function watchCreated(node){if(!enabled)return node;','function watchCreated(node){',node('page','recheck2 cached creation'))
case('recheck2b-activation-baseline','control/chrome/ci/activation-evidence.mjs',"assert.equal(row.alone.before.active,false,'baseline must have no transient activation');",'',node('activation-evidence','activated baseline'))
case('recheck2b-activation-receipt','control/chrome/ci/activation-evidence.mjs','assert.deepEqual(JSON.parse(receipt[0].body),{cause,before:observation.before,atHandler:observation.atHandler,trusted:false});','',node('activation-evidence','forged receipt'))

case('recheck2b-pending-clipboard','control/chrome/ci/activation-evidence.mjs',"outcome:'pending browser permission',error:null","outcome:'write accepted',error:null",node('activation-evidence','capability measurement'))

case('recheck2b-picker-leave-chooser','control/chrome/ci/compatibility.mjs','if(active===picker.window)return false;','',node('compatibility','native picker dismissal'))
case('recheck2b-picker-browser-focus','control/chrome/ci/compatibility.mjs','return windows.includes(active);','return true;',node('compatibility','native picker dismissal'))

case('recheck2c-clipboard-write',M,"for(const name of ['write','writeText'])","for(const name of ['writeText'])",node('page','2c Clipboard write reports'))
case('recheck2c-clipboard-writeText',M,"for(const name of ['write','writeText'])","for(const name of ['write'])",node('page','2c Clipboard writeText reports'))
case('recheck2c-copy-event',G,"listen('copy',event=>{try{if(event.isTrusted&&nativeRoot.call(event.composedPath()[0],{composed:true})===ownDocument)noteClipboard('copy');}catch{}},true);",'',node('page','2c trusted copy events'))
case('recheck2c-copy-trust',G,"event.isTrusted&&nativeRoot.call(event.composedPath()[0],{composed:true})===ownDocument","nativeRoot.call(event.composedPath()[0],{composed:true})===ownDocument",node('page','2c forged copy events'))
case('recheck2c-copy-document',G,"&&nativeRoot.call(event.composedPath()[0],{composed:true})===ownDocument",'',node('page','2c a watched node adopted'))
case('recheck2c-clipboard-reader',R,'...(clipboard?{clipboard}:{})','...{}',node('reader','2c post-input observations'))
case('recheck2c-clipboard-navigation',B,'owner.clipboardRoutes.add(message.route);','',node('background','2c private clipboard facts'))
case('recheck2c-clipboard-post-input',B,'return finish({available:false,url:current.url','return ({available:false,url:current.url',node('background','2c private clipboard facts'))
case('recheck2c-clipboard-route',B,"!['write','writeText','copy'].includes(message.route)",'false',node('background','2c clipboard messages'))
case('recheck2c-clipboard-description','control/aresos_control/chrome/definitions.py',"CLIPBOARD_NOTICE = ('If a click result says the page wrote to the clipboard, tell the owner. '", "CLIPBOARD_NOTICE = ('A clipboard write needs no report. '",'test_policy.ClipboardDescriptions.test_2c_click_descriptions_warn_without_changing_the_liftable_shared_block',True)
case('recheck2c-owner-exact-url','control/chrome/ci/owner-ui.mjs',"exec('xdotool',['key','--clearmodifiers','Delete']);",'',node('owner-ui','owner navigation deletes an inline history'))
case('recheck2b-transport-reset','control/boundary/hostile.py',', errno.ECONNRESET','', 'control.tests.test_boundary_host_transport.HostTransport.test_reset_and_timeout_are_unqualified_not_policy_denials',True)


case('recheck3-detached-listener',M,'if(node)watchCreated(this);','',node('page','recheck3 every wrapped native mix'))
case('recheck3-node-brand',M,'let node=false;try{invoke(root,this,[]);node=true;}catch{}','let node=this instanceof Node;',node('page','recheck3 detached listener branding'))
case('recheck3-foreign-node',M,"if(control!==privateControl)property(detail,'source_id',relayValue,true);",'',node('page','wrapped detached listener from another'))
case('recheck3-foreign-document-lookup',G,'if(source)source.enabled=true;','',node('page','wrapped detached listener from another'))
case('recheck3-foreign-document-reference',M,"    invoke(mapSet,foreignCarriers,[doc,{node,control,key,value}]);return true;","    return true;",node('page','wrapped detached listener from another'))
case('recheck3-foreign-document-release',G,"for(const [root,listeners] of watchedRoots())for(const [kind,listener,capture]of listeners)root.removeEventListener(kind,listener,capture);",'',node('page','foreign watch bridges and recipient capture'))
case('recheck3-svg-capture',G,'const shadow=html(element,HTMLElement)&&globalThis.chrome?.dom?.openOrClosedShadowRoot(element);','const shadow=globalThis.chrome?.dom?.openOrClosedShadowRoot(element);',node('page','recheck3 every hyperlink'))
case('recheck3-area-default',G,"['A','AREA'].includes(element.tagName)","['A'].includes(element.tagName)",node('page','recheck3 every hyperlink'))
case('recheck3-svg-default',G,"element.namespaceURI==='http://www.w3.org/2000/svg'&&element.localName==='a'","false",node('page','recheck3 every hyperlink'))
case('recheck3-svg-legacy-default',G,"if(legacy!==null)removeAttributeNS.call(node,xlink,'href');",'',node('page','recheck3 every hyperlink'))
case('recheck3-image-default',G,"['submit','image','reset'].includes(element.type)","['submit','reset'].includes(element.type)",node('page','recheck3 native submitters'))
case('recheck3-unknown-default',G,"if(!hyperlink&&node.tagName!=='FORM')return false;","if(!hyperlink&&node.tagName!=='FORM')return true;",node('page','recheck3 unrecognised defaults'))
case('recheck3-rendered-compose',R,'const content=renderedCompose(area);',"const content=text(area,false,true).replace(/\\s+/g,' ').trim();",node('reader','recheck3 compose preserves'))
case('recheck3-pre-modes',R,"['pre','pre-wrap','break-spaces','preserve'].includes(space)","['pre'].includes(space)",node('reader','recheck3 compose preserves'))
case('recheck3-pre-line',R,"space==='pre-line'&&part.includes('\\n')","false",node('reader','recheck3 compose preserves'))
case('recheck3-trailing-newline',R,"(pending==='\\n'||!result.endsWith('\\n'))","!result.endsWith('\\n')",node('reader','recheck3 leading pre-line'))
case('recheck3-leading-pre-line',R,"if(pending==='\\n')flush();",'',node('reader','recheck3 leading pre-line'))
case('recheck3-leading-br',R,"if(node.tagName==='BR'){if(visible){if(pending==='\\n')flush();","if(node.tagName==='BR'){if(visible){",node('reader','recheck3 leading pre-line'))
case('recheck3-visible-descendant',R,"if(style.display==='none')return;","if(style.display==='none'||style.visibility==='hidden')return;",node('reader','recheck3 significant visible descendant'))
case('recheck3-visible-hidden-attribute',R,"if(style.display==='none')return;","if(node.hidden||style.display==='none')return;",node('reader','recheck3 compose preserves rendered indentation'))
case('recheck3-compose-question',A,"if state.get('compose') is not None and not changed:","if False:",'test_questions.Questions.test_recheck3_whitespace_only_changes_keep_exact_questions_and_bounded_bindings',True)
case('recheck3-compose-extension',B,"compose:!adapter&&['send','confirmation','form'].includes(kind)?frame.compose||null:null,",'compose:null,',node('background','recheck3 final extension binding'))

case('recheck3-private-carrier-brand',M,'invoke(getAttribute,node,[key])!==value','false',node('page','private foreign links reject'))
case('recheck3-private-carrier-retirement',M,'if(relayKey&&privateRelay)invoke(removeAttribute,privateRelay,[relayKey]);','',node('page','private foreign links reject'))
case('recheck3-private-source-hold',G,"const candidate=source?source.privateHold():{...config,conservative:true,holdMs:config?.holdMs||500,defaultBlock:config?.defaultBlock||'https://aresos-hold.invalid/'};",'const candidate=null;',node('page','wrapped detached listener from another'))
case('recheck3-private-native-context',B,'state.factoryContexts.set(params.executionContextAuxData.frameId,params.executionContextId)','void 0',node('background','native MAIN context observed'))
case('recheck3-passive-carrier-retirement',G,'if(relayNode&&relayMarker)removeAttribute.call(relayNode,relayMarker);','',node('page','passive controlled recipient'))
case('recheck3-conservative-recipient',G,'candidate.conservative||combined?.conservative','candidate.conservative',node('page','already conservative recipient'))

case('recheck3-adopted-element-brand',G,"const isElement=node=>{try{elementAttribute.call(node,'');return true;}catch{return false;}};",'const isElement=node=>node instanceof Element;',node('page','native adoption into a third'))
case('recheck3-adopted-field-brand',R,"||isElement(node)&&node.namespaceURI==='http://www.w3.org/1999/xhtml'&&(!tag||node.localName===tag)",'',node('reader','adopted HTML controls'))
case('recheck3-peer-password',R,'if(guard.protectedPeer?.(element))protectNode(element);','',node('reader','adopted peer password provenance'))
case('recheck3-retired-peer-password',G,'return privacyCheck?.(node)===true;','return reader?.protected?.(node)===true;',node('page','retired peer metadata'))

case('recheck3-adopted-password-marker',R,'Object.defineProperty(node,protectedKey,{value:true});','void 0;',node('reader','adopted peer password provenance'))

case('recheck3-main-data-clone',M,"property(detail,'source_id',relayValue,true)","property(detail,'source_id',()=>relayValue,true)",node('page','wrapped detached listener from another'))

case('recheck3-paused-peer-setup',G,'api:null,enabled:false',"api:(()=>{const detail={};native.dispatch.call(node.firstElementChild,new CustomEvent('aresos-relay-guard',{detail}));if(!detail.api)throw Error('peer unavailable while paused');return detail.api;})(),enabled:false",node('page','peer setup survives suppressed DOM callbacks'))

case('recheck3-unavailable-private-peer',G,"else if(hold){if(event.cancelable)event.preventDefault();event.stopImmediatePropagation();report('activation_unknown',element,null,event.cancelable);}",'',node('page','unavailable recipient private guard'))

case('recheck3-conservative-adopted-recipient',G,'inheritedCapture.config.conservative||combined?.conservative','inheritedCapture.config.conservative',node('page','adopted capture preserves its conservative recipient'))

case('recheck3-passive-cleanup-ack',G,'if(relayMain)restored=!native.dispatch.call','restored=!native.dispatch.call',node('page','passive controlled recipient'))


for source in ['a','area','svg-href','svg-xlink']:
    before={
        'a':"if(element.tagName==='A'&&anchorHref)return anchorHref.call(element);",
        'area':"if(element.tagName==='AREA'&&areaHref)return areaHref.call(element);",
        'svg-href':"new URL(address,baseURI(element)).href",
        'svg-xlink':"new URL(address,baseURI(element)).href",
    }[source]
    after="return new URL(element.getAttribute('href'),location.href).href;" if source in ['a','area'] else "new URL(address,location.href).href"
    case('post18d-'+source,R,before,after,node('reader','post18d destination '+source+' follows'))
for source in ['form-action','button-formaction','input-formaction']:
    before="action: button?.hasAttribute('formaction') ? button.formAction : formProperty(form,'action'),"
    after="action: new URL('delete',location.href).href,"
    case('post18d-'+source,R,before,after,node('reader','post18d destination '+source+' uses'))
case('post18d-target',R,"const fallback=base?.getAttribute('target')||'_self';","const fallback='_self';",node('reader','post18d destination target and formtarget'))
case('post18d-formtarget',R,"browsingTarget(button,'formtarget')","'_self'",node('reader','post18d destination target and formtarget'))
case('post18d-destination-service',A,"if destination(fresh)!=destination(state):","if False:",'test_questions.Questions.test_post18d_destination_changes_reask_before_input_and_on_final_refusal',True)
case('post18d-destination-final',A,"if destination(fresh)!=destination(payload['binding']):","if False:",'test_questions.Questions.test_post18d_destination_changes_reask_before_input_and_on_final_refusal',True)

case('post18d-target-service-binding',A,"'href','browsing_target','value'","'href','value'",'test_questions.Questions.test_post18d_destination_changes_reask_before_input_and_on_final_refusal',True)
case('post18d-target-extension-binding',B,"'href','browsing_target','value'","'href','value'",node('background','post18d final destination binding'))


for signal in ['name','id','autocomplete','aria-label','placeholder']:
    before="['name','id','autocomplete','aria-label','placeholder']"
    after=repr([key for key in ['name','id','autocomplete','aria-label','placeholder'] if key!=signal])
    case('post18d-credential-'+signal,R,before,after,node('reader','post18d credential signal '+signal+' excludes'))
case('post18d-credential-label',R,"signals.push([...element.labels||[]].map(labelText).join(' '));",'',node('reader','post18d credential signal label excludes'))
case('post18d-late-mask',R,"if(!watched&&typedField(element))","if(false&&typedField(element))",node('reader','post18d late single-line values'))
for kind in ['text','tel','number','unknown','email','url','search']:
    case('post18d-late-type-'+kind,R,"html(element,HTMLInputElement,'input')&&!['hidden'",f"html(element,HTMLInputElement,'input')&&element.type!={kind!r}&&!['hidden'",node('reader','post18d late single-line values'))
case('post18d-watch-provenance',B,'globalThis[Symbol.for("aresos.chrome.document-start.v1")]=true;','',node('background','startup evaluates only fixed bundles'))
case('post18d-read-approval',R,'message.approved!==true||','',node('reader','post18d typed read approval is one call'))
case('post18d-read-replay',R,'||typedReads.has(message.operation)','',node('reader','post18d typed read approval is one call'))
case('post18d-read-credential-scope',R,'typedField(element)&&!password(element)','typedField(element)',node('reader','post18d typed read approval is one call'))
case('post18d-read-unlabelled',R,"name(element)||(html(element,HTMLTextAreaElement,'textarea')?'textarea ':'single-line field ')+(index+1)","name(element)",node('reader','post18d typed read approval is one call'))
case('post18d-read-list',R,"current.fields.some((field,index)=>['element','label','type'].some(key=>field[key]!==expected.fields[index][key]))",'false',node('reader','post18d typed field additions relabelling'))
case('post18d-read-service',A,"if operation['payload'].get('read_connection')!=self.bridge.connection_identity or self.typed_binding(operation['payload']['binding']['tab'])!=operation['payload']['binding']:",'if False:','test_questions.Questions.test_post18d_typed_field_list_change_reasks_at_service_and_final_extension',True)
case('post18d-read-final',B,'if(stable(current)!==stable(command.binding))','if(false)',node('background','post18d typed reads require approval'))
case('post18d-read-once-background',B,"||used.has(command.operation))throw Error('refused: typed fields", ")throw Error('refused: typed fields",node('background','post18d typed reads require approval'))


for kind in ['checkbox','radio','date','datetime-local','month','week','time','range','color']:
    before=next(line.strip() for line in (ROOT/R).read_text().splitlines() if line.strip().startswith("return html(element,HTMLTextAreaElement,'textarea')||html(element,HTMLInputElement,'input')&&!['hidden'"))
    case('post18d-readable-type-'+kind,R,before,before.replace(repr(kind)+',',''),node('reader','post18d watched input types and late choices'))
for kind in ['email','url','search']:
    case('post18d-readable-type-'+kind,R,'else value = element.value;',f'else if(element.type!={kind!r}) value = element.value;',node('reader','post18d watched input types and late choices'))
case('post18d-readable-textarea',R,"html(element,HTMLTextAreaElement,'textarea') || html(element,HTMLSelectElement,'select') || html(element,HTMLButtonElement,'button')) value", "html(element,HTMLSelectElement,'select') || html(element,HTMLButtonElement,'button')) value",node('reader','post18d watched input types and late choices'))
case('post18d-readable-editor',R,"else if (element.isContentEditable) value = editableText(element)","else if (false) value = editableText(element)",node('reader','post18d watched input types and late choices'))
case('post18d-credential-mask',R,"getComputedStyle(element).webkitTextSecurity !== 'none'",'false',node('reader','group7 protected values never reach'))
case('post18d-late-reload-privacy',R,"if(!watched&&(typedField(element)||html(element,HTMLInputElement,'input')&&element.type==='hidden')){unsaved=true;continue;}",'',node('reader','post18d late reload warning never extracts'))

case('post18d-credential-aria-labelledby',R,"signals.push(referenced.map(labelText).join(' '));",'',node('reader','post18d credential aria-labelledby labels'))

case('post18d-credential-combined-labels',R,"signals.push([...element.labels||[]].map(labelText).join(' '));","signals.push(...[...element.labels||[]].map(labelText));",node('reader','post18d combined associated credential labels'))

for source in ['href','xlink:href']:
    case('post18d-svg-animated-'+source,R,"svgHref&&animatedValue?animatedValue.call(svgHref.call(element)):",'',node('reader','post18d SVG animated '+source+' is the native destination'))
case('post18d-svg-animated-target',R,"if(attribute==='target'&&svgLink(element))return svgTarget&&animatedValue?animatedValue.call(svgTarget.call(element))||'_self':explicit||'_self';",'',node('reader','post18d SVG animated target uses the native'))

case('post18d-svg-empty-target',R,"if(attribute==='target'&&svgLink(element))return svgTarget&&animatedValue?animatedValue.call(svgTarget.call(element))||'_self':explicit||'_self';",'',node('reader','post18d SVG empty native target stays self'))

for source in ['href','xlink:href']:
    case('post18d-svg-native-default-'+source,G,"const animations=hyperlink?stopSVGAnimations(node):[];","const animations=[];",node('page','post18d uncancellable SVG '+source+' animation loses native authority'))
case('post18d-svg-native-target-default',G,"if(target!==node)continue;","if(target!==node||getAttribute.call(animation,'attributeName')==='target')continue;",node('page','post18d SVG quarantine covers external target animations'))

case('post18d-native-default-reentry',G,"const earlier=quarantined.get(node),blockedAddress=config.defaultBlock;","if(quarantined.has(node))return true;const earlier=quarantined.get(node),blockedAddress=config.defaultBlock;",node('page','post18d repeated native activation rechecks authority'))

case('post18d-native-query-clobber',G,"for(const animation of animationElements(root))","for(const animation of root.querySelectorAll?.('animate,set,animateTransform,animateMotion')||[])",node('page','post18d SVG scan uses native queries'))
for change in ['retarget','detach']:
    case('post18d-animation-restore-'+change,G,"for(const item of earlier?.animations||[])if(!animations.some(([node])=>node===item[0]))animations.push(item);",'',node('page','post18d reentry retains restoration for an animation the page '+change))

case('post18df-textarea-history',R,"return html(element,HTMLTextAreaElement,'textarea')||html(element,HTMLInputElement", "return html(element,HTMLInputElement",node('reader','post18df late textareas withhold values'))
case('post18df-reader-instance',R,'expected.reader!==readerInstance||','',node('reader','post18df reader instance replacement refuses'))
case('post18df-element-identity',R,"['element','label','type'].some(key=>field[key]!==expected.fields[index][key])","['label','type'].some(key=>field[key]!==expected.fields[index][key])",node('reader','post18df exact element identities distinguish'))
case('post18df-metadata-only',B,'const snapshot=await facts(tab,null,true);','const snapshot=await facts(tab);',node('background','post18df asking preparation uses value-free'))
case('post18df-frame-reader',B,'reader:frame.typed_fields.reader,','',node('background','post18df asking preparation uses value-free'))
case('post18df-native-frame',B,'browser_document:frame.browser_document,reader:frame.typed_fields.reader,','reader:frame.typed_fields.reader,',node('background','post18df asking preparation uses value-free'))
case('post18df-connection-identity','control/aresos_control/chrome/bridge.py','self.connection_identity = uuid.uuid4().hex','self.connection_identity = self.session','test_bridge.Handshake.test_post18df_reconnecting_the_same_browser_session_changes_private_connection_identity',True)
case('post18df-connection-before-read',A,"operation['payload'].get('read_connection')!=self.bridge.connection_identity or ",'','test_questions.Questions.test_post18df_connection_frame_reader_and_element_identity_changes_retire_approval',True)
case('post18df-connection-final',A,"if payload.get('read_connection')!=self.bridge.connection_identity:raise NothingLeft('The prepared browser connection changed; prepare a fresh read.')",'','test_questions.Questions.test_post18df_connection_change_after_revalidation_cannot_read_values',True)
case('post18df-withheld-form-prepare',A,"if any(field.get('unknown_history') for field in (state.get('form') or {}).get('fields',[])):",'if False:','test_questions.Questions.test_post18df_form_with_withheld_values_refuses_before_reload_or_preparation',True)
case('post18df-withheld-form-wait',A,'refuse_withheld_form(fresh)','pass','test_questions.Questions.test_post18df_form_added_withheld_field_and_changed_value_cannot_use_waiting_approval',True)
case('post18df-withheld-form-final',B,"if((command.kind||command.name==='resume'||submitting)&&frame?.form?.fields.some(field=>field.unknown_history))",'if(false)',node('background','post18df final native boundary refuses forms'))

def command(row):
    if row['python']:return ['python3','-B','-m','unittest',row['test'],'-v']
    file,pattern=row['test']
    return ['node','--test','--test-name-pattern',pattern,f'control/chrome_tests/{file}.test.mjs']

def run():
    records=[]
    with tempfile.TemporaryDirectory(dir=WORK) as temporary:
        target=Path(temporary)
        shutil.copytree(ROOT/'control',target/'control',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        (target/'.work/20-chrome').mkdir(parents=True)
        environment={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(target/'control')+':'+str(target/'control/chrome_tests')}
        baselines={}
        for row in CASES:
            key=tuple(command(row))
            if key not in baselines:
                original=subprocess.run(key,cwd=target,env=environment,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60)
                if original.returncode:raise RuntimeError('Baseline failed '+row['item']+'\n'+original.stdout)
                baselines[key]=True
            originals={}
            try:
                for file,before,after in row['edits']:
                    path=target/file
                    source=path.read_text();originals.setdefault(path,source)
                    if before not in source:raise RuntimeError('Mutation does not apply '+row['item']+' '+file)
                    path.write_text(source.replace(before,after,1))
                changed=subprocess.run(key,cwd=target,env=environment,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60)
                killed=changed.returncode!=0 and ('AssertionError' in changed.stdout or 'FAIL:' in changed.stdout or 'not ok' in changed.stdout or '✖' in changed.stdout)
                records.append({'item':row['item'],'baseline':'pass','mutation_failed':killed,'command':list(key),'output':changed.stdout.replace(str(target),'<mutation-worktree>')})
                print(row['item'], 'MUTATION REJECTED' if killed else 'SURVIVED',flush=True)
                if not killed:raise RuntimeError('Mutation survived '+row['item']+'\n'+changed.stdout)
            finally:
                for path,source in originals.items():path.write_text(source)
        output=ROOT/(sys.argv[1] if len(sys.argv)>1 else 'reviews/20-chrome/records/review-fixes-mutations.json')
        output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(records,indent=2)+'\n')
    print(f'{len(records)} mutations rejected; every baseline passed',flush=True)

if __name__=='__main__':run()
